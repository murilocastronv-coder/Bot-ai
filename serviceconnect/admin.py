"""Painel administrativo web (responsivo), protegido por login, sessão assinada e token CSRF."""
from __future__ import annotations

import asyncio
import hmac
import json
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_, select

import services as sv
from config import settings
from database import get_db
from i18n import LANGS, PLAN_NAMES, t
from models import (Base, Broadcast, Category, City, Plan, Promotion, Report, Review, ServiceRequest,
                    User, utcnow)

templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
router = APIRouter(prefix="/admin")
_failed: dict[str, deque] = defaultdict(deque)
_bg_tasks: set[asyncio.Task] = set()


class NeedLogin(Exception):
    pass


# ---------------------------------------------------------------- segurança
def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "?")


def csrf_token(request: Request) -> str:
    tok = request.session.get("csrf")
    if not tok:
        tok = secrets.token_urlsafe(32)
        request.session["csrf"] = tok
    return tok


async def require_admin(request: Request) -> str:
    if not request.session.get("admin"):
        raise NeedLogin()
    if request.method == "POST":
        form = await request.form()
        if not hmac.compare_digest(str(form.get("csrf", "")), request.session.get("csrf", "") or "x"):
            raise HTTPException(status_code=403, detail="CSRF inválido")
    return request.session["admin"]


async def session_dep():
    async with get_db().session() as s:
        yield s


def render(request: Request, name: str, **ctx) -> HTMLResponse:
    ctx.update(request=request, csrf=csrf_token(request), admin=request.session.get("admin"), flash=request.session.pop("flash", None),
               plan_names=PLAN_NAMES, langs=LANGS)
    return templates.TemplateResponse(request, name, ctx)


def back(url: str, request: Request | None = None, msg: str | None = None) -> RedirectResponse:
    if request is not None and msg:
        request.session["flash"] = msg
    return RedirectResponse(url, status_code=303)


# ---------------------------------------------------------------- login
@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return render(request, "login.html", disabled=not settings.admin_password)


@router.post("/login")
async def login(request: Request, username: str = Form(""), password: str = Form(""), csrf: str = Form("")):
    ip = client_ip(request)
    q = _failed[ip]
    now = time.monotonic()
    while q and now - q[0] > 900:
        q.popleft()
    if len(q) >= 5:
        request.session["flash"] = "Muitas tentativas. Aguarde 15 minutos."
        return back("/admin/login")
    if not hmac.compare_digest(csrf, request.session.get("csrf", "") or "x"):
        return back("/admin/login", request, "Sessão expirada, tente novamente.")
    ok = bool(settings.admin_password) and hmac.compare_digest(username.encode(), settings.admin_username.encode()) \
        and hmac.compare_digest(password.encode(), settings.admin_password.encode())
    if not ok:
        q.append(now)
        await asyncio.sleep(1)
        return back("/admin/login", request, "Credenciais inválidas.")
    request.session.clear()
    request.session["admin"] = username
    request.session["csrf"] = secrets.token_urlsafe(32)
    return back("/admin")


@router.post("/logout")
async def logout(request: Request, _=Depends(require_admin)):
    request.session.clear()
    return back("/admin/login")


