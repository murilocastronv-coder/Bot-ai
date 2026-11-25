"""Robô SAM SOL: a estratégia do EA "SAM Style V4" (MT5) passada para SOL/USD.

Regras (iguais ao EA, a cada 2 s em vez de 250 ms):
- momentum na vela de 1 minuto: preço ≥ abertura do minuto + 50 pontos → compra; ≤ −50 → venda
  (1 ponto = US$ 0,01, como o SOLUSD no MT5);
- no máximo 2 ordens, sempre no mesmo lado; a 2ª só 80 pontos a favor da última; 30 s entre entradas;
- cesta fecha tudo se perder 1% do saldo, ou depois de lucrar US$ 1,00 se devolver US$ 0,30;
- margem total ≤ 15% do capital;
- meta do mês +40% ou perda do mês −5%: fecha tudo e para até o mês seguinte.
Diferenças honestas: o lucro da cesta é calculado JÁ DESCONTANDO as taxas da Jupiter (0,06% para abrir
e 0,06% para fechar), porque é isso que a conta real recebe; e não há spread (a Jupiter usa o preço do oráculo).

Conta demo: dinheiro de mentira com o preço real da Binance. Conta real: Jupiter Perps com a carteira
cifrada no banco (sam_wallet.py). Backtest: velas de 1 minuto da Binance (1 ano, 3, 2 e 1 mês).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from array import array
from dataclasses import dataclass, field
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

import services as sv
from config import settings

log = logging.getLogger("serviceconnect.sam")
router = Router(name="sam_sol")


def _env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class Params:
    qty: float = field(default_factory=lambda: _env("SAM_QTY_SOL", 1.0))          # "Lots": SOL por ordem
    max_orders: int = field(default_factory=lambda: int(_env("SAM_MAX_ORDERS", 2)))
    target_pct: float = field(default_factory=lambda: _env("SAM_MONTH_TARGET", 40.0))
    basket_risk_pct: float = field(default_factory=lambda: _env("SAM_BASKET_RISK", 1.0))
    month_loss_pct: float = field(default_factory=lambda: _env("SAM_MONTH_LOSS", 5.0))
    max_margin_pct: float = field(default_factory=lambda: _env("SAM_MAX_MARGIN", 15.0))
    momentum_pts: float = field(default_factory=lambda: _env("SAM_MOMENTUM", 50))
    spacing_pts: float = field(default_factory=lambda: _env("SAM_SPACING", 80))
    max_spread_pts: float = field(default_factory=lambda: _env("SAM_MAX_SPREAD", 40))
    cooldown: float = field(default_factory=lambda: _env("SAM_COOLDOWN", 30))
    activation: float = field(default_factory=lambda: _env("SAM_ACTIVATION", 1.0))
    giveback: float = field(default_factory=lambda: _env("SAM_GIVEBACK", 0.30))
    point: float = field(default_factory=lambda: _env("SAM_POINT", 0.01))
    leverage: float = field(default_factory=lambda: _env("SAM_LEVERAGE", 10))
    fee: float = field(default_factory=lambda: _env("SAM_FEE", 0.0006))
    demo_capital: float = field(default_factory=lambda: _env("SAM_DEMO_CAPITAL", 1000))


def month_key(ts: float) -> int:
    g = time.gmtime(ts)
    return g.tm_year * 100 + g.tm_mon


# ======================================================================= estratégia
class Engine:
    """Contabilidade e decisões do EA. Estado em dict (JSON) para guardar no banco."""

    def __init__(self, p: Params, capital: float, state: dict | None = None):
        self.p = p
        self.s = state or {"balance": capital, "capital": capital, "pos": [], "peak": 0.0, "closing": False,
                           "last_entry": 0.0, "month": 0, "month_base": 0.0, "locked": False, "lock_reason": "",
                           "baskets": 0, "wins": 0, "fees": 0.0, "last": []}

    # ---- contas
    def float_pnl(self, price: float) -> float:
        return sum(q["side"] * q["qty"] * (price - q["price"]) for q in self.s["pos"])

    def basket_pnl(self, price: float) -> float:
        """Lucro da cesta como na conta real: preço − taxas de abertura pagas − taxa de fecho."""
        pos = self.s["pos"]
        return self.float_pnl(price) - sum(q["fee"] for q in pos) - sum(q["qty"] for q in pos) * price * self.p.fee

    def equity(self, price: float) -> float:
        pos = self.s["pos"]
        return self.s["balance"] + self.float_pnl(price) - sum(q["qty"] for q in pos) * price * self.p.fee

    def margin_used(self) -> float:
        return sum(q["qty"] * q["price"] for q in self.s["pos"]) / self.p.leverage

    # ---- decisão (o OnTimer do EA)
    def decide(self, ts: float, price: float, m1_open: float, spread: float = 0.0, mkey: int | None = None):
        p, s = self.p, self.s
        k = mkey if mkey is not None else month_key(ts)
        if k != s["month"]:
            s["month"], s["month_base"], s["locked"], s["lock_reason"] = k, self.equity(price), False, ""
        eq = self.equity(price)
        base = s["month_base"]
        if base > 0 and not s["locked"]:
            if eq >= base * (1 + p.target_pct / 100):
                s["locked"], s["lock_reason"] = True, "meta do mês"
            elif eq <= base * (1 - p.month_loss_pct / 100):
                s["locked"], s["lock_reason"] = True, "perda máxima do mês"
        if s["locked"]:
            return ("close",) if s["pos"] else None
        n = len(s["pos"])
        if n == 0:
            s["peak"], s["closing"] = 0.0, False
        else:
            bp = self.basket_pnl(price)
            if bp <= -s["balance"] * p.basket_risk_pct / 100:
                s["closing"] = True
            s["peak"] = max(s["peak"], bp)
            if s["peak"] >= p.activation and bp <= s["peak"] - p.giveback:
                s["closing"] = True
        if s["closing"]:
            return ("close",)
        move = (price - m1_open) / p.point
        side = 1 if move >= p.momentum_pts else -1 if move <= -p.momentum_pts else 0
        if side == 0 or n >= p.max_orders or (n > 0 and s["pos"][-1]["side"] != side):
            return None
        if spread / p.point > p.max_spread_pts or ts - s["last_entry"] < p.cooldown:
            return None
        if n > 0 and side * (price - s["pos"][-1]["price"]) < p.spacing_pts * p.point:
            return None
        margin = p.qty * price / p.leverage
        used = self.margin_used()
        if margin > eq - used or margin + used > eq * p.max_margin_pct / 100:
            return None
        return ("open", side, p.qty)

    # ---- execução
    def apply_open(self, ts: float, side: int, qty: float, price: float) -> None:
        fee = qty * price * self.p.fee
        self.s["balance"] -= fee
        self.s["fees"] += fee
        self.s["pos"].append({"side": side, "qty": qty, "price": price, "fee": fee, "ts": ts})

    def apply_close(self, ts: float, price: float) -> float:
        """Fecha a cesta; devolve o resultado líquido dela (já com as taxas de abrir e fechar)."""
        s = self.s
        pos = s["pos"]
        gross = self.float_pnl(price)
        fee = sum(q["qty"] for q in pos) * price * self.p.fee
        net = gross - fee - sum(q["fee"] for q in pos)
        s["balance"] += gross - fee
        s["fees"] += fee
        s["baskets"] += 1
        s["wins"] += net > 0
        s["last"] = (s["last"] + [[ts, round(net, 2), len(pos), pos[0]["side"] if pos else 0]])[-10:]
        s["pos"], s["peak"], s["closing"] = [], 0.0, False
        return net

    def step(self, ts: float, price: float, m1_open: float, mkey: int | None = None):
        """Demo/backtest: decide e executa logo ao preço atual."""
        act = self.decide(ts, price, m1_open, 0.0, mkey)
        if not act:
            return None
        if act[0] == "open":
            self.s["last_entry"] = ts
            self.apply_open(ts, act[1], act[2], price)
            return ("open", act[1], price)
        return ("close", self.apply_close(ts, price))


# ======================================================================= dados (Binance)
HOSTS = ("https://api.binance.com", "https://data-api.binance.vision", "https://api1.binance.com")
_cache: dict = {}


async def _get_json(http, path: str, params: dict):
    last = None
    for host in HOSTS:
        try:
            async with http.get(host + path, params=params) as r:
                if r.status == 200:
                    return await r.json()
                last = f"HTTP {r.status} em {host}"
        except Exception as ex:  # noqa: BLE001
            last = f"{type(ex).__name__} em {host}"
    raise RuntimeError("Binance indisponível: " + str(last))


async def live_price(http) -> tuple[float, float, float]:
    """(hora de abertura do minuto, abertura do minuto, preço atual) do SOLUSDT."""
    k = await _get_json(http, "/api/v3/klines", {"symbol": "SOLUSDT", "interval": "1m", "limit": 1})
    return k[-1][0] / 1000, float(k[-1][1]), float(k[-1][4])


async def load_candles(days: int = 366):
    """Velas de 1 minuto dos últimos `days` dias (fica em memória 6 h)."""
    import aiohttp
    hit = _cache.get("c")
    if hit and time.time() - hit[0] < 6 * 3600 and hit[1] >= days:
        return hit[2]
    t, o, h, l, c = array("q"), array("d"), array("d"), array("d"), array("d")
    end = int(time.time() // 60 * 60 * 1000)
    start = end - days * 86_400_000
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as http:
        while start < end:
            rows = await _get_json(http, "/api/v3/klines", {"symbol": "SOLUSDT", "interval": "1m",
                                                            "startTime": start, "endTime": end - 1, "limit": 1000})
            if not rows:
                break
            for r in rows:
                t.append(r[0] // 1000)
                o.append(float(r[1]))
                h.append(float(r[2]))
                l.append(float(r[3]))
                c.append(float(r[4]))
            start = rows[-1][0] + 60_000
    data = (t, o, h, l, c)
    _cache["c"] = (time.time(), days, data)
    return data


# ======================================================================= backtest
PERIODS = {"1a": (365, "1 ano"), "3m": (90, "3 meses"), "2m": (60, "2 meses"), "1m": (30, "1 mês")}


def backtest(data, days: int, p: Params | None = None, capital: float | None = None) -> dict:
    """Simula cada vela de 1 minuto como 4 preços: abertura, mínima/máxima (na ordem mais provável) e fecho."""
    p = p or Params()
    capital = capital or p.demo_capital
    t, o, h, l, c = data
    if not t:
        raise RuntimeError("sem velas")
    first = t[-1] - days * 86400
    i0 = 0
    while i0 < len(t) and t[i0] < first:
        i0 += 1
    eng = Engine(p, capital)
    peak_eq, max_dd = capital, 0.0
    months: dict[int, list] = {}
    locks: dict[int, str] = {}
    mk = None
    for i in range(i0, len(t)):
        ts, op = t[i], o[i]
        if mk is None or ts % 86400 < 60:
            mk = month_key(ts)
        if op <= 0:
            continue
        mid = (l[i], h[i]) if c[i] >= op else (h[i], l[i])
        for off, px in ((0, op), (20, mid[0]), (40, mid[1]), (59, c[i])):
            eng.step(ts + off, px, op, mk)
        eq = eng.equity(c[i])
        if eq > peak_eq:
            peak_eq = eq
        dd = (peak_eq - eq) / peak_eq if peak_eq > 0 else 0
        if dd > max_dd:
            max_dd = dd
        m = months.setdefault(mk, [eng.s["month_base"] or eq, eq])
        m[1] = eq
        if eng.s["locked"]:
            locks[mk] = eng.s["lock_reason"]
    if eng.s["pos"]:
        eng.apply_close(t[-1] + 60, c[-1])
    end_eq = eng.s["balance"]
    s = eng.s
    return {"days": days, "start": t[i0], "end": t[-1], "capital": capital, "final": end_eq,
            "ret": (end_eq / capital - 1) * 100, "baskets": s["baskets"], "wins": s["wins"], "fees": s["fees"],
            "max_dd": max_dd * 100, "months": {k: (v[1] / v[0] - 1) * 100 if v[0] else 0 for k, v in months.items()},
            "locks": locks, "price0": o[i0], "price1": c[-1]}


def backtest_text(r: dict, label: str, p: Params | None = None) -> str:
    p = p or Params()
    d0, d1 = time.strftime("%d/%m/%Y", time.gmtime(r["start"])), time.strftime("%d/%m/%Y", time.gmtime(r["end"]))
    wr = r["wins"] / r["baskets"] * 100 if r["baskets"] else 0
    lines = [f"🧪 <b>Backtest SAM SOL — {label}</b> ({d0} → {d1})",
             f"SOL: ${r['price0']:.2f} → ${r['price1']:.2f}",
             f"Capital: ${r['capital']:.2f} → <b>${r['final']:.2f}</b> ({r['ret']:+.1f}%)",
             f"Cestas fechadas: {r['baskets']} · acerto {wr:.0f}%",
             f"Taxas pagas (Jupiter {p.fee * 100:.2f}% ×2): ${r['fees']:.2f}",
             f"Maior queda do capital: −{r['max_dd']:.1f}%", "", "<b>Por mês</b>"]
    for k in sorted(r["months"]):
        lock = r["locks"].get(k, "")
        tag = " 🎯 meta" if lock == "meta do mês" else " 🛑 parou (−5%)" if lock else ""
        lines.append(f"{k % 100:02d}/{k // 100}: {r['months'][k]:+.1f}%{tag}")
    lines += ["", f"Ordem: {p.qty:g} SOL · alavancagem {p.leverage:g}x · velas de 1 min da Binance.",
              "⚠️ Passado não garante futuro; dentro do minuto o caminho do preço é estimado."]
    return "\n".join(lines)


# ======================================================================= estado e robô ao vivo
DEMO, REAL = "sam_sol_demo", "sam_sol_real"
_bt_running = False


_mem: dict = {}


async def load(key: str, capital: float) -> tuple[dict, Engine]:
    """Estado da conta (em memória; lido do banco só na primeira vez)."""
    if key in _mem:
        return _mem[key]
    from database import get_db
    async with get_db().session() as s:
        d = await sv.get_setting(s, key)
    if not isinstance(d, dict) or "engine" not in d:
        d = {"on": key == DEMO, "engine": None, "errors": 0}
    eng = Engine(Params(), capital, d.get("engine"))
    _mem[key] = (d, eng)
    return d, eng


async def save(key: str, d: dict, eng: Engine) -> None:
    from database import get_db
    d["engine"] = eng.s
    d["saved"] = time.time()
    _mem[key] = (d, eng)
    async with get_db().session() as s:
        await sv.set_setting(s, key, d)
        await s.commit()


async def save_soon(key: str, d: dict, eng: Engine, changed: bool) -> None:
    """Grava logo quando houve ordem; senão no máximo a cada 60 s (não martela o banco)."""
    if changed or time.time() - d.get("saved", 0) > 60:
        await save(key, d, eng)


async def tell(bot: Bot, text: str) -> None:
    from bot import notify_admins
    from database import get_db
    try:
        async with get_db().session() as s:
            await notify_admins(bot, text, s)
    except Exception:  # noqa: BLE001
        log.exception("aviso falhou")


def side_name(side: int) -> str:
    return "COMPRA" if side > 0 else "VENDA"


async def demo_tick(bot: Bot, price_info) -> None:
    d, eng = await load(DEMO, Params().demo_capital)
    if not d.get("on"):
        return
    _, m1_open, price = price_info
    ev = eng.step(time.time(), price, m1_open)
    await save_soon(DEMO, d, eng, ev is not None)
    if ev and ev[0] == "close":
        await tell(bot, f"🧪 SAM SOL demo: cesta fechada {ev[1]:+.2f} USD · saldo ${eng.s['balance']:.2f}")


async def real_tick(bot: Bot, price_info) -> None:
    import sam_perps
    import sam_wallet
    from database import get_db
    d, eng = await load(REAL, 0.0)
    if not d.get("on"):
        return
    _, m1_open, price = price_info
    act = eng.decide(time.time(), price, m1_open)
    if not act:
        await save_soon(REAL, d, eng, False)
        return
    p = eng.p
    try:
        async with get_db().session() as s:
            kp = await sam_wallet.keypair(s)
        if act[0] == "open":
            eng.s["last_entry"] = time.time()
            side = "long" if act[1] > 0 else "short"
            collateral = act[2] * price / p.leverage
            pos = await asyncio.to_thread(sam_perps.open_position, kp, side, collateral, p.leverage, price)
            eng.apply_open(time.time(), act[1], act[2], price)
            await tell(bot, f"💰 SAM SOL REAL: {side_name(act[1])} {act[2]:g} SOL a ${price:.2f} "
                            f"(posição ${pos.get('size_usd', 0):.2f})")
        else:
            side = "long" if eng.s["pos"][0]["side"] > 0 else "short"
            await asyncio.to_thread(sam_perps.close_position, kp, side, price)
            net = eng.apply_close(time.time(), price)
            await tell(bot, f"💰 SAM SOL REAL: cesta fechada {net:+.2f} USD (estimado)")
        d["errors"] = 0
    except Exception as ex:  # noqa: BLE001
        d["errors"] = d.get("errors", 0) + 1
        log.warning("ordem real falhou: %s", ex)
        if d["errors"] >= 3:
            d["on"] = False
            await tell(bot, "⛔ SAM SOL REAL desligado depois de 3 erros seguidos: " + escape(str(ex))[:300])
        else:
            await tell(bot, "⚠️ SAM SOL REAL: ordem falhou: " + escape(str(ex))[:300])
    await save(REAL, d, eng)


async def run(bot: Bot) -> None:
    """Laço do robô: preço a cada 2 s; demo e real em tarefas separadas (a real espera a Jupiter)."""
    import aiohttp
    await asyncio.sleep(20)
    real_task = None
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as http:
        while True:
            try:
                info = await live_price(http)
                await demo_tick(bot, info)
                if real_task is None or real_task.done():
                    real_task = asyncio.create_task(real_tick(bot, info))
            except asyncio.CancelledError:
                raise
            except Exception as ex:  # noqa: BLE001
                log.warning("SAM SOL ciclo: %s", ex)
                await asyncio.sleep(10)
            await asyncio.sleep(2)


# ======================================================================= Telegram (/sol, só administradores)
def kb(demo_on: bool, real_on: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [b(text="🔴 Desligar demo" if demo_on else "🟢 Ligar demo", callback_data="sam:demo"),
         b(text="🔴 Desligar real" if real_on else "💰 Ligar real", callback_data="sam:real")],
        [b(text="📊 Atualizar", callback_data="sam:home")],
        [b(text="🧪 1 ano", callback_data="sam:bt:1a"), b(text="🧪 3 meses", callback_data="sam:bt:3m"),
         b(text="🧪 2 meses", callback_data="sam:bt:2m"), b(text="🧪 1 mês", callback_data="sam:bt:1m")],
        [b(text="💼 Carteira real", callback_data="sam:wallet"), b(text="♻️ Zerar demo", callback_data="sam:reset")],
    ])


def account_text(title: str, d: dict, eng: Engine, price: float | None) -> str:
    s = eng.s
    on = "🟢 ligada" if d.get("on") else "⚪ desligada"
    lines = [f"<b>{title}</b>: {on}"]
    if s["capital"] or s["baskets"]:
        eq = eng.equity(price) if price else s["balance"]
        lines.append(f"Saldo ${s['balance']:.2f} · capital agora ${eq:.2f} (início ${s['capital']:.2f})")
        wr = s["wins"] / s["baskets"] * 100 if s["baskets"] else 0
        lines.append(f"Cestas {s['baskets']} · acerto {wr:.0f}% · taxas ${s['fees']:.2f}")
    if s["pos"]:
        lines.append(f"Aberta: {len(s['pos'])} × {side_name(s['pos'][0]['side'])} · resultado "
                     f"{eng.basket_pnl(price):+.2f} USD" if price else f"Aberta: {len(s['pos'])} ordens")
    if s["locked"]:
        lines.append(f"⏸ Parado até o mês que vem ({s['lock_reason']})")
    return "\n".join(lines)


async def home_text() -> tuple[str, bool, bool]:
    import aiohttp
    p = Params()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as http:
            price = (await live_price(http))[2]
    except Exception:  # noqa: BLE001
        price = None
    dd, de = await load(DEMO, p.demo_capital)
    rd, re_ = await load(REAL, 0.0)
    head = "🤖 <b>Robô SAM SOL</b> (estratégia SAM Style V4 em SOL/USD)"
    if price:
        head += f"\nSOL agora: ${price:.2f}"
    text = "\n\n".join([head, account_text("Conta demo", dd, de, price), account_text("Conta real (Jupiter)", rd, re_, price),
                        f"Ordem {p.qty:g} SOL · máx {p.max_orders} · alavancagem {p.leverage:g}x · meta mês +{p.target_pct:g}% · "
                        f"stop mês −{p.month_loss_pct:g}%"])
    return text, bool(dd.get("on")), bool(rd.get("on"))


def _admin(event) -> bool:
    from bot import is_admin_user
    return is_admin_user(event.from_user)


@router.message(Command("sol"))
async def cmd_sol(m: Message):
    if not _admin(m):
        return
    text, d_on, r_on = await home_text()
    await m.answer(text, reply_markup=kb(d_on, r_on))


@router.callback_query(F.data.startswith("sam:"))
async def cb_sam(c: CallbackQuery, bot: Bot):
    global _bt_running
    if not _admin(c):
        await c.answer()
        return
    part = (c.data or "").split(":")
    action = part[1] if len(part) > 1 else "home"
    p = Params()
    if action == "demo":
        d, eng = await load(DEMO, p.demo_capital)
        d["on"] = not d.get("on")
        await save(DEMO, d, eng)
    elif action == "reset":
        d, _ = await load(DEMO, p.demo_capital)
        await save(DEMO, {"on": d.get("on", True), "errors": 0}, Engine(p, p.demo_capital))
        await c.answer("Demo zerada com $%.0f" % p.demo_capital)
    elif action == "real":
        d, eng = await load(REAL, 0.0)
        if d.get("on"):
            d["on"] = False
            await save(REAL, d, eng)
            await c.answer("Real desligada (ordens abertas continuam na Jupiter até você fechar)", show_alert=True)
        else:
            await c.answer()
            await c.message.answer(
                "⚠️ <b>Ligar a conta REAL?</b>\nO robô vai abrir ordens de verdade na Jupiter com o USDC da carteira "
                "do robô. As taxas (~0,06% para abrir e 0,06% para fechar) comem parte das cestas pequenas. "
                "Pode perder dinheiro. O capital inicial é o USDC que estiver na carteira agora.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="✅ Confirmar real", callback_data="sam:realok"),
                    InlineKeyboardButton(text="Cancelar", callback_data="sam:home")]]))
            return
    elif action == "realok":
        import sam_perps
        import sam_wallet
        from database import get_db
        try:
            async with get_db().session() as s:
                kp = await sam_wallet.keypair(s)
            usdc = await asyncio.to_thread(sam_perps.usdc_balance, kp.pubkey())
            sol = await asyncio.to_thread(sam_perps.sol_balance, kp.pubkey())
        except Exception as ex:  # noqa: BLE001
            await c.answer()
            await c.message.answer("❌ Não liguei a real: " + escape(str(ex))[:300] + "\nAbra 💼 Carteira real.")
            return
        if usdc < 5 or sol < 0.02:
            await c.answer()
            await c.message.answer(f"❌ Não liguei a real: a carteira tem ${usdc:.2f} USDC e {sol:.4f} SOL. "
                                   "Precisa de USDC para a garantia e ~0,05 SOL para as taxas da rede.")
            return
        d, eng = await load(REAL, usdc)
        if not eng.s["capital"]:
            eng = Engine(p, usdc)
        d.update(on=True, errors=0)
        await save(REAL, d, eng)
        await c.answer("Real ligada", show_alert=True)
    elif action == "wallet":
        import sam_perps
        import sam_wallet
        from database import get_db
        await c.answer()
        try:
            async with get_db().session() as s:
                addr, new = await sam_wallet.create_or_get(s)
            from solders.pubkey import Pubkey
            owner = Pubkey.from_string(addr)
            usdc = await asyncio.to_thread(sam_perps.usdc_balance, owner)
            sol = await asyncio.to_thread(sam_perps.sol_balance, owner)
            await c.message.answer(
                ("🆕 Carteira nova criada.\n" if new else "") +
                f"💼 <b>Carteira da conta real</b>\n<code>{addr}</code>\nUSDC: ${usdc:.2f} · SOL: {sol:.4f}\n\n"
                "Envie USDC (rede Solana) para a garantia e ~0,05 SOL para as taxas. A chave fica cifrada no banco "
                "e nunca aparece aqui.")
        except Exception as ex:  # noqa: BLE001
            await c.message.answer("❌ " + escape(str(ex))[:300])
        return
    elif action == "bt":
        key = part[2] if len(part) > 2 and part[2] in PERIODS else "1m"
        await c.answer()
        if _bt_running:
            await c.message.answer("⏳ Já há um backtest a correr, espere ele terminar.")
            return
        _bt_running = True
        days, label = PERIODS[key]
        await c.message.answer(f"⏳ Backtest de {label}: baixando as velas de 1 minuto da Binance "
                               "(1 ano demora uns minutos)…")
        try:
            data = await load_candles(366 if key == "1a" else max(days + 1, 31))
            r = await asyncio.to_thread(backtest, data, days, p)
            await c.message.answer(backtest_text(r, label, p))
        except Exception as ex:  # noqa: BLE001
            log.exception("backtest")
            await c.message.answer("❌ Backtest falhou: " + escape(str(ex))[:300])
        finally:
            _bt_running = False
        return
    else:
        await c.answer()
    text, d_on, r_on = await home_text()
    try:
        await c.message.edit_text(text, reply_markup=kb(d_on, r_on))
    except Exception:  # noqa: BLE001
        await c.message.answer(text, reply_markup=kb(d_on, r_on))
