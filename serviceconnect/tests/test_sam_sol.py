import calendar
import math
from array import array

import pytest

import sam_sol
from sam_sol import Engine, Params, backtest, backtest_text

T0 = calendar.timegm((2026, 3, 10, 12, 0, 0))


def params(**kw):
    p = Params()
    for k, v in dict(qty=1.0, max_orders=2, target_pct=40, basket_risk_pct=1, month_loss_pct=5, max_margin_pct=15,
                     momentum_pts=50, spacing_pts=80, max_spread_pts=40, cooldown=30, activation=1.0, giveback=0.30,
                     point=0.01, leverage=10, fee=0.0, demo_capital=1000).items():
        setattr(p, k, kw.get(k, v))
    return p


def test_no_entry_without_momentum():
    e = Engine(params(), 1000)
    assert e.step(T0, 100.49, 100.0) is None
    assert e.s["pos"] == []


def test_buy_and_sell_on_momentum():
    e = Engine(params(), 1000)
    assert e.step(T0, 100.50, 100.0)[:2] == ("open", 1)
    e2 = Engine(params(), 1000)
    assert e2.step(T0, 99.50, 100.0)[:2] == ("open", -1)


def test_cooldown_spacing_same_side_and_max_orders():
    e = Engine(params(), 1000)
    e.step(T0, 100.50, 100.0)
    assert e.step(T0 + 10, 101.40, 100.0) is None          # cooldown 30 s
    assert e.step(T0 + 31, 101.20, 101.0) is None           # só 0,70 a favor (< 80 pontos)
    assert len(e.s["pos"]) == 1
    e.s["peak"] = 0
    # sem lucro acumulado ainda para o trailing: 2ª ordem 0,80 acima
    ev = e.step(T0 + 40, 101.30, 100.80)
    assert ev is None or ev[0] == "open"


def test_opposite_signal_ignored_while_open():
    e = Engine(params(activation=100), 1000)
    e.step(T0, 100.50, 100.0)
    assert e.step(T0 + 60, 100.00, 100.50) is None
    assert len(e.s["pos"]) == 1


def test_trailing_basket_close():
    e = Engine(params(), 1000)
    e.step(T0, 100.50, 100.0)
    e.step(T0 + 1, 101.60, 101.55)                          # +1,10 → ativou
    ev = e.step(T0 + 2, 101.25, 101.55)                     # devolveu 0,35 ≥ 0,30
    assert ev[0] == "close" and math.isclose(ev[1], 0.75, abs_tol=1e-9)
    assert e.s["pos"] == [] and e.s["baskets"] == 1 and e.s["wins"] == 1


def test_basket_risk_stop():
    e = Engine(params(), 1000)
    e.step(T0, 100.50, 100.0)
    ev = e.step(T0 + 5, 90.40, 90.45)                       # −10,10 ≤ −1% de 1000
    assert ev[0] == "close" and ev[1] < -10


def test_fees_counted_in_basket():
    e = Engine(params(fee=0.0006), 1000)
    e.step(T0, 100.0 + 0.5, 100.0)
    assert e.basket_pnl(100.5) == pytest.approx(-2 * 100.5 * 0.0006)


def test_margin_limit_blocks_entry():
    e = Engine(params(leverage=1), 1000)                     # 1 SOL de $100 = 10% < 15%
    e.step(T0, 100.50, 100.0)
    assert len(e.s["pos"]) == 1
    e2 = Engine(params(leverage=1, qty=2), 1000)              # $201 > 15% de 1000
    assert e2.step(T0, 100.50, 100.0) is None


def test_month_target_locks_until_next_month():
    e = Engine(params(target_pct=1, activation=1000), 1000)
    e.step(T0, 100.50, 100.0)
    ev = e.step(T0 + 5, 111.0, 111.0)                         # +10,5 ≥ 1% de 1000
    assert ev[0] == "close" and e.s["locked"] and e.s["lock_reason"] == "meta do mês"
    assert e.step(T0 + 100, 120.0, 100.0) is None             # parado
    nxt = calendar.timegm((2026, 4, 1, 0, 1, 0))
    assert e.step(nxt, 120.0, 100.0)[0] == "open"             # mês novo volta a operar


def _candles(n, start, f):
    t, o, h, l, c = array("q"), array("d"), array("d"), array("d"), array("d")
    for i in range(n):
        op, cl = f(i), f(i + 1)
        t.append(start + 60 * i)
        o.append(op)
        c.append(cl)
        h.append(max(op, cl) + 0.2)
        l.append(min(op, cl) - 0.2)
    return t, o, h, l, c


