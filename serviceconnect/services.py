"""Regras de negócio (independentes do Telegram) — usadas pelo bot, pelo painel e pelos testes."""
from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models import (Category, City, Conversation, FSMRecord, Message, Plan, PortfolioPhoto, Promotion, PromotionUse,
                    Proposal, ProviderProfile, Report, Review, ServiceRequest, Setting, Subscription, User, utcnow)

RADII = (5, 10, 25, 50, 100)
URGENCIES = ("low", "normal", "high", "urgent")
PAID_FEATURES_HIGHLIGHT = {"highlight", "sponsored"}


class BusinessError(Exception):
    """Erro de regra de negócio; .code corresponde a uma chave de tradução."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# ---------------------------------------------------------------- geografia
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def fold(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip().casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


@dataclass
class Place:
    city: str
    country: str | None
    lat: float | None
    lon: float | None


async def resolve_city(s: AsyncSession, raw: str) -> Place:
    """Interpreta 'Cidade' ou 'Cidade, PT'. Usa a tabela de cidades (gerida pelo admin) para coordenadas."""
    raw = (raw or "").strip()[:128]
    name, _, cc = raw.partition(",")
    name, cc = name.strip(), cc.strip().upper()[:8] or None
    cities = (await s.execute(select(City).where(City.active.is_(True)))).scalars().all()
    target = fold(name)
    for c in cities:
        if fold(c.name) == target and (cc is None or c.country.upper() == cc):
            return Place(c.name, c.country, c.lat, c.lon)
    return Place(name.title() if name.islower() else name, cc, None, None)


async def nearest_city(s: AsyncSession, lat: float, lon: float, max_km: float = 60) -> City | None:
    best, best_d = None, max_km
    for c in (await s.execute(select(City).where(City.active.is_(True)))).scalars():
        d = haversine_km(lat, lon, c.lat, c.lon)
        if d <= best_d:
            best, best_d = c, d
    return best


def distance_between(a_lat, a_lon, b_lat, b_lon) -> float | None:
    if None in (a_lat, a_lon, b_lat, b_lon):
        return None
    return haversine_km(a_lat, a_lon, b_lat, b_lon)


def same_city(city_a, country_a, city_b, country_b) -> bool:
    if not city_a or not city_b or fold(city_a) != fold(city_b):
        return False
    return not (country_a and country_b and country_a.upper() != country_b.upper())


def in_area(a: tuple, b: tuple, radius_km: float) -> tuple[bool, float | None]:
    """a, b = (city, country, lat, lon). Com coordenadas usa a distância; sem elas compara a cidade."""
    d = distance_between(a[2], a[3], b[2], b[3])
    if d is not None:
        return d <= radius_km, d
    return same_city(a[0], a[1], b[0], b[1]), None


# ---------------------------------------------------------------- settings
async def get_setting(s: AsyncSession, key: str, default=None):
    row = await s.get(Setting, key)
    return default if row is None else row.value


async def set_setting(s: AsyncSession, key: str, value) -> None:
    row = await s.get(Setting, key)
    if row is None:
        s.add(Setting(key=key, value=value))
    else:
        row.value = value


async def monetization_enabled(s: AsyncSession) -> bool:
    return bool(await get_setting(s, "monetization_enabled", False))


# ---------------------------------------------------------------- usuários
async def get_or_create_user(s: AsyncSession, telegram_id: int, name: str, username: str | None, lang: str) -> tuple[User, bool]:
    user = (await s.execute(select(User).where(User.telegram_id == telegram_id))).scalar_one_or_none()
    if user:
        user.last_active_at = utcnow()
        if username != user.username:
            user.username = username
        if user.blocked_bot:
            user.blocked_bot = False
        return user, False
    total = (await s.execute(select(func.count(User.id)))).scalar_one()
    limit = int(await get_setting(s, "early_adopter_limit", 1000) or 0)
    user = User(telegram_id=telegram_id, name=(name or "")[:128], username=username, language=lang,
                early_adopter=total < limit)
    s.add(user)
    await s.flush()
    return user, True


async def user_by_ref_code(s: AsyncSession, code: str) -> User | None:
    return (await s.execute(select(User).where(User.referral_code == code))).scalar_one_or_none()


async def apply_referral(s: AsyncSession, user: User, code: str) -> User | None:
    """Só conta para contas novas, nunca para si mesmo nem para contas suspensas."""
    if user.referred_by_id or not code:
        return None
    inviter = await user_by_ref_code(s, code)
    if not inviter or inviter.id == user.id or inviter.is_banned:
        return None
    user.referred_by_id = inviter.id
    return inviter


def _valid_referral_clause():
    # Indicação válida = convidado concluiu o cadastro, aceitou os termos e não está suspenso (anti-contas falsas)
    return and_(User.onboarded.is_(True), User.is_banned.is_(False), User.accepted_terms_at.is_not(None))


async def referral_stats(s: AsyncSession, user: User) -> dict:
    total = (await s.execute(select(func.count(User.id)).where(User.referred_by_id == user.id))).scalar_one()
    valid = (await s.execute(select(func.count(User.id)).where(User.referred_by_id == user.id, _valid_referral_clause()))).scalar_one()
    top = await referral_ranking(s, 10)
    rank = next((i + 1 for i, (u, _) in enumerate(await referral_ranking(s, 1000)) if u.id == user.id), None)
    return {"total": total, "valid": valid, "top": top, "rank": rank}


async def referral_ranking(s: AsyncSession, limit: int = 10) -> list[tuple[User, int]]:
    invited = User.__table__.alias("invited")
    q = (select(User, func.count(invited.c.id).label("n"))
         .join(invited, invited.c.referred_by_id == User.id)
         .where(invited.c.onboarded.is_(True), invited.c.is_banned.is_(False), invited.c.accepted_terms_at.is_not(None),
                User.is_banned.is_(False))
         .group_by(User.id).order_by(func.count(invited.c.id).desc(), User.id).limit(limit))
    return [(u, n) for u, n in (await s.execute(q)).all()]


async def delete_user_data(s: AsyncSession, user: User) -> None:
    """Direito ao apagamento (RGPD, art. 17): remove o usuário e tudo o que lhe pertence."""
    uid = user.id
    prof = (await s.execute(select(ProviderProfile).where(ProviderProfile.user_id == uid))).scalar_one_or_none()
    conv_ids = select(Conversation.id).where(or_(Conversation.client_id == uid, Conversation.provider_user_id == uid))
    await s.execute(delete(Message).where(Message.conversation_id.in_(conv_ids)))
    await s.execute(delete(Conversation).where(or_(Conversation.client_id == uid, Conversation.provider_user_id == uid)))
    req_ids = select(ServiceRequest.id).where(ServiceRequest.client_id == uid)
    await s.execute(delete(Proposal).where(Proposal.request_id.in_(req_ids)))
    await s.execute(delete(Review).where(Review.request_id.in_(req_ids)))
    await s.execute(update(Report).where(Report.request_id.in_(req_ids)).values(request_id=None))
    await s.execute(delete(ServiceRequest).where(ServiceRequest.client_id == uid))
    await s.execute(delete(Review).where(Review.reviewer_id == uid))
    if prof:
        await s.execute(update(ServiceRequest).where(ServiceRequest.assigned_provider_id == prof.id)
                        .values(assigned_provider_id=None))
        await s.execute(delete(Proposal).where(Proposal.provider_id == prof.id))
        await s.execute(delete(Review).where(Review.provider_id == prof.id))
        await s.execute(delete(PortfolioPhoto).where(PortfolioPhoto.provider_id == prof.id))
        # o próprio perfil é apagado em cascata com o usuário (relação delete-orphan)
    await s.execute(update(Report).where(Report.reporter_id == uid).values(reporter_id=None))
    await s.execute(update(Report).where(Report.target_user_id == uid).values(target_user_id=None))
    await s.execute(update(User).where(User.referred_by_id == uid).values(referred_by_id=None))
    await s.execute(delete(Subscription).where(Subscription.user_id == uid))
    await s.execute(delete(PromotionUse).where(PromotionUse.user_id == uid))
    await s.execute(delete(FSMRecord).where(FSMRecord.key.like(f"%:{user.telegram_id}:%")))
    await s.delete(user)
    await s.flush()


async def export_user_data(s: AsyncSession, user: User) -> dict:
    """Direito de acesso/portabilidade (RGPD, art. 15 e 20)."""
    def row(o):
        return {c.name: (getattr(o, c.name).isoformat() if isinstance(getattr(o, c.name), datetime) else getattr(o, c.name))
                for c in o.__table__.columns}
    data = {"user": row(user)}
    prof = (await s.execute(select(ProviderProfile).where(ProviderProfile.user_id == user.id))).scalar_one_or_none()
    if prof:
        data["provider_profile"] = row(prof)
        data["proposals"] = [row(p) for p in (await s.execute(select(Proposal).where(Proposal.provider_id == prof.id))).scalars()]
    data["requests"] = [row(r) for r in (await s.execute(select(ServiceRequest).where(ServiceRequest.client_id == user.id))).scalars()]
    data["reviews_written"] = [row(r) for r in (await s.execute(select(Review).where(Review.reviewer_id == user.id))).scalars()]
    convs = (await s.execute(select(Conversation).where(or_(Conversation.client_id == user.id, Conversation.provider_user_id == user.id)))).scalars().all()
    data["messages_sent"] = [row(m) for m in (await s.execute(select(Message).where(Message.sender_id == user.id))).scalars()]
    data["conversations"] = [row(c) for c in convs]
    data["subscriptions"] = [row(x) for x in (await s.execute(select(Subscription).where(Subscription.user_id == user.id))).scalars()]
    return data


async def count_since(s: AsyncSession, col_user, user_id: int, col_date, since: datetime) -> int:
    return (await s.execute(select(func.count()).where(col_user == user_id, col_date >= since))).scalar_one()


# ---------------------------------------------------------------- categorias
async def list_categories(s: AsyncSession, active_only: bool = True) -> list[Category]:
    q = select(Category).order_by(Category.sort, Category.id)
    if active_only:
        q = q.where(Category.active.is_(True))
    return list((await s.execute(q)).scalars())


# ---------------------------------------------------------------- profissionais
async def get_provider(s: AsyncSession, user_id: int) -> ProviderProfile | None:
    return (await s.execute(select(ProviderProfile).where(ProviderProfile.user_id == user_id))).scalar_one_or_none()


def provider_highlighted(user: User) -> bool:
    return user.has_paid_plan()


def _rank_key(prof: ProviderProfile, user: User, dist: float | None):
    return (not provider_highlighted(user), not prof.verified, dist if dist is not None else 9_999,
            -prof.rating_avg, -prof.rating_count, -prof.jobs_done)


async def search_providers(s: AsyncSession, searcher: User, category_id: int, radius_km: int | None,
                           limit: int = 30) -> list[tuple[ProviderProfile, User, float | None]]:
    """radius_km=None → só a cidade do usuário. Prioriza destaque, verificados, proximidade e avaliação."""
    q = (select(ProviderProfile, User).join(User, User.id == ProviderProfile.user_id)
         .where(User.is_banned.is_(False), User.is_provider.is_(True), User.id != searcher.id))
    out = []
    me = (searcher.city, searcher.country, searcher.lat, searcher.lon)
    for prof, user in (await s.execute(q)).all():
        if category_id not in (prof.category_ids or []):
            continue
        them = (user.city, user.country, user.lat, user.lon)
        d = distance_between(me[2], me[3], them[2], them[3])
        if radius_km is None or d is None:
            # sem coordenadas (ou "só a minha cidade"): compara a cidade
            ok = same_city(me[0], me[1], them[0], them[1])
        else:
            # dentro da distância pedida E dentro do raio de atendimento do profissional
            ok = d <= radius_km and d <= prof.radius_km
        if ok:
            out.append((prof, user, d))
    out.sort(key=lambda x: _rank_key(x[0], x[1], x[2]))
    return out[:limit]


async def matching_providers(s: AsyncSession, req: ServiceRequest, only_notifiable: bool = True) -> list[tuple[ProviderProfile, User, float | None]]:
    """Profissionais compatíveis com um pedido: especialidade + dentro do raio deles (ou mesma cidade)."""
    q = (select(ProviderProfile, User).join(User, User.id == ProviderProfile.user_id)
         .where(User.is_banned.is_(False), User.is_provider.is_(True), User.id != req.client_id))
    if only_notifiable:
        q = q.where(ProviderProfile.notify_new_requests.is_(True), User.blocked_bot.is_(False))
    out = []
    where = (req.city, req.country, req.lat, req.lon)
    for prof, user in (await s.execute(q)).all():
        if req.category_id not in (prof.category_ids or []):
            continue
        ok, d = in_area(where, (user.city, user.country, user.lat, user.lon), prof.radius_km)
        if ok:
            out.append((prof, user, d))
    # notificações prioritárias para planos pagos (quando existirem), depois os mais próximos
    out.sort(key=lambda x: (not x[1].has_paid_plan(), x[2] if x[2] is not None else 9_999, -x[0].rating_avg))
    return out


async def open_jobs_for_provider(s: AsyncSession, prof: ProviderProfile, user: User, limit: int = 20) -> list[tuple[ServiceRequest, float | None]]:
    cats = prof.category_ids or []
    if not cats:
        return []
    q = (select(ServiceRequest).join(User, User.id == ServiceRequest.client_id)
         .where(ServiceRequest.status == "open", ServiceRequest.category_id.in_(cats),
                ServiceRequest.client_id != user.id, User.is_banned.is_(False))
         .order_by(ServiceRequest.created_at.desc()).limit(300))
    me = (user.city, user.country, user.lat, user.lon)
    out = []
    for req in (await s.execute(q)).scalars():
        ok, d = in_area((req.city, req.country, req.lat, req.lon), me, prof.radius_km)
        if ok:
            out.append((req, d))
    urg = {u: i for i, u in enumerate(reversed(URGENCIES))}
    out.sort(key=lambda x: (urg.get(x[0].urgency, 9), x[1] if x[1] is not None else 9_999))
    return out[:limit]


async def market_requests(s: AsyncSession, viewer: User, category_id: int | None = None,
                          limit: int = 300) -> list[tuple[ServiceRequest, float | None]]:
    """Mural público: todos os pedidos abertos (de qualquer lugar), os mais próximos e recentes primeiro."""
    q = (select(ServiceRequest).join(User, User.id == ServiceRequest.client_id)
         .where(ServiceRequest.status == "open", User.is_banned.is_(False))
         .order_by(ServiceRequest.created_at.desc()).limit(limit))
    if category_id:
        q = q.where(ServiceRequest.category_id == category_id)
    out = []
    for req in (await s.execute(q)).scalars():
        d = distance_between(viewer.lat, viewer.lon, req.lat, req.lon)
        if d is None and same_city(viewer.city, viewer.country, req.city, req.country):
            d = 0.0
        out.append((req, d))
    # mesma região primeiro (até 100 km), depois o resto por data
    out.sort(key=lambda x: (x[1] is None or x[1] > 100, x[1] if x[1] is not None and x[1] <= 100 else 0,
                            -x[0].created_at.timestamp()))
    return out


async def market_providers(s: AsyncSession, viewer: User, limit: int = 300) -> list[tuple[ProviderProfile, User, float | None]]:
    q = (select(ProviderProfile, User).join(User, User.id == ProviderProfile.user_id)
         .where(User.is_banned.is_(False), User.is_provider.is_(True)).limit(limit))
    out = []
    for prof, user in (await s.execute(q)).all():
        d = distance_between(viewer.lat, viewer.lon, user.lat, user.lon)
        if d is None and same_city(viewer.city, viewer.country, user.city, user.country):
            d = 0.0
        out.append((prof, user, d))
    out.sort(key=lambda x: _rank_key(x[0], x[1], x[2]))
    return out


async def recompute_rating(s: AsyncSession, provider_id: int) -> None:
    avg, n = (await s.execute(select(func.avg(Review.rating), func.count(Review.id))
                              .where(Review.provider_id == provider_id, Review.hidden.is_(False)))).one()
    prof = await s.get(ProviderProfile, provider_id)
    if prof:
        prof.rating_avg = round(float(avg or 0), 2)
        prof.rating_count = int(n or 0)


# ---------------------------------------------------------------- pedidos
async def create_request(s: AsyncSession, client: User, *, category_id: int, description: str, photos: list[str],
                         place: Place, budget: str | None, desired_date: str | None, urgency: str,
                         max_per_day: int = 10) -> ServiceRequest:
    if client.is_banned:
        raise BusinessError("banned")
    if await count_since(s, ServiceRequest.client_id, client.id, ServiceRequest.created_at, utcnow() - timedelta(days=1)) >= max_per_day:
        raise BusinessError("daily_limit")
    cat = await s.get(Category, category_id)
    if not cat or not cat.active:
        raise BusinessError("not_found")
    req = ServiceRequest(client_id=client.id, category_id=category_id, description=description.strip()[:2000],
                         photo_file_ids=photos[:5], city=place.city, country=place.country, lat=place.lat, lon=place.lon,
                         budget=(budget or None) and budget[:64], desired_date=(desired_date or None) and desired_date[:64],
                         urgency=urgency if urgency in URGENCIES else "normal")
    s.add(req)
    await s.flush()
    return req


async def create_proposal(s: AsyncSession, req: ServiceRequest, prof: ProviderProfile, provider_user: User, *,
                          price: str, availability: str, message: str, max_per_day: int = 40) -> Proposal:
    if provider_user.is_banned:
        raise BusinessError("banned")
    if req.status != "open":
        raise BusinessError("not_found")
    if req.client_id == provider_user.id:
        raise BusinessError("prop.own_request")
    exists = (await s.execute(select(Proposal.id).where(Proposal.request_id == req.id, Proposal.provider_id == prof.id))).first()
    if exists:
        raise BusinessError("prop.already")
    if await count_since(s, Proposal.provider_id, prof.id, Proposal.created_at, utcnow() - timedelta(days=1)) >= max_per_day:
        raise BusinessError("daily_limit")
    p = Proposal(request_id=req.id, provider_id=prof.id, price=price.strip()[:64], availability=availability.strip()[:255],
                 message=message.strip()[:1500])
    s.add(p)
    await s.flush()
    return p


async def proposals_for_request(s: AsyncSession, req_id: int) -> list[tuple[Proposal, ProviderProfile, User]]:
    q = (select(Proposal, ProviderProfile, User).join(ProviderProfile, ProviderProfile.id == Proposal.provider_id)
         .join(User, User.id == ProviderProfile.user_id)
         .where(Proposal.request_id == req_id, Proposal.status.in_(("pending", "accepted")), User.is_banned.is_(False)))
    rows = list((await s.execute(q)).all())

    def price_num(p: str) -> float:
        digits = "".join(c if c.isdigit() or c in ".," else " " for c in p).replace(",", ".").split()
        try:
            return float(digits[0])
        except (IndexError, ValueError):
            return 9e9
    rows.sort(key=lambda r: (r[0].status != "accepted", not r[1].verified, -r[1].rating_avg, price_num(r[0].price)))
    return rows


async def count_proposals(s: AsyncSession, req_id: int) -> int:
    return (await s.execute(select(func.count(Proposal.id)).where(Proposal.request_id == req_id,
                                                                    Proposal.status.in_(("pending", "accepted"))))).scalar_one()


async def accept_proposal(s: AsyncSession, proposal: Proposal, client: User) -> list[Proposal]:
    req = await s.get(ServiceRequest, proposal.request_id)
    if not req or req.client_id != client.id:
        raise BusinessError("not_allowed")
    if req.status != "open" or proposal.status != "pending":
        raise BusinessError("not_found")
    proposal.status = "accepted"
    req.status = "assigned"
    req.assigned_provider_id = proposal.provider_id
    req.provider_confirmed = False
    others = list((await s.execute(select(Proposal).where(Proposal.request_id == req.id, Proposal.id != proposal.id,
                                                          Proposal.status == "pending"))).scalars())
    for o in others:
        o.status = "rejected"
    await s.flush()
    return others


async def provider_respond(s: AsyncSession, req: ServiceRequest, prof: ProviderProfile, accept: bool) -> None:
    if req.assigned_provider_id != prof.id or req.status != "assigned":
        raise BusinessError("not_allowed")
    if accept:
        req.provider_confirmed = True
    else:
        prop = (await s.execute(select(Proposal).where(Proposal.request_id == req.id, Proposal.provider_id == prof.id))).scalar_one_or_none()
        if prop:
            prop.status = "withdrawn"
        # outras propostas voltam a poder ser escolhidas
        await s.execute(update(Proposal).where(Proposal.request_id == req.id, Proposal.status == "rejected").values(status="pending"))
        req.status = "open"
        req.assigned_provider_id = None
        req.provider_confirmed = False
    await s.flush()


async def complete_request(s: AsyncSession, req: ServiceRequest, client: User) -> None:
    if req.client_id != client.id:
        raise BusinessError("not_allowed")
    if req.status != "assigned" or not req.assigned_provider_id:
        raise BusinessError("not_found")
    req.status = "completed"
    req.completed_at = utcnow()
    prof = await s.get(ProviderProfile, req.assigned_provider_id)
    if prof:
        prof.jobs_done += 1
    await s.flush()


async def cancel_request(s: AsyncSession, req: ServiceRequest, client: User) -> None:
    if req.client_id != client.id:
        raise BusinessError("not_allowed")
    if req.status not in ("open", "assigned"):
        raise BusinessError("not_found")
    req.status = "cancelled"
    await s.execute(update(Proposal).where(Proposal.request_id == req.id, Proposal.status == "pending").values(status="rejected"))
    await s.flush()


# ---------------------------------------------------------------- avaliações
async def can_review(s: AsyncSession, req: ServiceRequest, user: User) -> bool:
    if req.status != "completed" or req.client_id != user.id or not req.assigned_provider_id:
        return False
    exists = (await s.execute(select(Review.id).where(Review.request_id == req.id, Review.reviewer_id == user.id))).first()
    return not exists


async def add_review(s: AsyncSession, req: ServiceRequest, user: User, rating: int, comment: str) -> Review:
    if not 1 <= int(rating) <= 5:
        raise BusinessError("rate_not_allowed")
    if not await can_review(s, req, user):
        raise BusinessError("rate_not_allowed")
    r = Review(request_id=req.id, reviewer_id=user.id, provider_id=req.assigned_provider_id, rating=int(rating),
               comment=(comment or "").strip()[:1000])
    s.add(r)
    await s.flush()
    await recompute_rating(s, req.assigned_provider_id)
    return r


async def pending_reviews(s: AsyncSession, user: User) -> list[ServiceRequest]:
    reviewed = select(Review.request_id).where(Review.reviewer_id == user.id)
    q = (select(ServiceRequest).where(ServiceRequest.client_id == user.id, ServiceRequest.status == "completed",
                                      ServiceRequest.assigned_provider_id.is_not(None), ServiceRequest.id.not_in(reviewed))
         .order_by(ServiceRequest.completed_at.desc()))
    return list((await s.execute(q)).scalars())


async def provider_reviews(s: AsyncSession, provider_id: int, limit: int = 10) -> list[Review]:
    q = (select(Review).where(Review.provider_id == provider_id, Review.hidden.is_(False))
         .order_by(Review.created_at.desc()).limit(limit))
    return list((await s.execute(q)).scalars())


async def create_report(s: AsyncSession, reporter: User, reason: str, *, kind: str = "report", target_user_id: int | None = None,
                        review_id: int | None = None, request_id: int | None = None) -> Report:
    r = Report(kind=kind, reporter_id=reporter.id, target_user_id=target_user_id, review_id=review_id,
               request_id=request_id, reason=(reason or "").strip()[:2000])
    s.add(r)
    await s.flush()
    return r


# ---------------------------------------------------------------- chat
async def get_or_create_conversation(s: AsyncSession, client_id: int, provider_user_id: int, request_id: int | None) -> Conversation:
    if client_id == provider_user_id:
        raise BusinessError("cant_message_self")
    q = select(Conversation).where(Conversation.client_id == client_id, Conversation.provider_user_id == provider_user_id)
    q = q.where(Conversation.request_id == request_id) if request_id else q.where(Conversation.request_id.is_(None))
    conv = (await s.execute(q)).scalar_one_or_none()
    if conv:
        return conv
    conv = Conversation(client_id=client_id, provider_user_id=provider_user_id, request_id=request_id)
    s.add(conv)
    await s.flush()
    return conv


def other_party(conv: Conversation, user_id: int) -> int:
    if user_id == conv.client_id:
        return conv.provider_user_id
    if user_id == conv.provider_user_id:
        return conv.client_id
    raise BusinessError("not_allowed")


async def add_message(s: AsyncSession, conv: Conversation, sender: User, text: str | None, photo: str | None) -> Message:
    other_party(conv, sender.id)  # valida participação
    m = Message(conversation_id=conv.id, sender_id=sender.id, text=(text or "")[:4000] or None, photo_file_id=photo)
    conv.last_message_at = utcnow()
    s.add(m)
    await s.flush()
    return m


async def conversations_for(s: AsyncSession, user: User) -> list[tuple[Conversation, User, int]]:
    q = (select(Conversation).where(or_(Conversation.client_id == user.id, Conversation.provider_user_id == user.id))
         .order_by(Conversation.last_message_at.desc()).limit(20))
    out = []
    for conv in (await s.execute(q)).scalars():
        other = await s.get(User, other_party(conv, user.id))
        if not other:
            continue
        unread = (await s.execute(select(func.count(Message.id)).where(Message.conversation_id == conv.id,
                                                                         Message.sender_id != user.id,
                                                                         Message.read.is_(False)))).scalar_one()
        out.append((conv, other, unread))
    return out


async def conversation_history(s: AsyncSession, conv: Conversation, reader: User, limit: int = 10) -> list[Message]:
    q = select(Message).where(Message.conversation_id == conv.id).order_by(Message.id.desc()).limit(limit)
    msgs = list(reversed(list((await s.execute(q)).scalars())))
    await s.execute(update(Message).where(Message.conversation_id == conv.id, Message.sender_id != reader.id)
                    .values(read=True))
    return msgs


async def display_name(s: AsyncSession, user: User) -> str:
    """Nome público: nome profissional, se existir; nunca o telefone nem o @username."""
    business = (await s.execute(select(ProviderProfile.business_name).where(ProviderProfile.user_id == user.id))).scalar_one_or_none()
    return business or user.name or "—"


# ---------------------------------------------------------------- planos / monetização
async def active_plans(s: AsyncSession) -> list[Plan]:
    return list((await s.execute(select(Plan).where(Plan.active.is_(True)).order_by(Plan.sort))).scalars())


async def activate_plan(s: AsyncSession, user: User, plan_code: str, days: int, *, source: str, stars: int = 0,
                        charge_id: str | None = None, consent: bool = False) -> Subscription:
    start = max(utcnow(), user.plan_until or utcnow()) if user.plan_code == plan_code else utcnow()
    end = start + timedelta(days=days)
    user.plan_code, user.plan_until = plan_code, end
    sub = Subscription(user_id=user.id, plan_code=plan_code, source=source, stars_amount=stars, telegram_charge_id=charge_id,
                       consent_at=utcnow() if consent else None, starts_at=start, ends_at=end)
    s.add(sub)
    await s.flush()
    return sub


async def redeem_promo(s: AsyncSession, user: User, code: str) -> Subscription:
    promo = (await s.execute(select(Promotion).where(func.upper(Promotion.code) == (code or "").strip().upper()))).scalar_one_or_none()
    if not promo or not promo.active or promo.uses >= promo.max_uses:
        raise BusinessError("promo_invalid")
    used = (await s.execute(select(PromotionUse.id).where(PromotionUse.promotion_id == promo.id, PromotionUse.user_id == user.id))).first()
    if used:
        raise BusinessError("promo_invalid")
    promo.uses += 1
    s.add(PromotionUse(promotion_id=promo.id, user_id=user.id))
    return await activate_plan(s, user, promo.plan_code, promo.days, source="promo")


async def expire_plans(s: AsyncSession) -> int:
    res = await s.execute(update(User).where(User.plan_code != "free", User.plan_until.is_not(None), User.plan_until < utcnow())
                          .values(plan_code="free", plan_until=None))
    return res.rowcount or 0


# ---------------------------------------------------------------- estatísticas
async def stats(s: AsyncSession) -> dict:
    now = utcnow()

    async def c(q):
        return (await s.execute(q)).scalar_one()
    return {
        "users": await c(select(func.count(User.id))),
        "providers": await c(select(func.count(User.id)).where(User.is_provider.is_(True))),
        "clients": await c(select(func.count(User.id)).where(User.is_provider.is_(False))),
        "active_24h": await c(select(func.count(User.id)).where(User.last_active_at >= now - timedelta(days=1))),
        "active_7d": await c(select(func.count(User.id)).where(User.last_active_at >= now - timedelta(days=7))),
        "new_7d": await c(select(func.count(User.id)).where(User.created_at >= now - timedelta(days=7))),
        "banned": await c(select(func.count(User.id)).where(User.is_banned.is_(True))),
        "requests": await c(select(func.count(ServiceRequest.id))),
        "requests_open": await c(select(func.count(ServiceRequest.id)).where(ServiceRequest.status == "open")),
        "requests_completed": await c(select(func.count(ServiceRequest.id)).where(ServiceRequest.status == "completed")),
        "proposals": await c(select(func.count(Proposal.id))),
        "messages": await c(select(func.count(Message.id))),
        "reviews": await c(select(func.count(Review.id))),
        "reports_open": await c(select(func.count(Report.id)).where(Report.status == "open")),
        "paid_users": await c(select(func.count(User.id)).where(User.plan_code != "free")),
        "revenue_stars": await c(select(func.coalesce(func.sum(Subscription.stars_amount), 0)).where(Subscription.source == "stars")),
        "revenue_stars_30d": await c(select(func.coalesce(func.sum(Subscription.stars_amount), 0))
                                     .where(Subscription.source == "stars", Subscription.created_at >= now - timedelta(days=30))),
    }