# ---------------------------------------------------------------- dashboard
@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    st = await sv.stats(s)
    days = []
    for i in range(13, -1, -1):
        d0 = (utcnow() - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        d1 = d0 + timedelta(days=1)
        u = (await s.execute(select(func.count(User.id)).where(User.created_at >= d0, User.created_at < d1))).scalar_one()
        r = (await s.execute(select(func.count(ServiceRequest.id)).where(ServiceRequest.created_at >= d0, ServiceRequest.created_at < d1))).scalar_one()
        days.append({"day": d0.strftime("%d/%m"), "users": u, "requests": r})
    peak = max([1] + [max(d["users"], d["requests"]) for d in days])
    top_cats = (await s.execute(select(Category, func.count(ServiceRequest.id)).join(ServiceRequest, ServiceRequest.category_id == Category.id)
                                .group_by(Category.id).order_by(func.count(ServiceRequest.id).desc()).limit(8))).all()
    top_cities = (await s.execute(select(User.city, func.count(User.id)).where(User.city.is_not(None))
                                  .group_by(User.city).order_by(func.count(User.id).desc()).limit(8))).all()
    return render(request, "dashboard.html", st=st, days=days, peak=peak, top_cats=top_cats, top_cities=top_cities,
                  monetization=await sv.monetization_enabled(s))


# ---------------------------------------------------------------- usuários
@router.get("/users", response_class=HTMLResponse)
async def users(request: Request, q: str = "", role: str = "", status: str = "", page: int = 1, _=Depends(require_admin), s=Depends(session_dep)):
    query = select(User).order_by(User.created_at.desc())
    if q:
        like = f"%{q.strip()}%"
        conds = [User.name.ilike(like), User.username.ilike(like), User.city.ilike(like)]
        if q.strip().isdigit():
            conds += [User.id == int(q), User.telegram_id == int(q)]
        query = query.where(or_(*conds))
    if role == "providers":
        query = query.where(User.is_provider.is_(True))
    elif role == "clients":
        query = query.where(User.is_provider.is_(False))
    if status == "banned":
        query = query.where(User.is_banned.is_(True))
    elif status == "active":
        query = query.where(User.last_active_at >= utcnow() - timedelta(days=7))
    elif status == "paid":
        query = query.where(User.plan_code != "free")
    page = max(1, page)
    rows = (await s.execute(query.limit(51).offset((page - 1) * 50))).scalars().all()
    return render(request, "users.html", users=rows[:50], has_next=len(rows) > 50, page=page, q=q, role=role, status=status)


@router.get("/users/{uid}", response_class=HTMLResponse)
async def user_detail(request: Request, uid: int, _=Depends(require_admin), s=Depends(session_dep)):
    user = await s.get(User, uid)
    if not user:
        raise HTTPException(404)
    prof = await sv.get_provider(s, uid)
    reqs = (await s.execute(select(ServiceRequest).where(ServiceRequest.client_id == uid).order_by(ServiceRequest.id.desc()).limit(30))).scalars().all()
    reports = (await s.execute(select(Report).where(or_(Report.target_user_id == uid, Report.reporter_id == uid))
                               .order_by(Report.id.desc()).limit(30))).scalars().all()
    invited = (await s.execute(select(func.count(User.id)).where(User.referred_by_id == uid))).scalar_one()
    plans = await sv.active_plans(s)
    return render(request, "user.html", u=user, prof=prof, reqs=reqs, reports=reports, invited=invited, plans=plans)


@router.post("/users/{uid}/action")
async def user_action(request: Request, uid: int, action: str = Form(...), reason: str = Form(""), plan: str = Form("premium"),
                      days: int = Form(30), _=Depends(require_admin), s=Depends(session_dep)):
    user = await s.get(User, uid)
    if not user:
        raise HTTPException(404)
    prof = await sv.get_provider(s, uid)
    msg = "OK"
    if action == "ban":
        user.is_banned, user.ban_reason = True, reason[:255] or "fraude"
        msg = "Conta suspensa."
    elif action == "unban":
        user.is_banned, user.ban_reason = False, None
        msg = "Conta reativada."
    elif action == "verify" and prof:
        prof.verified = True
        msg = "Profissional verificado."
    elif action == "unverify" and prof:
        prof.verified = False
    elif action == "grant":
        days = max(1, min(int(days), 3650))
        await sv.activate_plan(s, user, plan, days, source="admin_grant")
        msg = f"Plano {plan} concedido por {days} dias (grátis)."
    elif action == "revoke":
        user.plan_code, user.plan_until = "free", None
    elif action == "delete":
        await sv.delete_user_data(s, user)
        await s.commit()
        return back("/admin/users", request, "Usuário e dados excluídos.")
    await s.commit()
    return back(f"/admin/users/{uid}", request, msg)


# ---------------------------------------------------------------- pedidos
@router.get("/requests", response_class=HTMLResponse)
async def requests_page(request: Request, status: str = "", page: int = 1, _=Depends(require_admin), s=Depends(session_dep)):
    query = select(ServiceRequest).order_by(ServiceRequest.created_at.desc())
    if status:
        query = query.where(ServiceRequest.status == status)
    page = max(1, page)
    rows = (await s.execute(query.limit(51).offset((page - 1) * 50))).scalars().all()
    counts = {r.id: await sv.count_proposals(s, r.id) for r in rows}
    return render(request, "requests.html", reqs=rows[:50], counts=counts, status=status, page=page, has_next=len(rows) > 50)


@router.post("/requests/{rid}/hide")
async def request_hide(request: Request, rid: int, _=Depends(require_admin), s=Depends(session_dep)):
    req = await s.get(ServiceRequest, rid)
    if req:
        req.status = "hidden"
        await s.commit()
    return back("/admin/requests", request, f"Pedido #{rid} removido.")


# ---------------------------------------------------------------- categorias
@router.get("/categories", response_class=HTMLResponse)
async def categories(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    return render(request, "categories.html", cats=await sv.list_categories(s, active_only=False))


@router.post("/categories")
async def category_save(request: Request, cid: int = Form(0), key: str = Form(""), emoji: str = Form("✨"), sort: int = Form(100),
                        name_pt: str = Form(""), name_en: str = Form(""), name_fr: str = Form(""), name_es: str = Form(""),
                        _=Depends(require_admin), s=Depends(session_dep)):
    names = {k: v.strip()[:80] for k, v in {"pt": name_pt, "en": name_en, "fr": name_fr, "es": name_es}.items() if v.strip()}
    if not names:
        return back("/admin/categories", request, "Indique pelo menos um nome.")
    if cid:
        cat = await s.get(Category, cid)
        if not cat:
            raise HTTPException(404)
    else:
        key = "".join(ch for ch in (key or next(iter(names.values()))).lower() if ch.isalnum() or ch == "_")[:48] or secrets.token_hex(4)
        if (await s.execute(select(Category.id).where(Category.key == key))).first():
            key = f"{key}_{secrets.token_hex(2)}"
        cat = Category(key=key)
        s.add(cat)
    cat.emoji, cat.sort, cat.names = (emoji or "✨")[:8], sort, names
    await s.commit()
    return back("/admin/categories", request, "Categoria guardada.")


@router.post("/categories/{cid}/toggle")
async def category_toggle(request: Request, cid: int, _=Depends(require_admin), s=Depends(session_dep)):
    cat = await s.get(Category, cid)
    if cat:
        cat.active = not cat.active
        await s.commit()
    return back("/admin/categories")


# ---------------------------------------------------------------- denúncias e suporte
@router.get("/reports", response_class=HTMLResponse)
async def reports(request: Request, status: str = "open", _=Depends(require_admin), s=Depends(session_dep)):
    query = select(Report).order_by(Report.id.desc()).limit(100)
    if status:
        query = query.where(Report.status == status)
    rows = (await s.execute(query)).scalars().all()
    reviews = {r.review_id: await s.get(Review, r.review_id) for r in rows if r.review_id}
    users = {}
    for r in rows:
        for uid in (r.reporter_id, r.target_user_id):
            if uid and uid not in users:
                users[uid] = await s.get(User, uid)
    return render(request, "reports.html", reports=rows, reviews=reviews, users=users, status=status)


@router.post("/reports/{rid}/action")
async def report_action(request: Request, rid: int, action: str = Form(...), reply: str = Form(""),
                        _=Depends(require_admin), s=Depends(session_dep)):
    rep = await s.get(Report, rid)
    if not rep:
        raise HTTPException(404)
    msg = "OK"
    if action == "resolve":
        rep.status = "resolved"
    elif action == "dismiss":
        rep.status = "dismissed"
    elif action == "hide_review" and rep.review_id:
        review = await s.get(Review, rep.review_id)
        if review:
            review.hidden = True
            await s.flush()
            await sv.recompute_rating(s, review.provider_id)
        rep.status = "resolved"
        msg = "Avaliação ocultada."
    elif action == "ban" and rep.target_user_id:
        target = await s.get(User, rep.target_user_id)
        if target:
            target.is_banned, target.ban_reason = True, f"denúncia #{rid}"
        rep.status = "resolved"
        msg = "Usuário suspenso."
    elif action == "hide_request" and rep.request_id:
        req = await s.get(ServiceRequest, rep.request_id)
        if req:
            req.status = "hidden"
        rep.status = "resolved"
    elif action == "reply" and reply.strip() and rep.reporter_id:
        target = await s.get(User, rep.reporter_id)
        bot = getattr(request.app.state, "bot", None)
        from bot import notify
        if target and bot and await notify(bot, s, target, t("support_reply", target.language, text=reply.strip()[:3500])):
            rep.status = "resolved"
            msg = "Resposta enviada."
        else:
            msg = "Não foi possível enviar a resposta."
    await s.commit()
    return back("/admin/reports", request, msg)


# ---------------------------------------------------------------- comunicados
@router.get("/broadcast", response_class=HTMLResponse)
async def broadcast_page(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    rows = (await s.execute(select(Broadcast).order_by(Broadcast.id.desc()).limit(20))).scalars().all()
    reach = (await s.execute(select(func.count(User.id)).where(User.announcements_opt_in.is_(True), User.blocked_bot.is_(False),
                                                                User.is_banned.is_(False), User.onboarded.is_(True)))).scalar_one()
    return render(request, "broadcast.html", rows=rows, reach=reach)


@router.post("/broadcast")
async def broadcast_send(request: Request, text: str = Form(...), audience: str = Form("all"), _=Depends(require_admin),
                         s=Depends(session_dep)):
    text = text.strip()[:3500]
    if not text:
        return back("/admin/broadcast", request, "Texto vazio.")
    b = Broadcast(text=text, audience=audience if audience in ("all", "clients", "providers") else "all")
    s.add(b)
    await s.commit()
    bot = getattr(request.app.state, "bot", None)
    if bot:
        from bot import broadcast
        task = asyncio.create_task(broadcast(bot, get_db(), text, b.audience, b.id))
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
    return back("/admin/broadcast", request, "Comunicado em envio (apenas para quem aceitou receber comunicados).")


# ---------------------------------------------------------------- monetização
@router.get("/monetization", response_class=HTMLResponse)
async def monetization(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    plans = (await s.execute(select(Plan).order_by(Plan.sort))).scalars().all()
    promos = (await s.execute(select(Promotion).order_by(Promotion.id.desc()))).scalars().all()
    return render(request, "monetization.html", enabled=await sv.monetization_enabled(s), plans=plans, promos=promos,
                  st=await sv.stats(s))


@router.post("/monetization/toggle")
async def monetization_toggle(request: Request, confirm: str = Form(""), _=Depends(require_admin), s=Depends(session_dep)):
    enabled = await sv.monetization_enabled(s)
    if not enabled and confirm != "ATIVAR":
        return back("/admin/monetization", request, "Para ativar, escreva ATIVAR na confirmação.")
    await sv.set_setting(s, "monetization_enabled", not enabled)
    await s.commit()
    return back("/admin/monetization", request, "Cobranças ATIVADAS (os usuários continuam no plano gratuito até aceitarem)." if not enabled
                else "Cobranças desativadas.")


@router.post("/plans/{pid}")
async def plan_update(request: Request, pid: int, name: str = Form(...), price_eur: float = Form(0), price_stars: int = Form(0),
                      active: str = Form(""), _=Depends(require_admin), s=Depends(session_dep)):
    plan = await s.get(Plan, pid)
    if not plan:
        raise HTTPException(404)
    plan.name, plan.price_eur, plan.price_stars = name[:64], max(0.0, price_eur), max(0, price_stars)
    plan.active = bool(active) or plan.code == "free"
    await s.commit()
    return back("/admin/monetization", request, f"Plano {plan.name} atualizado.")


@router.post("/promotions")
async def promotion_create(request: Request, code: str = Form(...), plan_code: str = Form("premium"), days: int = Form(30),
                           max_uses: int = Form(100), _=Depends(require_admin), s=Depends(session_dep)):
    code = "".join(ch for ch in code.upper() if ch.isalnum())[:32]
    if not code or (await s.execute(select(Promotion.id).where(Promotion.code == code))).first():
        return back("/admin/monetization", request, "Código inválido ou já existente.")
    s.add(Promotion(code=code, plan_code=plan_code, days=max(1, days), max_uses=max(1, max_uses)))
    await s.commit()
    return back("/admin/monetization", request, f"Promoção {code} criada.")


@router.post("/promotions/{pid}/toggle")
async def promotion_toggle(request: Request, pid: int, _=Depends(require_admin), s=Depends(session_dep)):
    p = await s.get(Promotion, pid)
    if p:
        p.active = not p.active
        await s.commit()
    return back("/admin/monetization")


# ---------------------------------------------------------------- países e cidades
@router.get("/cities", response_class=HTMLResponse)
async def cities(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    rows = (await s.execute(select(City).order_by(City.country, City.name))).scalars().all()
    countries = (await s.execute(select(User.country, func.count(User.id)).where(User.country.is_not(None))
                                 .group_by(User.country).order_by(func.count(User.id).desc()))).all()
    return render(request, "cities.html", cities=rows, countries=countries)


@router.post("/cities")
async def city_add(request: Request, name: str = Form(...), country: str = Form(...), lat: float = Form(...), lon: float = Form(...),
                   _=Depends(require_admin), s=Depends(session_dep)):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return back("/admin/cities", request, "Coordenadas inválidas.")
    s.add(City(name=name.strip()[:128], country=country.strip().upper()[:8], lat=lat, lon=lon))
    await s.commit()
    return back("/admin/cities", request, "Cidade adicionada.")


@router.post("/cities/{cid}/toggle")
async def city_toggle(request: Request, cid: int, _=Depends(require_admin), s=Depends(session_dep)):
    c = await s.get(City, cid)
    if c:
        c.active = not c.active
        await s.commit()
    return back("/admin/cities")


# ---------------------------------------------------------------- indicações
@router.get("/referrals", response_class=HTMLResponse)
async def referrals(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    return render(request, "referrals.html", ranking=await sv.referral_ranking(s, 100))


# ---------------------------------------------------------------- backup
@router.get("/backup")
async def backup(request: Request, _=Depends(require_admin), s=Depends(session_dep)):
    """Exporta todas as tabelas (exceto o estado temporário do bot) em JSON."""
    out: dict = {"exported_at": utcnow().isoformat()}
    for table in Base.metadata.sorted_tables:
        if table.name == "fsm_states":
            continue
        rows = (await s.execute(select(table))).mappings().all()
        out[table.name] = [{k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in r.items()} for r in rows]
    body = json.dumps(out, ensure_ascii=False, default=str).encode()
    name = f"serviceconnect-backup-{utcnow():%Y%m%d-%H%M}.json"
    return Response(body, media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{name}"'})