def test_backtest_runs_and_reports():
    data = _candles(60 * 24 * 40, T0, lambda i: 150 + 5 * math.sin(i / 37.0) + (i % 7) * 0.15)
    r = backtest(data, 30, params(fee=0.0006))
    assert r["baskets"] > 0 and r["final"] > 0 and r["days"] == 30
    assert 0 <= r["max_dd"] <= 100 and r["months"]
    txt = backtest_text(r, "1 mês", params(fee=0.0006))
    assert "Backtest SAM SOL" in txt and "Por mês" in txt


def test_backtest_period_slicing():
    data = _candles(60 * 24 * 100, T0, lambda i: 150 + 3 * math.sin(i / 50.0))
    r30 = backtest(data, 30, params())
    r90 = backtest(data, 90, params())
    assert r90["start"] < r30["start"] and r30["end"] == r90["end"]


def test_perps_instructions_build():
    from solders.keypair import Keypair

    import sam_perps
    owner = Keypair().pubkey()
    ix = sam_perps.increase_ix(owner, "long", 1_000_000, 10_000_000, 150_000_000, 6_000_000, 7)
    assert ix.program_id == sam_perps.PROGRAM_ID and len(ix.accounts) == 16
    ix2 = sam_perps.decrease_ix(owner, "short", 150_000_000, 8)
    assert len(ix2.accounts) == 16
    assert sam_perps.position_pda(owner, "long") != sam_perps.position_pda(owner, "short")


async def test_wallet_create_and_decrypt(db, monkeypatch):
    import sam_wallet
    monkeypatch.setenv("SAM_WALLET_PASSPHRASE", "x" * 30)
    async with db.session() as s:
        addr, new = await sam_wallet.create_or_get(s)
        assert new
        addr2, new2 = await sam_wallet.create_or_get(s)
        assert addr2 == addr and not new2
        kp = await sam_wallet.keypair(s)
        assert str(kp.pubkey()) == addr
    monkeypatch.setenv("SAM_WALLET_PASSPHRASE", "y" * 30)
    async with db.session() as s:
        with pytest.raises(sam_wallet.WalletError):
            await sam_wallet.keypair(s)


async def test_wallet_needs_passphrase(db, monkeypatch):
    import sam_wallet
    monkeypatch.delenv("SAM_WALLET_PASSPHRASE", raising=False)
    async with db.session() as s:
        with pytest.raises(sam_wallet.WalletError):
            await sam_wallet.create_or_get(s)


async def test_demo_state_persists_and_real_starts_off(db):
    sam_sol._mem.clear()
    d, eng = await sam_sol.load(sam_sol.DEMO, 1000)
    r, _ = await sam_sol.load(sam_sol.REAL, 0)
    assert d["on"] is True and r["on"] is False
    eng.apply_open(T0, 1, 1.0, 100.0)
    await sam_sol.save(sam_sol.DEMO, d, eng)
    sam_sol._mem.clear()
    d2, eng2 = await sam_sol.load(sam_sol.DEMO, 1000)
    assert len(eng2.s["pos"]) == 1
    sam_sol._mem.clear()


async def test_sol_command_admin_only(db, fake_bot, monkeypatch):
    from tests.test_bot_flow import Harness

    async def no_price(http):
        raise RuntimeError("offline")
    monkeypatch.setattr(sam_sol, "live_price", no_price)
    sam_sol._mem.clear()
    bot, session = fake_bot
    h = Harness(db, bot, session)
    await h.text(555, "/sol")
    assert not any("SAM SOL" in x for x in session.texts_to(555))
    await h.text(999, "/sol")                                    # 999 = ADMIN_TELEGRAM_IDS nos testes
    assert any("Robô SAM SOL" in x for x in session.texts_to(999))
    assert "sam:bt:1a" in h.last_markup_callbacks(999) and "sam:real" in h.last_markup_callbacks(999)
    await h.click(999, "sam:demo")                               # desliga a demo
    d, _ = await sam_sol.load(sam_sol.DEMO, 1000)
    assert d["on"] is False
    await h.click(999, "sam:real")                               # pede confirmação, não liga
    r, _ = await sam_sol.load(sam_sol.REAL, 0)
    assert r["on"] is False
    assert any("Ligar a conta REAL" in x for x in session.texts_to(999))
    sam_sol._mem.clear()
