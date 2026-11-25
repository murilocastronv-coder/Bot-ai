"""Bot do Telegram ServiceConnect (aiogram 3): menus, cadastros, pedidos, propostas, chat, avaliações, convites."""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict, deque
from html import escape as e
from typing import Any, Awaitable, Callable
from urllib.parse import quote

from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (BotCommand, BufferedInputFile, CallbackQuery, ChatMemberUpdated, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, LabeledPrice, Message, PreCheckoutQuery,
                           ReplyKeyboardMarkup, TelegramObject, Update)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

import services as sv
from config import settings
from i18n import LANG_NAMES, LANGS, MENU_LOOKUP, PLAN_NAMES, all_variants, norm_lang, t
from models import (Category, Conversation, Plan, PortfolioPhoto, Proposal, ProviderProfile, Review, ServiceRequest,
                    User, utcnow)
from storage import DBStorage

log = logging.getLogger("serviceconnect.bot")
router = Router(name="main")


# ======================================================================= estados
class Onb(StatesGroup):
    terms = State()
    name = State()
    role = State()
    location = State()


class Loc(StatesGroup):
    city = State()


class Req(StatesGroup):
    category = State()
    description = State()
    photos = State()
    city = State()
    budget = State()
    date = State()
    urgency = State()
    confirm = State()


class Prop(StatesGroup):
    price = State()
    availability = State()
    message = State()


class Prov(StatesGroup):
    business = State()
    photo = State()
    description = State()
    categories = State()
    radius = State()
    price_type = State()
    rate = State()
    availability = State()


class Port(StatesGroup):
    photos = State()


class Chat(StatesGroup):
    active = State()


class Rate(StatesGroup):
    comment = State()


class Rep(StatesGroup):
    reason = State()


class Sup(StatesGroup):
    text = State()


class EditName(StatesGroup):
    name = State()


class Promo(StatesGroup):
    code = State()


# ======================================================================= middlewares
class ContextMiddleware(BaseMiddleware):
    """Abre a sessão do banco, carrega/cria o usuário, aplica bloqueios e faz commit no final."""

    def __init__(self, database):
        self.db = database

    async def __call__(self, handler: Callable[[TelegramObject, dict], Awaitable[Any]], event: TelegramObject, data: dict) -> Any:
        tg_user = data.get("event_from_user")
        async with self.db.session() as s:
            data["s"] = s
            if tg_user and not tg_user.is_bot:
                user, created = await sv.get_or_create_user(
                    s, tg_user.id, tg_user.full_name, tg_user.username, norm_lang(tg_user.language_code))
                data["user"], data["lang"], data["is_new"] = user, user.language, created
                # grava já (cadastro/última atividade) e liberta a transação antes do handler
                await s.commit()
                if user.is_banned:
                    await _tell(event, t("banned", user.language))
                    return None
            result = await handler(event, data)
            await s.commit()
            return result


class ThrottleMiddleware(BaseMiddleware):
    """Anti-spam: limita ações por minuto por usuário."""

    def __init__(self, per_minute: int):
        self.per_minute = per_minute
        self.hits: dict[int, deque] = defaultdict(deque)
        self.warned: dict[int, float] = {}

    async def __call__(self, handler, event, data):
        tg_user = data.get("event_from_user")
        if tg_user and not isinstance(getattr(event, "pre_checkout_query", None), PreCheckoutQuery):
            now = time.monotonic()
            q = self.hits[tg_user.id]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= self.per_minute:
                if now - self.warned.get(tg_user.id, 0) > 30:
                    self.warned[tg_user.id] = now
                    await _tell(event, t("slow_down", norm_lang(tg_user.language_code)))
                return None
            q.append(now)
            if len(self.hits) > 50_000:
                self.hits.clear()
        return await handler(event, data)


async def _tell(event: TelegramObject, text: str) -> None:
    try:
        if isinstance(event, Update):
            if event.message:
                await event.message.answer(text)
            elif event.callback_query:
                await event.callback_query.answer(text, show_alert=True)
    except Exception:  # noqa: BLE001
        pass


# ======================================================================= utilitários
def menu_kb(lang: str) -> ReplyKeyboardMarkup:
    keys = ["menu.market", "menu.find", "menu.publish", "menu.jobs", "menu.profile", "menu.requests", "menu.messages",
            "menu.reviews", "menu.location", "menu.invite", "menu.language", "menu.support"]
    rows = [[KeyboardButton(text=t(keys[i], lang)) for i in range(j, min(j + 2, len(keys)))] for j in range(0, len(keys), 2)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, is_persistent=True)


def ikb(*rows: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """rows de (texto, callback_data) ou (texto, 'url:https://...')."""
    out = []
    for row in rows:
        btns = []
        for text, data in row:
            if data.startswith("url:"):
                btns.append(InlineKeyboardButton(text=text, url=data[4:]))
            else:
                btns.append(InlineKeyboardButton(text=text, callback_data=data))
        out.append(btns)
    return InlineKeyboardMarkup(inline_keyboard=out)


def cancel_kb(lang: str) -> InlineKeyboardMarkup:
    return ikb([(t("btn.cancel", lang), "cancel")])


def skip_cancel_kb(lang: str, skip: str = "skip") -> InlineKeyboardMarkup:
    return ikb([(t("btn.skip", lang), skip), (t("btn.cancel", lang), "cancel")])


def location_kb(lang: str, extra: str | None = None) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text=t("btn.share_location", lang), request_location=True)]]
    if extra:
        rows.append([KeyboardButton(text=extra)])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def public_url(path: str, lang: str) -> str:
    base = settings.webhook_base_url or "https://t.me"
    return f"{base}{path}?lang={lang}"


async def deep_link(bot: Bot, payload: str) -> str:
    me = await bot.me()
    return f"https://t.me/{me.username}?start={payload}"


def share_url(link: str, text: str) -> str:
    return f"https://t.me/share/url?url={quote(link)}&text={quote(text)}"


def stars(n: float) -> str:
    return "★" * int(round(n)) + "☆" * (5 - int(round(n)))


def fmt_km(d: float | None, lang: str) -> str:
    if d is None:
        return ""
    return t("km_away", lang, km="<1" if d < 1 else f"{d:.0f}")


def cut(text: str | None, n: int = 300) -> str:
    text = text or ""
    return text if len(text) <= n else text[: n - 1] + "…"


def price_text(prof: ProviderProfile, lang: str) -> str:
    if prof.price_type == "hourly" and prof.hourly_rate:
        rate = f"{prof.hourly_rate:g}"
        return t("price_hourly", lang, rate=rate, cur=prof.currency)
    return t("price_quote", lang)


def rating_text(prof: ProviderProfile, lang: str) -> str:
    return f"{prof.rating_avg:.1f} ({prof.rating_count})" if prof.rating_count else t("no_reviews_yet", lang)


def badges(prof: ProviderProfile, user: User, lang: str) -> str:
    b = []
    if prof.verified:
        b.append(t("verified", lang))
    if sv.provider_highlighted(user):
        b.append(t("sponsored", lang))
    return " ".join(b)


async def cat_names(s, ids: list[int], lang: str) -> str:
    if not ids:
        return "—"
    cats = (await s.execute(select(Category).where(Category.id.in_(ids)))).scalars()
    return ", ".join(c.label(lang) for c in cats)


async def provider_card(s, prof: ProviderProfile, user: User, lang: str) -> str:
    return t("provider_card", lang, name=e(prof.business_name or user.name), badges=badges(prof, user, lang),
             rating=rating_text(prof, lang), jobs=prof.jobs_done, city=e(user.city or "—"), radius=prof.radius_km,
             price=e(price_text(prof, lang)), availability=e(prof.availability or "—"),
             description=e(cut(prof.description, 700)), cats=await cat_names(s, prof.category_ids or [], lang))


def urgency_label(u: str, lang: str) -> str:
    return t(f"urg.{u}", lang) if u in sv.URGENCIES else u


async def request_card(s, req: ServiceRequest, lang: str, dist: float | None = None) -> str:
    cat = await s.get(Category, req.category_id)
    ns = t("not_specified", lang)
    return t("req.card", lang, id=req.id, cat=cat.label(lang) if cat else "—", desc=e(cut(req.description, 600)),
             city=e(req.city or "—"), dist=f"({fmt_km(dist, lang)})" if dist is not None else "",
             budget=e(req.budget or ns), date=e(req.desired_date or ns), urgency=urgency_label(req.urgency, lang),
             proposals=await sv.count_proposals(s, req.id), created=req.created_at.strftime("%d/%m %H:%M"))


async def proposal_card(prop: Proposal, prof: ProviderProfile, user: User, lang: str) -> str:
    return t("prop.card", lang, name=e(prof.business_name or user.name), badges=badges(prof, user, lang),
             rating=rating_text(prof, lang), jobs=prof.jobs_done, price=e(prop.price),
             availability=e(prop.availability or "—"), message=e(cut(prop.message, 600) or "—"))


async def notify(bot: Bot, s, user: User, text: str, kb: InlineKeyboardMarkup | None = None, photo: str | None = None) -> bool:
    """Envia uma notificação; marca o usuário se ele bloqueou o bot."""
    if user.blocked_bot or user.is_banned:
        return False
    for attempt in range(2):
        try:
            if photo:
                await bot.send_photo(user.telegram_id, photo, caption=text[:1024], reply_markup=kb)
            else:
                await bot.send_message(user.telegram_id, text, reply_markup=kb, disable_web_page_preview=True)
            return True
        except TelegramRetryAfter as ex:
            await asyncio.sleep(min(ex.retry_after, 10))
        except TelegramForbiddenError:
            user.blocked_bot = True
            return False
        except TelegramBadRequest as ex:
            log.warning("notify %s failed: %s", user.id, ex)
            return False
    return False


async def admin_ids(s=None) -> set[int]:
    """IDs configurados + IDs dos @usernames de ADMIN_USERNAMES que já usaram o bot."""
    ids = set(settings.admin_telegram_ids)
    if s is not None and settings.admin_usernames:
        from sqlalchemy import func
        rows = await s.execute(select(User.telegram_id).where(func.lower(User.username).in_(settings.admin_usernames)))
        ids.update(r[0] for r in rows)
    return ids


def is_admin_user(tg_user) -> bool:
    return tg_user is not None and (tg_user.id in settings.admin_telegram_ids
                                    or (tg_user.username or "").lower() in settings.admin_usernames)


async def notify_admins(bot: Bot, text: str, s=None) -> None:
    for admin_id in await admin_ids(s):
        try:
            await bot.send_message(admin_id, text, disable_web_page_preview=True)
        except Exception as ex:  # noqa: BLE001
            log.warning("admin notify failed: %s", ex)


def parts(c: CallbackQuery) -> list[str]:
    return (c.data or "").split(":")


def as_int(v: str) -> int:
    try:
        return int(v)
    except (TypeError, ValueError):
        return -1


async def show_menu(m: Message, lang: str, text: str | None = None) -> None:
    await m.answer(text or t("menu.title", lang), reply_markup=menu_kb(lang))


async def need_onboarded(m: Message, user: User, lang: str) -> bool:
    if not user.onboarded:
        await m.answer(t("need_onboarding", lang))
        return False
    return True


def text_ok(m: Message, lang: str, max_len: int) -> str | None:
    txt = (m.text or "").strip()
    return txt if txt and len(txt) <= max_len else None


# ======================================================================= /start, onboarding
@router.message(CommandStart())
async def cmd_start(m: Message, command: CommandObject, state: FSMContext, s, user: User, lang: str, is_new: bool, bot: Bot):
    payload = (command.args or "").strip()
    await state.clear()
    if payload and (is_new or not user.onboarded):
        code = payload[4:] if payload.startswith("ref_") else payload
        if not payload.startswith(("p_", "r_")):
            await sv.apply_referral(s, user, code)
    if payload.startswith(("p_", "r_")):
        await state.update_data(pending=payload)
    if not user.accepted_terms_at:
        await state.set_state(Onb.terms)
        await send_welcome(m, lang)
        return
    if not user.onboarded:
        await ask_name(m, user, lang, state)
        return
    await show_menu(m, lang)
    if payload.startswith(("p_", "r_")):
        await open_deep_link(m, payload, s, user, lang, bot)


async def send_welcome(m: Message, lang: str) -> None:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=t("btn.accept_terms", lang), callback_data="terms:ok"))
    kb.row(*[InlineKeyboardButton(text=LANG_NAMES[code], callback_data=f"lang:{code}") for code in LANGS])
    await m.answer(t("welcome", lang, terms=public_url("/terms", lang), privacy=public_url("/privacy", lang)),
                   reply_markup=kb.as_markup(), disable_web_page_preview=True)


async def ask_name(m: Message, user: User, lang: str, state: FSMContext) -> None:
    await state.set_state(Onb.name)
    rows = [[KeyboardButton(text=user.name[:64])]] if user.name else []
    await m.answer(t("ask_name", lang), reply_markup=ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)
                   if rows else None)


@router.callback_query(F.data == "terms:ok")
async def cb_terms(c: CallbackQuery, state: FSMContext, user: User, lang: str):
    user.accepted_terms_at = user.accepted_terms_at or utcnow()
    await c.answer("✅")
    await ask_name(c.message, user, lang, state)


@router.message(Onb.terms)
async def onb_terms_text(m: Message, lang: str):
    await send_welcome(m, lang)


@router.message(Onb.name)
async def onb_name(m: Message, state: FSMContext, user: User, lang: str):
    name = text_ok(m, lang, 64)
    if not name:
        await m.answer(t("too_long", lang, n=64) if m.text else t("send_text", lang))
        return
    user.name = name
    await state.set_state(Onb.role)
    await m.answer(t("ask_role", lang), reply_markup=ikb([(t("btn.role_client", lang), "role:client")],
                                                          [(t("btn.role_provider", lang), "role:provider")]))


@router.callback_query(Onb.role, F.data.startswith("role:"))
async def onb_role(c: CallbackQuery, state: FSMContext, lang: str):
    await state.update_data(role=parts(c)[1])
    await state.set_state(Onb.location)
    await c.answer()
    await c.message.answer(t("ask_location", lang), reply_markup=location_kb(lang))


async def save_location_message(m: Message, s, user: User, lang: str) -> bool:
    """Trata localização partilhada ou nome da cidade. Retorna True quando a cidade fica definida."""
    if m.location:
        user.lat, user.lon = round(m.location.latitude, 4), round(m.location.longitude, 4)
        city = await sv.nearest_city(s, user.lat, user.lon)
        if city:
            user.city, user.country = city.name, city.country
            return True
        await m.answer(t("location_city_unknown", lang))
        return False
    raw = text_ok(m, lang, 120)
    if not raw:
        await m.answer(t("send_text", lang))
        return False
    place = await sv.resolve_city(s, raw)
    user.city, user.country = place.city, place.country or user.country
    if place.lat is not None:
        # coordenadas da cidade, exceto se o usuário já partilhou a posição dentro dela
        if user.lat is None or sv.haversine_km(user.lat, user.lon, place.lat, place.lon) > 60:
            user.lat, user.lon = place.lat, place.lon
    return True


@router.message(Onb.location)
async def onb_location(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    if not await save_location_message(m, s, user, lang):
        return
    data = await state.get_data()
    was_onboarded = user.onboarded
    user.onboarded = True
    await state.clear()
    await m.answer(t("location_saved", lang, city=e(user.city)))
    await show_menu(m, lang, t("onboard_done", lang, name=e(user.name)))
    if not was_onboarded and user.referred_by_id:
        inviter = await s.get(User, user.referred_by_id)
        if inviter:
            await notify(bot, s, inviter, t("referral_joined", inviter.language))
    if data.get("role") == "provider":
        await start_provider_flow(m, state, s, user, lang)
    elif data.get("pending"):
        await open_deep_link(m, data["pending"], s, user, lang, bot)


async def open_deep_link(m: Message, payload: str, s, user: User, lang: str, bot: Bot) -> None:
    kind, _, raw_id = payload.partition("_")
    if kind == "p":
        prof = await s.get(ProviderProfile, as_int(raw_id))
        if prof:
            await send_provider_profile(m, s, prof, user, lang, bot)
    elif kind == "r":
        req = await s.get(ServiceRequest, as_int(raw_id))
        if req:
            await send_job_detail(m, s, req, user, lang)


# ======================================================================= comandos gerais
@router.message(Command("cancel"))
@router.message(Command("menu"))
async def cmd_menu(m: Message, state: FSMContext, user: User, lang: str):
    await state.clear()
    if not await need_onboarded(m, user, lang):
        return
    await show_menu(m, lang)


@router.message(Command("help"))
async def cmd_help(m: Message, lang: str):
    await m.answer(t("help", lang))


@router.callback_query(F.data == "cancel")
async def cb_cancel(c: CallbackQuery, state: FSMContext, lang: str):
    await state.clear()
    await c.answer(t("cancelled", lang))
    await show_menu(c.message, lang, t("cancelled", lang))


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang(c: CallbackQuery, state: FSMContext, user: User):
    code = parts(c)[1]
    if code not in LANGS:
        await c.answer()
        return
    user.language = code
    await c.answer(t("language_set", code))
    if not user.accepted_terms_at:
        await send_welcome(c.message, code)
    elif user.onboarded:
        await state.clear()
        await show_menu(c.message, code, t("language_set", code))


# ======================================================================= menu principal (prioritário)
@router.message(F.text.in_(set(MENU_LOOKUP)))
async def on_menu(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    await state.clear()
    if not await need_onboarded(m, user, lang):
        return
    key = MENU_LOOKUP[m.text]
    handler = {
        "menu.market": menu_market, "menu.find": menu_find, "menu.publish": menu_publish, "menu.jobs": menu_jobs, "menu.profile": menu_profile,
        "menu.requests": menu_requests, "menu.messages": menu_messages, "menu.reviews": menu_reviews,
        "menu.location": menu_location, "menu.invite": menu_invite, "menu.language": menu_language,
        "menu.support": menu_support,
    }[key]
    await handler(m=m, state=state, s=s, user=user, lang=lang, bot=bot)


async def categories_kb(s, lang: str, prefix: str, selected: set[int] | None = None, done: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for cat in await sv.list_categories(s):
        mark = "✅ " if selected and cat.id in selected else ""
        kb.button(text=mark + cat.label(lang), callback_data=f"{prefix}:{cat.id}")
    kb.adjust(2)
    if done:
        kb.row(InlineKeyboardButton(text=t("btn.done", lang), callback_data=f"{prefix}:done"))
    kb.row(InlineKeyboardButton(text=t("btn.cancel", lang), callback_data="cancel"))
    return kb.as_markup()


# ----------------------------------------------------------------------- 🔎 encontrar profissional
async def menu_find(m: Message, s, lang: str, **_):
    await m.answer(t("choose_category", lang), reply_markup=await categories_kb(s, lang, "fc"))


@router.callback_query(F.data.startswith("fc:"))
async def cb_find_category(c: CallbackQuery, lang: str):
    cat_id = as_int(parts(c)[1])
    kb = InlineKeyboardBuilder()
    for r in sv.RADII:
        kb.button(text=f"{r} km", callback_data=f"fr:{cat_id}:{r}:0")
    kb.adjust(5)
    kb.row(InlineKeyboardButton(text=t("radius_city", lang), callback_data=f"fr:{cat_id}:0:0"))
    await c.answer()
    await c.message.answer(t("choose_radius", lang), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("fr:"))
async def cb_find_results(c: CallbackQuery, s, user: User, lang: str):
    _, cat_id, radius, offset = (parts(c) + ["0"])[:4]
    cat_id, radius, offset = as_int(cat_id), as_int(radius), max(0, as_int(offset))
    results = await sv.search_providers(s, user, cat_id, radius or None, limit=100)
    await c.answer()
    if not results:
        await c.message.answer(t("no_providers", lang))
        return
    page = results[offset:offset + 10]
    lines = [t("providers_found", lang, n=len(results))]
    kb = InlineKeyboardBuilder()
    for i, (prof, pu, d) in enumerate(page, start=offset + 1):
        badge = " ✅" if prof.verified else ""
        rating = f"⭐{prof.rating_avg:.1f} ({prof.rating_count})" if prof.rating_count else "🆕"
        lines.append(f"{i}. <b>{e(prof.business_name or pu.name)}</b>{badge} · {rating} · {e(price_text(prof, lang))}"
                     + (f" · {fmt_km(d, lang)}" if d is not None else ""))
        kb.button(text=f"{i}. {cut(prof.business_name or pu.name, 30)}", callback_data=f"pv:{prof.id}")
    kb.adjust(2)
    if offset + 10 < len(results):
        kb.row(InlineKeyboardButton(text=t("btn.more", lang), callback_data=f"fr:{cat_id}:{radius}:{offset + 10}"))
    await c.message.answer("\n".join(lines), reply_markup=kb.as_markup())


async def send_provider_profile(m: Message, s, prof: ProviderProfile, viewer: User, lang: str, bot: Bot) -> None:
    pu = await s.get(User, prof.user_id)
    if not pu or pu.is_banned:
        await m.answer(t("not_found", lang))
        return
    if viewer.id != pu.id:
        prof.profile_views += 1
    link = await deep_link(bot, f"p_{prof.id}")
    rows = []
    if viewer.id != pu.id:
        rows.append([(t("btn.contact", lang), f"ct:{pu.id}")])
    rows.append([(t("btn.portfolio", lang), f"pf:{prof.id}"), (t("btn.see_reviews", lang), f"rv:{prof.id}")])
    rows.append([(t("btn.share", lang), "url:" + share_url(link, prof.business_name or pu.name))]
                + ([(t("btn.report", lang), f"rp:u:{pu.id}")] if viewer.id != pu.id else []))
    text = await provider_card(s, prof, pu, lang)
    if prof.photo_file_id and len(text) <= 1024:
        await m.answer_photo(prof.photo_file_id, caption=text, reply_markup=ikb(*rows))
    else:
        await m.answer(text, reply_markup=ikb(*rows), disable_web_page_preview=True)


@router.callback_query(F.data.startswith("pv:"))
async def cb_provider_view(c: CallbackQuery, s, user: User, lang: str, bot: Bot):
    prof = await s.get(ProviderProfile, as_int(parts(c)[1]))
    await c.answer()
    if not prof:
        await c.message.answer(t("not_found", lang))
        return
    await send_provider_profile(c.message, s, prof, user, lang, bot)


@router.callback_query(F.data.startswith("pf:"))
async def cb_portfolio(c: CallbackQuery, s, lang: str):
    photos = (await s.execute(select(PortfolioPhoto).where(PortfolioPhoto.provider_id == as_int(parts(c)[1]))
                              .order_by(PortfolioPhoto.id))).scalars().all()
    await c.answer()
    if not photos:
        await c.message.answer(t("portfolio_empty", lang))
        return
    from aiogram.types import InputMediaPhoto
    await c.message.answer_media_group([InputMediaPhoto(media=p.file_id) for p in photos[:10]])


@router.callback_query(F.data.startswith("rv:"))
async def cb_reviews_of(c: CallbackQuery, s, lang: str):
    prof = await s.get(ProviderProfile, as_int(parts(c)[1]))
    await c.answer()
    if not prof:
        return
    reviews = await sv.provider_reviews(s, prof.id)
    if not reviews:
        await c.message.answer(t("reviews_none", lang))
        return
    lines = [t("reviews_received", lang, avg=f"{prof.rating_avg:.1f}", n=prof.rating_count)]
    kb = InlineKeyboardBuilder()
    for r in reviews:
        lines.append(f"\n{stars(r.rating)} · {r.created_at:%d/%m/%Y}\n{e(cut(r.comment, 300))}")
        kb.button(text=f"🚩 {r.created_at:%d/%m} {stars(r.rating)}", callback_data=f"rp:r:{r.id}")
    kb.adjust(2)
    await c.message.answer("\n".join(lines), reply_markup=kb.as_markup())


# ----------------------------------------------------------------------- 📢 publicar pedido
async def menu_publish(m: Message, state: FSMContext, s, lang: str, **_):
    await state.set_state(Req.category)
    await m.answer(t("choose_category", lang), reply_markup=await categories_kb(s, lang, "pc"))


@router.callback_query(Req.category, F.data.startswith("pc:"))
async def req_category(c: CallbackQuery, state: FSMContext, s, lang: str):
    cat = await s.get(Category, as_int(parts(c)[1]))
    await c.answer()
    if not cat or not cat.active:
        return
    await state.update_data(category_id=cat.id, photos=[])
    await state.set_state(Req.description)
    await c.message.answer(f"{cat.label(lang)}\n\n" + t("req.ask_description", lang), reply_markup=cancel_kb(lang))


@router.message(Req.description)
async def req_description(m: Message, state: FSMContext, lang: str):
    txt = (m.text or "").strip()
    if len(txt) < 5:
        await m.answer(t("req.ask_description", lang))
        return
    if len(txt) > 2000:
        await m.answer(t("too_long", lang, n=2000))
        return
    await state.update_data(description=txt)
    await state.set_state(Req.photos)
    await m.answer(t("req.ask_photos", lang), reply_markup=ikb([(t("btn.done", lang), "rq:photos")], [(t("btn.cancel", lang), "cancel")]))


@router.message(Req.photos, F.photo)
async def req_photo(m: Message, state: FSMContext, lang: str):
    data = await state.get_data()
    photos = data.get("photos", [])
    if len(photos) >= 5:
        return
    photos.append(m.photo[-1].file_id)
    await state.update_data(photos=photos)
    await m.answer(t("req.photo_added", lang, n=len(photos)), reply_markup=ikb([(t("btn.done", lang), "rq:photos")]))


@router.message(Req.photos)
async def req_photo_other(m: Message, lang: str):
    await m.answer(t("req.ask_photos", lang), reply_markup=ikb([(t("btn.done", lang), "rq:photos")]))


@router.callback_query(Req.photos, F.data == "rq:photos")
async def req_photos_done(c: CallbackQuery, state: FSMContext, user: User, lang: str):
    await state.set_state(Req.city)
    await c.answer()
    rows = [[KeyboardButton(text=f"🏙 {user.city}")]] if user.city else []
    await c.message.answer(t("req.ask_city", lang),
                           reply_markup=ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True) if rows else None)


@router.message(Req.city)
async def req_city(m: Message, state: FSMContext, s, user: User, lang: str):
    raw = text_ok(m, lang, 120)
    if not raw:
        await m.answer(t("req.ask_city", lang))
        return
    raw = raw.removeprefix("🏙").strip()
    if user.city and sv.fold(raw) == sv.fold(user.city):
        place = sv.Place(user.city, user.country, user.lat, user.lon)
    else:
        place = await sv.resolve_city(s, raw)
    await state.update_data(place=[place.city, place.country, place.lat, place.lon])
    await state.set_state(Req.budget)
    await m.answer(t("req.ask_budget", lang), reply_markup=skip_cancel_kb(lang, "rq:skip"))


@router.message(Req.budget)
async def req_budget(m: Message, state: FSMContext, lang: str):
    txt = text_ok(m, lang, 64)
    if not txt:
        await m.answer(t("too_long", lang, n=64))
        return
    await state.update_data(budget=txt)
    await ask_req_date(m, state, lang)


async def ask_req_date(m: Message, state: FSMContext, lang: str):
    await state.set_state(Req.date)
    await m.answer(t("req.ask_date", lang), reply_markup=skip_cancel_kb(lang, "rq:skip"))


@router.message(Req.date)
async def req_date(m: Message, state: FSMContext, lang: str):
    txt = text_ok(m, lang, 64)
    if not txt:
        await m.answer(t("too_long", lang, n=64))
        return
    await state.update_data(date=txt)
    await ask_req_urgency(m, state, lang)


async def ask_req_urgency(m: Message, state: FSMContext, lang: str):
    await state.set_state(Req.urgency)
    kb = InlineKeyboardBuilder()
    for u in sv.URGENCIES:
        kb.button(text=t(f"urg.{u}", lang), callback_data=f"ru:{u}")
    kb.adjust(2)
    await m.answer(t("req.ask_urgency", lang), reply_markup=kb.as_markup())


@router.callback_query(StateFilter(Req.budget, Req.date), F.data == "rq:skip")
async def req_skip(c: CallbackQuery, state: FSMContext, lang: str):
    await c.answer()
    if await state.get_state() == Req.budget.state:
        await ask_req_date(c.message, state, lang)
    else:
        await ask_req_urgency(c.message, state, lang)


@router.callback_query(Req.urgency, F.data.startswith("ru:"))
async def req_urgency(c: CallbackQuery, state: FSMContext, s, lang: str):
    urgency = parts(c)[1]
    await state.update_data(urgency=urgency if urgency in sv.URGENCIES else "normal")
    data = await state.get_data()
    cat = await s.get(Category, data["category_id"])
    ns = t("not_specified", lang)
    await state.set_state(Req.confirm)
    await c.answer()
    await c.message.answer(
        t("req.summary", lang, cat=cat.label(lang) if cat else "—", desc=e(cut(data["description"], 800)),
          photos=len(data.get("photos", [])), city=e(data["place"][0]), budget=e(data.get("budget") or ns),
          date=e(data.get("date") or ns), urgency=urgency_label(data["urgency"], lang)),
        reply_markup=ikb([(t("btn.confirm", lang), "rq:confirm"), (t("btn.cancel", lang), "cancel")]))


@router.callback_query(Req.confirm, F.data == "rq:confirm")
async def req_confirm(c: CallbackQuery, state: FSMContext, s, user: User, lang: str, bot: Bot):
    data = await state.get_data()
    await state.clear()
    try:
        req = await sv.create_request(
            s, user, category_id=data["category_id"], description=data["description"], photos=data.get("photos", []),
            place=sv.Place(*data["place"]), budget=data.get("budget"), desired_date=data.get("date"),
            urgency=data.get("urgency", "normal"), max_per_day=settings.max_requests_per_day)
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    await c.answer("✅")
    await s.commit()
    n = await notify_new_request(bot, s, req)
    link = await deep_link(bot, f"r_{req.id}")
    await c.message.answer(t("req.published", lang, id=req.id, n=n),
                           reply_markup=ikb([(t("btn.share_request", lang), "url:" + share_url(link, cut(req.description, 120)))]))
    await show_menu(c.message, lang)


async def notify_new_request(bot: Bot, s, req: ServiceRequest) -> int:
    """Envia o pedido aos profissionais compatíveis (respeitando as preferências de notificação)."""
    sent = 0
    for prof, pu, d in (await sv.matching_providers(s, req))[: settings.max_notifications_per_request]:
        lang = pu.language
        text = t("new_request_notify", lang) + "\n\n" + await request_card(s, req, lang, d)
        kb = ikb([(t("btn.send_proposal", lang), f"pp:{req.id}")],
                 [(t("btn.message_client", lang), f"cq:{req.id}"), ("🔍", f"jb:{req.id}")])
        if await notify(bot, s, pu, text, kb):
            sent += 1
        await asyncio.sleep(0.04)  # respeita os limites do Telegram
    req.notified_count = sent
    return sent


# ----------------------------------------------------------------------- 🛒 marketplace (mural público)
async def menu_market(m: Message, lang: str, **_):
    await m.answer(t("market.title", lang), reply_markup=ikb([(t("market.btn_requests", lang), "mk:r:0:0")],
                                                             [(t("market.btn_providers", lang), "mk:p:0")],
                                                             [(t("market.btn_filter", lang), "mk:f")]))


@router.callback_query(F.data == "mk:f")
async def cb_market_filter(c: CallbackQuery, s, lang: str):
    await c.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text=t("market.btn_all", lang), callback_data="mk:r:0:0")
    for cat in await sv.list_categories(s):
        kb.button(text=cat.label(lang), callback_data=f"mk:r:{cat.id}:0")
    kb.adjust(2)
    await c.message.answer(t("choose_category", lang), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mk:r:"))
async def cb_market_requests(c: CallbackQuery, s, user: User, lang: str):
    _, _, cat_id, offset = (parts(c) + ["0", "0"])[:4]
    cat_id, offset = max(0, as_int(cat_id)), max(0, as_int(offset))
    cat = await s.get(Category, cat_id) if cat_id else None
    cat_txt = f" · {cat.label(lang)}" if cat else ""
    rows = await sv.market_requests(s, user, cat_id or None)
    await c.answer()
    if not rows:
        await c.message.answer(t("market.no_requests", lang, cat=cat_txt),
                               reply_markup=ikb([(t("market.btn_filter", lang), "mk:f")]))
        return
    page = rows[offset:offset + 10]
    lines = [t("market.requests_title", lang, n=len(rows), cat=cat_txt)]
    kb = InlineKeyboardBuilder()
    for req, d in page:
        rc = await s.get(Category, req.category_id)
        where = e(req.city or "—") + (f" ({fmt_km(d, lang)})" if d else "")
        lines.append(f"\n<b>#{req.id}</b> {rc.label(lang) if rc else ''} · {urgency_label(req.urgency, lang)}\n"
                     f"📝 {e(cut(req.description, 120))}\n📍 {where} · 💶 {e(req.budget or t('not_specified', lang))}"
                     f" · 🕒 {req.created_at:%d/%m}")
        kb.button(text=f"#{req.id} {cut(req.description, 24)}", callback_data=f"jb:{req.id}")
    kb.adjust(2)
    nav = []
    if offset + 10 < len(rows):
        nav.append(InlineKeyboardButton(text=t("btn.more", lang), callback_data=f"mk:r:{cat_id}:{offset + 10}"))
    nav.append(InlineKeyboardButton(text=t("market.btn_filter", lang), callback_data="mk:f"))
    kb.row(*nav)
    await c.message.answer("\n".join(lines)[:4000], reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mk:p:"))
async def cb_market_providers(c: CallbackQuery, s, user: User, lang: str):
    offset = max(0, as_int(parts(c)[2]))
    rows = [r for r in await sv.market_providers(s, user) if r[1].id != user.id]
    await c.answer()
    if not rows:
        await c.message.answer(t("market.no_providers", lang))
        return
    lines = [t("market.providers_title", lang, n=len(rows))]
    kb = InlineKeyboardBuilder()
    for i, (prof, pu, d) in enumerate(rows[offset:offset + 10], start=offset + 1):
        badge = " ✅" if prof.verified else ""
        rating = f"⭐{prof.rating_avg:.1f} ({prof.rating_count})" if prof.rating_count else "🆕"
        cats = await cat_names(s, (prof.category_ids or [])[:3], lang)
        lines.append(f"\n{i}. <b>{e(prof.business_name or pu.name)}</b>{badge} · {rating}\n🏷 {cats}\n"
                     f"📍 {e(pu.city or '—')}" + (f" ({fmt_km(d, lang)})" if d else "") + f" · 💶 {e(price_text(prof, lang))}")
        kb.button(text=f"{i}. {cut(prof.business_name or pu.name, 28)}", callback_data=f"pv:{prof.id}")
    kb.adjust(2)
    if offset + 10 < len(rows):
        kb.row(InlineKeyboardButton(text=t("btn.more", lang), callback_data=f"mk:p:{offset + 10}"))
    await c.message.answer("\n".join(lines)[:4000], reply_markup=kb.as_markup())


# ----------------------------------------------------------------------- 💼 encontrar trabalho
async def menu_jobs(m: Message, s, user: User, lang: str, **_):
    prof = await sv.get_provider(s, user.id)
    if not prof or not user.is_provider:
        await m.answer(t("become_provider_first", lang), reply_markup=ikb([(t("btn.become_provider", lang), "prov:start")]))
        return
    jobs = await sv.open_jobs_for_provider(s, prof, user)
    if not jobs:
        await m.answer(t("no_jobs", lang))
        return
    kb = InlineKeyboardBuilder()
    lines = [t("jobs_found", lang, n=len(jobs))]
    for req, d in jobs:
        cat = await s.get(Category, req.category_id)
        lines.append(f"• <b>#{req.id}</b> {cat.label(lang) if cat else ''} · {e(req.city or '')} {fmt_km(d, lang)} · "
                     f"{urgency_label(req.urgency, lang)}\n  {e(cut(req.description, 90))}")
        kb.button(text=f"#{req.id} {cut(req.description, 25)}", callback_data=f"jb:{req.id}")
    kb.adjust(2)
    await m.answer("\n".join(lines), reply_markup=kb.as_markup())


async def send_job_detail(m: Message, s, req: ServiceRequest, user: User, lang: str) -> None:
    if req.status == "hidden":
        await m.answer(t("not_found", lang))
        return
    card = await request_card(s, req, lang) + f"\n{t('status.' + req.status, lang)}"
    rows = []
    if req.client_id != user.id and req.status == "open":
        rows.append([(t("btn.send_proposal", lang), f"pp:{req.id}")])
        rows.append([(t("btn.message_client", lang), f"cq:{req.id}"), (t("btn.report", lang), f"rp:q:{req.id}")])
    if req.photo_file_ids:
        from aiogram.types import InputMediaPhoto
        await m.answer_media_group([InputMediaPhoto(media=p) for p in req.photo_file_ids[:5]])
    await m.answer(card, reply_markup=ikb(*rows) if rows else None)


@router.callback_query(F.data.startswith("jb:"))
async def cb_job(c: CallbackQuery, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    await c.answer()
    if not req:
        await c.message.answer(t("not_found", lang))
        return
    await send_job_detail(c.message, s, req, user, lang)


# ----------------------------------------------------------------------- propostas
@router.callback_query(F.data.startswith("pp:"))
async def cb_proposal_start(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    prof = await sv.get_provider(s, user.id)
    if not prof or not user.is_provider:
        await c.answer()
        await c.message.answer(t("become_provider_first", lang), reply_markup=ikb([(t("btn.become_provider", lang), "prov:start")]))
        return
    if not req or req.status != "open":
        await c.answer(t("not_found", lang), show_alert=True)
        return
    if req.client_id == user.id:
        await c.answer(t("prop.own_request", lang), show_alert=True)
        return
    if (await s.execute(select(Proposal.id).where(Proposal.request_id == req.id, Proposal.provider_id == prof.id))).first():
        await c.answer(t("prop.already", lang), show_alert=True)
        return
    await state.set_state(Prop.price)
    await state.update_data(request_id=req.id)
    await c.answer()
    await c.message.answer(f"#{req.id}\n" + t("prop.ask_price", lang), reply_markup=cancel_kb(lang))


@router.message(Prop.price)
async def prop_price(m: Message, state: FSMContext, lang: str):
    txt = text_ok(m, lang, 64)
    if not txt:
        await m.answer(t("too_long", lang, n=64))
        return
    await state.update_data(price=txt)
    await state.set_state(Prop.availability)
    await m.answer(t("prop.ask_availability", lang), reply_markup=cancel_kb(lang))


@router.message(Prop.availability)
async def prop_availability(m: Message, state: FSMContext, lang: str):
    txt = text_ok(m, lang, 255)
    if not txt:
        await m.answer(t("too_long", lang, n=255))
        return
    await state.update_data(availability=txt)
    await state.set_state(Prop.message)
    await m.answer(t("prop.ask_message", lang), reply_markup=skip_cancel_kb(lang, "pr:skipmsg"))


@router.message(Prop.message)
async def prop_message(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    txt = text_ok(m, lang, 1500)
    if not txt:
        await m.answer(t("too_long", lang, n=1500))
        return
    await finish_proposal(m, state, s, user, lang, bot, txt)


@router.callback_query(Prop.message, F.data == "pr:skipmsg")
async def prop_skip_message(c: CallbackQuery, state: FSMContext, s, user: User, lang: str, bot: Bot):
    await c.answer()
    await finish_proposal(c.message, state, s, user, lang, bot, "")


async def finish_proposal(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot, message: str):
    data = await state.get_data()
    await state.clear()
    req = await s.get(ServiceRequest, data.get("request_id", -1))
    prof = await sv.get_provider(s, user.id)
    if not req or not prof:
        await m.answer(t("not_found", lang))
        return
    try:
        prop = await sv.create_proposal(s, req, prof, user, price=data["price"], availability=data["availability"],
                                        message=message, max_per_day=settings.max_proposals_per_day)
    except sv.BusinessError as ex:
        await m.answer(t(ex.code, lang))
        return
    await m.answer(t("prop.sent", lang), reply_markup=menu_kb(lang))
    client = await s.get(User, req.client_id)
    if client:
        cl = client.language
        n = await sv.count_proposals(s, req.id)
        text = t("prop.new_notify", cl, id=req.id, card=await proposal_card(prop, prof, user, cl))
        await notify(bot, s, client, text, ikb([(t("btn.hire", cl), f"hire:{prop.id}"), (t("btn.chat", cl), f"cp:{prop.id}")],
                                               [(t("btn.profile", cl), f"pv:{prof.id}"),
                                                (t("btn.view_proposals", cl, n=n), f"vp:{req.id}")]))


@router.callback_query(F.data.startswith("vp:"))
async def cb_view_proposals(c: CallbackQuery, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    await c.answer()
    if not req or req.client_id != user.id:
        await c.message.answer(t("not_allowed", lang))
        return
    rows = await sv.proposals_for_request(s, req.id)
    if not rows:
        await c.message.answer(t("no_proposals", lang))
        return
    await c.message.answer(t("proposals_compare", lang, id=req.id))
    for prop, prof, pu in rows[:10]:
        buttons = [[(t("btn.chat", lang), f"cp:{prop.id}"), (t("btn.profile", lang), f"pv:{prof.id}")]]
        if req.status == "open" and prop.status == "pending":
            buttons.insert(0, [(t("btn.hire", lang), f"hire:{prop.id}")])
        prefix = "🤝 " if prop.status == "accepted" else ""
        await c.message.answer(prefix + await proposal_card(prop, prof, pu, lang), reply_markup=ikb(*buttons))


@router.callback_query(F.data.startswith("hire:"))
async def cb_hire(c: CallbackQuery, s, user: User, lang: str, bot: Bot):
    prop = await s.get(Proposal, as_int(parts(c)[1]))
    if not prop:
        await c.answer(t("not_found", lang), show_alert=True)
        return
    try:
        rejected = await sv.accept_proposal(s, prop, user)
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    prof = await s.get(ProviderProfile, prop.provider_id)
    pu = await s.get(User, prof.user_id)
    req = await s.get(ServiceRequest, prop.request_id)
    await c.answer("🤝")
    await c.message.answer(t("hired_client", lang, name=e(prof.business_name or pu.name)),
                           reply_markup=ikb([(t("btn.chat", lang), f"cp:{prop.id}")]))
    pl = pu.language
    await notify(bot, s, pu, t("hired_provider", pl, id=req.id, card=await request_card(s, req, pl)),
                 ikb([(t("btn.accept_job", pl), f"pj:{req.id}:1"), (t("btn.decline_job", pl), f"pj:{req.id}:0")],
                     [(t("btn.message_client", pl), f"cq:{req.id}")]))
    for other in rejected:
        op = await s.get(ProviderProfile, other.provider_id)
        ou = await s.get(User, op.user_id) if op else None
        if ou:
            await notify(bot, s, ou, t("proposal_rejected", ou.language, id=req.id))


@router.callback_query(F.data.startswith("pj:"))
async def cb_provider_job_response(c: CallbackQuery, s, user: User, lang: str, bot: Bot):
    _, req_id, accept = parts(c)
    req = await s.get(ServiceRequest, as_int(req_id))
    prof = await sv.get_provider(s, user.id)
    if not req or not prof:
        await c.answer(t("not_found", lang), show_alert=True)
        return
    try:
        await sv.provider_respond(s, req, prof, accept == "1")
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    await c.answer("✅" if accept == "1" else "✖️")
    client = await s.get(User, req.client_id)
    if accept == "1":
        await c.message.answer(t("job_accepted_provider", lang), reply_markup=ikb([(t("btn.message_client", lang), f"cq:{req.id}")]))
        if client:
            await notify(bot, s, client, t("job_accepted_client", client.language, name=e(prof.business_name or user.name), id=req.id),
                         ikb([(t("btn.complete", client.language), f"done:{req.id}")]))
    else:
        await c.message.answer(t("job_declined_provider", lang))
        if client:
            await notify(bot, s, client, t("job_declined_client", client.language, id=req.id),
                         ikb([(t("btn.view_proposals", client.language, n=await sv.count_proposals(s, req.id)), f"vp:{req.id}")]))


# ----------------------------------------------------------------------- 📋 minhas solicitações
async def menu_requests(m: Message, s, user: User, lang: str, **_):
    reqs = (await s.execute(select(ServiceRequest).where(ServiceRequest.client_id == user.id, ServiceRequest.status != "hidden")
                            .order_by(ServiceRequest.created_at.desc()).limit(15))).scalars().all()
    prof = await sv.get_provider(s, user.id)
    jobs = []
    if prof:
        jobs = (await s.execute(select(ServiceRequest).where(ServiceRequest.assigned_provider_id == prof.id)
                                .order_by(ServiceRequest.created_at.desc()).limit(15))).scalars().all()
    if not reqs and not jobs:
        await m.answer(t("my_requests_empty", lang), reply_markup=menu_kb(lang))
        return
    if reqs:
        kb = InlineKeyboardBuilder()
        for r in reqs:
            n = await sv.count_proposals(s, r.id)
            kb.button(text=f"{t('status.' + r.status, lang)[:2]} #{r.id} · {cut(r.description, 22)} · 📨{n}", callback_data=f"mr:{r.id}")
        kb.adjust(1)
        await m.answer(t("my_requests", lang), reply_markup=kb.as_markup())
    if jobs:
        kb = InlineKeyboardBuilder()
        for r in jobs:
            kb.button(text=f"{t('status.' + r.status, lang)[:2]} #{r.id} · {cut(r.description, 30)}", callback_data=f"mj:{r.id}")
        kb.adjust(1)
        await m.answer(t("my_jobs", lang), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("mr:"))
async def cb_my_request(c: CallbackQuery, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    await c.answer()
    if not req or req.client_id != user.id:
        await c.message.answer(t("not_allowed", lang))
        return
    n = await sv.count_proposals(s, req.id)
    rows = []
    if req.status in ("open", "assigned"):
        rows.append([(t("btn.view_proposals", lang, n=n), f"vp:{req.id}")])
    if req.status == "assigned":
        rows.append([(t("btn.complete", lang), f"done:{req.id}")])
    if req.status in ("open", "assigned"):
        rows.append([(t("btn.cancel_request", lang), f"cx:{req.id}")])
    if await sv.can_review(s, req, user):
        rows.append([(t("btn.rate", lang, id=req.id), f"rate:{req.id}")])
    await c.message.answer(await request_card(s, req, lang) + f"\n{t('status.' + req.status, lang)}",
                           reply_markup=ikb(*rows) if rows else None)


@router.callback_query(F.data.startswith("mj:"))
async def cb_my_job(c: CallbackQuery, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    prof = await sv.get_provider(s, user.id)
    await c.answer()
    if not req or not prof or req.assigned_provider_id != prof.id:
        await c.message.answer(t("not_allowed", lang))
        return
    rows = [[(t("btn.message_client", lang), f"cq:{req.id}")]]
    if req.status == "assigned" and not req.provider_confirmed:
        rows.insert(0, [(t("btn.accept_job", lang), f"pj:{req.id}:1"), (t("btn.decline_job", lang), f"pj:{req.id}:0")])
    await c.message.answer(await request_card(s, req, lang) + f"\n{t('status.' + req.status, lang)}", reply_markup=ikb(*rows))


@router.callback_query(F.data.startswith("cx:"))
async def cb_cancel_request(c: CallbackQuery, s, user: User, lang: str, bot: Bot):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    if not req:
        await c.answer(t("not_found", lang), show_alert=True)
        return
    assigned = req.assigned_provider_id
    try:
        await sv.cancel_request(s, req, user)
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    await c.answer("✅")
    await c.message.answer(t("request_cancelled", lang))
    if assigned:
        prof = await s.get(ProviderProfile, assigned)
        pu = await s.get(User, prof.user_id) if prof else None
        if pu:
            await notify(bot, s, pu, f"#{req.id} · {t('status.cancelled', pu.language)}")


@router.callback_query(F.data.startswith("done:"))
async def cb_complete(c: CallbackQuery, s, user: User, lang: str, bot: Bot):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    if not req:
        await c.answer(t("not_found", lang), show_alert=True)
        return
    try:
        await sv.complete_request(s, req, user)
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    await c.answer("✅")
    await send_rating_prompt(c.message, s, req, lang)
    prof = await s.get(ProviderProfile, req.assigned_provider_id)
    pu = await s.get(User, prof.user_id) if prof else None
    if pu:
        await notify(bot, s, pu, t("provider_job_completed", pu.language, id=req.id))


async def send_rating_prompt(m: Message, s, req: ServiceRequest, lang: str) -> None:
    prof = await s.get(ProviderProfile, req.assigned_provider_id)
    pu = await s.get(User, prof.user_id) if prof else None
    kb = InlineKeyboardBuilder()
    for n in range(1, 6):
        kb.button(text="⭐" * n, callback_data=f"rs:{req.id}:{n}")
    kb.adjust(1)
    await m.answer(t("request_completed", lang) + "\n" + t("rate_ask", lang, name=e((prof.business_name if prof else "") or (pu.name if pu else ""))),
                   reply_markup=kb.as_markup())


# ----------------------------------------------------------------------- ⭐ avaliações
async def menu_reviews(m: Message, s, user: User, lang: str, **_):
    lines = [t("reviews_title", lang)]
    pending = await sv.pending_reviews(s, user)
    kb = InlineKeyboardBuilder()
    if pending:
        lines.append("\n" + t("reviews_pending", lang))
        for r in pending[:10]:
            lines.append(f"• #{r.id} {e(cut(r.description, 60))}")
            kb.button(text=t("btn.rate", lang, id=r.id), callback_data=f"rate:{r.id}")
    prof = await sv.get_provider(s, user.id)
    if prof:
        reviews = await sv.provider_reviews(s, prof.id)
        lines.append("\n" + t("reviews_received", lang, avg=f"{prof.rating_avg:.1f}", n=prof.rating_count))
        for r in reviews:
            lines.append(f"{stars(r.rating)} · {r.created_at:%d/%m/%Y} — {e(cut(r.comment, 200))}")
            kb.button(text=f"🚩 {r.created_at:%d/%m} {stars(r.rating)}", callback_data=f"rp:r:{r.id}")
    if not pending and not prof:
        lines.append(t("reviews_none", lang))
    kb.adjust(2)
    await m.answer("\n".join(lines), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("rate:"))
async def cb_rate(c: CallbackQuery, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    if not req or not await sv.can_review(s, req, user):
        await c.answer(t("rate_not_allowed", lang), show_alert=True)
        return
    await c.answer()
    kb = InlineKeyboardBuilder()
    for n in range(1, 6):
        kb.button(text="⭐" * n, callback_data=f"rs:{req.id}:{n}")
    kb.adjust(1)
    prof = await s.get(ProviderProfile, req.assigned_provider_id)
    await c.message.answer(t("rate_ask", lang, name=e(prof.business_name if prof else "")), reply_markup=kb.as_markup())


@router.callback_query(F.data.startswith("rs:"))
async def cb_rate_stars(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    _, req_id, n = parts(c)
    req = await s.get(ServiceRequest, as_int(req_id))
    if not req or not await sv.can_review(s, req, user) or not 1 <= as_int(n) <= 5:
        await c.answer(t("rate_not_allowed", lang), show_alert=True)
        return
    await state.set_state(Rate.comment)
    await state.update_data(request_id=req.id, rating=as_int(n))
    await c.answer("⭐" * as_int(n))
    await c.message.answer(t("rate_comment", lang), reply_markup=skip_cancel_kb(lang, "rt:skip"))


@router.message(Rate.comment)
async def rate_comment(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    txt = text_ok(m, lang, 1000)
    if not txt:
        await m.answer(t("too_long", lang, n=1000))
        return
    await finish_rating(m, state, s, user, lang, bot, txt)


@router.callback_query(Rate.comment, F.data == "rt:skip")
async def rate_skip(c: CallbackQuery, state: FSMContext, s, user: User, lang: str, bot: Bot):
    await c.answer()
    await finish_rating(c.message, state, s, user, lang, bot, "")


async def finish_rating(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot, comment: str):
    data = await state.get_data()
    await state.clear()
    req = await s.get(ServiceRequest, data.get("request_id", -1))
    try:
        review = await sv.add_review(s, req, user, data.get("rating", 0), comment) if req else None
    except sv.BusinessError as ex:
        await m.answer(t(ex.code, lang))
        return
    if not review:
        await m.answer(t("not_found", lang))
        return
    await m.answer(t("rate_thanks", lang), reply_markup=menu_kb(lang))
    prof = await s.get(ProviderProfile, review.provider_id)
    pu = await s.get(User, prof.user_id) if prof else None
    if pu:
        await notify(bot, s, pu, t("new_review_notify", pu.language, stars=stars(review.rating), comment=e(comment)))


# ----------------------------------------------------------------------- 🚩 denúncias
@router.callback_query(F.data.startswith("rp:"))
async def cb_report(c: CallbackQuery, state: FSMContext, lang: str):
    _, kind, target = parts(c)
    await state.set_state(Rep.reason)
    await state.update_data(kind=kind, target=as_int(target))
    await c.answer()
    await c.message.answer(t("report_ask", lang), reply_markup=cancel_kb(lang))


@router.message(Rep.reason)
async def report_reason(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    txt = text_ok(m, lang, 2000)
    if not txt:
        await m.answer(t("too_long", lang, n=2000))
        return
    data = await state.get_data()
    await state.clear()
    kind, target = data.get("kind"), data.get("target")
    kwargs: dict = {}
    if kind == "u":
        kwargs["target_user_id"] = target
    elif kind == "r":
        review = await s.get(Review, target)
        kwargs["review_id"] = target
        if review:
            prof = await s.get(ProviderProfile, review.provider_id)
            kwargs["target_user_id"] = review.reviewer_id if prof and prof.user_id == user.id else (prof.user_id if prof else None)
    elif kind == "q":
        req = await s.get(ServiceRequest, target)
        kwargs["request_id"] = target
        kwargs["target_user_id"] = req.client_id if req else None
    rep = await sv.create_report(s, user, txt, **kwargs)
    await m.answer(t("report_sent", lang), reply_markup=menu_kb(lang))
    await notify_admins(bot, f"🚩 Denúncia #{rep.id} ({kind}:{target}) de {e(user.name)} [{user.id}]\n{e(cut(txt, 500))}", s)


# ----------------------------------------------------------------------- 💬 mensagens (chat interno)
async def menu_messages(m: Message, s, user: User, lang: str, **_):
    convs = await sv.conversations_for(s, user)
    if not convs:
        await m.answer(t("no_conversations", lang))
        return
    kb = InlineKeyboardBuilder()
    for conv, other, unread in convs:
        label = f"{'🔴 ' + str(unread) + ' · ' if unread else ''}{cut(await sv.display_name(s, other), 28)}" + (f" · #{conv.request_id}" if conv.request_id else "")
        kb.button(text=label, callback_data=f"cv:{conv.id}")
    kb.adjust(1)
    await m.answer(t("conversations", lang), reply_markup=kb.as_markup())


async def open_conversation(m: Message, state: FSMContext, s, conv: Conversation, user: User, lang: str) -> None:
    other = await s.get(User, sv.other_party(conv, user.id))
    history = await sv.conversation_history(s, conv, user)
    other_name = await sv.display_name(s, other)
    lines = []
    for msg in history:
        who = t("you", lang) if msg.sender_id == user.id else e(other_name)
        body = e(cut(msg.text, 300)) if msg.text else t("photo", lang)
        lines.append(f"<b>{who}</b> <i>{msg.created_at:%d/%m %H:%M}</i>\n{body}")
    await state.set_state(Chat.active)
    await state.update_data(conv_id=conv.id)
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=t("btn.exit_chat", lang))]], resize_keyboard=True)
    req = f" · #{conv.request_id}" if conv.request_id else ""
    await m.answer(t("chat_open", lang, name=e(other_name), req=req, history="\n\n".join(lines[-10:])), reply_markup=kb)


@router.callback_query(F.data.startswith("cv:"))
async def cb_conversation(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    conv = await s.get(Conversation, as_int(parts(c)[1]))
    await c.answer()
    if not conv or user.id not in (conv.client_id, conv.provider_user_id):
        await c.message.answer(t("not_allowed", lang))
        return
    await open_conversation(c.message, state, s, conv, user, lang)


async def _start_conv(c: CallbackQuery, state: FSMContext, s, user: User, lang: str, client_id: int, provider_user_id: int, req_id):
    try:
        conv = await sv.get_or_create_conversation(s, client_id, provider_user_id, req_id)
    except sv.BusinessError as ex:
        await c.answer(t(ex.code, lang), show_alert=True)
        return
    await c.answer()
    await open_conversation(c.message, state, s, conv, user, lang)


@router.callback_query(F.data.startswith("ct:"))
async def cb_contact_provider(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    other = await s.get(User, as_int(parts(c)[1]))
    if not other or other.is_banned:
        await c.answer(t("not_found", lang), show_alert=True)
        return
    await _start_conv(c, state, s, user, lang, user.id, other.id, None)


@router.callback_query(F.data.startswith("cq:"))
async def cb_contact_client(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    req = await s.get(ServiceRequest, as_int(parts(c)[1]))
    if not req or req.status == "hidden":
        await c.answer(t("not_found", lang), show_alert=True)
        return
    await _start_conv(c, state, s, user, lang, req.client_id, user.id, req.id)


@router.callback_query(F.data.startswith("cp:"))
async def cb_contact_proposal(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    prop = await s.get(Proposal, as_int(parts(c)[1]))
    req = await s.get(ServiceRequest, prop.request_id) if prop else None
    prof = await s.get(ProviderProfile, prop.provider_id) if prop else None
    if not prop or not req or not prof or req.client_id != user.id:
        await c.answer(t("not_allowed", lang), show_alert=True)
        return
    await _start_conv(c, state, s, user, lang, user.id, prof.user_id, req.id)


@router.message(Chat.active, F.text.in_(all_variants("btn.exit_chat")))
async def chat_exit(m: Message, state: FSMContext, lang: str):
    await state.clear()
    await show_menu(m, lang, t("chat_closed", lang))


@router.message(Chat.active, F.text | F.photo)
async def chat_message(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    data = await state.get_data()
    conv = await s.get(Conversation, data.get("conv_id", -1))
    if not conv or user.id not in (conv.client_id, conv.provider_user_id):
        await state.clear()
        await show_menu(m, lang)
        return
    if m.text and len(m.text) > 4000:
        await m.answer(t("too_long", lang, n=4000))
        return
    photo = m.photo[-1].file_id if m.photo else None
    text = m.text or m.caption
    await sv.add_message(s, conv, user, text, photo)
    other = await s.get(User, sv.other_party(conv, user.id))
    if other:
        ol = other.language
        req = f" · #{conv.request_id}" if conv.request_id else ""
        body = t("msg_incoming", ol, name=e(await sv.display_name(s, user)), req=req, text=e(text or ""))
        delivered = await notify(bot, s, other, body, ikb([(t("btn.reply", ol), f"cv:{conv.id}")]), photo=photo)
        await m.answer(t("msg_sent", lang) if delivered else "✓")


# ----------------------------------------------------------------------- 👤 perfil
async def menu_profile(m: Message, s, user: User, lang: str, bot: Bot, **_):
    prof = await sv.get_provider(s, user.id)
    plan = PLAN_NAMES.get(user.plan_code, {}).get(lang, user.plan_code)
    if user.plan_until and user.plan_code != "free":
        plan += f" (→ {user.plan_until:%d/%m/%Y})"
    text = t("profile_text", lang, name=e(user.name), city=e(f"{user.city or '—'}{', ' + user.country if user.country else ''}"),
             language=LANG_NAMES.get(user.language, user.language), plan=plan,
             ann=t("on" if user.announcements_opt_in else "off", lang), since=f"{user.created_at:%d/%m/%Y}")
    if user.early_adopter:
        text += "\n🏅 Early adopter"
    rows = [[(t("btn.edit_name", lang), "pr:name")]]
    if prof and user.is_provider:
        text += "\n\n" + await provider_card(s, prof, user, lang) + f"\n👁 {prof.profile_views}"
        link = await deep_link(bot, f"p_{prof.id}")
        rows += [[(t("btn.edit_provider", lang), "prov:start")],
                 [(t("btn.add_portfolio", lang), "pr:port"), (t("btn.clear_portfolio", lang), "pr:portclr")],
                 [(t("btn.toggle_notify", lang, state=t("on" if prof.notify_new_requests else "off", lang)), "pr:notify")],
                 [(t("btn.share_profile", lang), "url:" + share_url(link, prof.business_name or user.name))]]
    else:
        rows.append([(t("btn.become_provider", lang), "prov:start")])
    rows += [[(t("btn.toggle_ann", lang, state=t("on" if user.announcements_opt_in else "off", lang)), "pr:ann")],
             [(t("btn.plans", lang), "pl:list")],
             [(t("btn.export", lang), "pr:export"), (t("btn.delete_account", lang), "pr:del")]]
    await m.answer(text, reply_markup=ikb(*rows), disable_web_page_preview=True)


@router.callback_query(F.data == "pr:name")
async def cb_edit_name(c: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(EditName.name)
    await c.answer()
    await c.message.answer(t("ask_new_name", lang), reply_markup=cancel_kb(lang))


@router.message(EditName.name)
async def edit_name(m: Message, state: FSMContext, user: User, lang: str):
    name = text_ok(m, lang, 64)
    if not name:
        await m.answer(t("too_long", lang, n=64))
        return
    user.name = name
    await state.clear()
    await show_menu(m, lang, t("saved", lang))


@router.callback_query(F.data == "pr:notify")
async def cb_toggle_notify(c: CallbackQuery, s, user: User, lang: str):
    prof = await sv.get_provider(s, user.id)
    if prof:
        prof.notify_new_requests = not prof.notify_new_requests
        await c.answer(t("btn.toggle_notify", lang, state=t("on" if prof.notify_new_requests else "off", lang)), show_alert=True)
    else:
        await c.answer()


@router.callback_query(F.data == "pr:ann")
async def cb_toggle_ann(c: CallbackQuery, user: User, lang: str):
    user.announcements_opt_in = not user.announcements_opt_in
    await c.answer(t("btn.toggle_ann", lang, state=t("on" if user.announcements_opt_in else "off", lang)), show_alert=True)


@router.callback_query(F.data == "pr:export")
async def cb_export(c: CallbackQuery, s, user: User):
    data = await sv.export_user_data(s, user)
    await c.answer()
    await c.message.answer_document(BufferedInputFile(json.dumps(data, ensure_ascii=False, indent=2, default=str).encode(),
                                                      filename=f"serviceconnect-data-{user.id}.json"))


@router.callback_query(F.data == "pr:del")
async def cb_delete(c: CallbackQuery, lang: str):
    await c.answer()
    await c.message.answer(t("delete_confirm", lang), reply_markup=ikb([(t("btn.delete_yes", lang), "pr:del2")],
                                                                        [(t("btn.cancel", lang), "cancel")]))


@router.callback_query(F.data == "pr:del2")
async def cb_delete_confirm(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    await state.clear()
    await sv.delete_user_data(s, user)
    await c.answer("🗑")
    from aiogram.types import ReplyKeyboardRemove
    await c.message.answer(t("deleted", lang), reply_markup=ReplyKeyboardRemove())


# ---- portfólio
@router.callback_query(F.data == "pr:port")
async def cb_portfolio_add(c: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(Port.photos)
    await c.answer()
    await c.message.answer(t("portfolio_ask", lang), reply_markup=ikb([(t("btn.done", lang), "cancel")]))


@router.message(Port.photos, F.photo)
async def portfolio_photo(m: Message, s, user: User, lang: str):
    prof = await sv.get_provider(s, user.id)
    if not prof:
        return
    count = len((await s.execute(select(PortfolioPhoto.id).where(PortfolioPhoto.provider_id == prof.id))).all())
    if count >= 10:
        await m.answer(t("portfolio_full", lang))
        return
    s.add(PortfolioPhoto(provider_id=prof.id, file_id=m.photo[-1].file_id))
    await m.answer(f"🖼 {count + 1}/10", reply_markup=ikb([(t("btn.done", lang), "cancel")]))


@router.callback_query(F.data == "pr:portclr")
async def cb_portfolio_clear(c: CallbackQuery, s, user: User, lang: str):
    prof = await sv.get_provider(s, user.id)
    if prof:
        for p in (await s.execute(select(PortfolioPhoto).where(PortfolioPhoto.provider_id == prof.id))).scalars():
            await s.delete(p)
    await c.answer(t("saved", lang))


# ---- perfil profissional
async def start_provider_flow(m: Message, state: FSMContext, s, user: User, lang: str):
    prof = await sv.get_provider(s, user.id)
    await state.set_state(Prov.business)
    await state.update_data(categories=list(prof.category_ids) if prof else [])
    default = (prof.business_name if prof else None) or user.name
    rows = [[KeyboardButton(text=default[:64])]] if default else []
    await m.answer(t("prov.ask_business", lang),
                   reply_markup=ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True) if rows else None)


@router.callback_query(F.data == "prov:start")
async def cb_provider_start(c: CallbackQuery, state: FSMContext, s, user: User, lang: str):
    await c.answer()
    await start_provider_flow(c.message, state, s, user, lang)


@router.message(Prov.business)
async def prov_business(m: Message, state: FSMContext, lang: str):
    txt = text_ok(m, lang, 128)
    if not txt:
        await m.answer(t("too_long", lang, n=128))
        return
    await state.update_data(business=txt)
    await state.set_state(Prov.photo)
    await m.answer(t("prov.ask_photo", lang), reply_markup=skip_cancel_kb(lang, "pv2:skip"))


@router.message(Prov.photo, F.photo)
async def prov_photo(m: Message, state: FSMContext, lang: str):
    await state.update_data(photo=m.photo[-1].file_id)
    await ask_prov_description(m, state, lang)


@router.callback_query(Prov.photo, F.data == "pv2:skip")
async def prov_photo_skip(c: CallbackQuery, state: FSMContext, lang: str):
    await c.answer()
    await ask_prov_description(c.message, state, lang)


@router.message(Prov.photo)
async def prov_photo_other(m: Message, lang: str):
    await m.answer(t("prov.ask_photo", lang), reply_markup=skip_cancel_kb(lang, "pv2:skip"))


async def ask_prov_description(m: Message, state: FSMContext, lang: str):
    await state.set_state(Prov.description)
    await m.answer(t("prov.ask_description", lang), reply_markup=cancel_kb(lang))


@router.message(Prov.description)
async def prov_description(m: Message, state: FSMContext, s, lang: str):
    txt = text_ok(m, lang, 1500)
    if not txt:
        await m.answer(t("too_long", lang, n=1500))
        return
    await state.update_data(description=txt)
    await state.set_state(Prov.categories)
    selected = set((await state.get_data()).get("categories", []))
    await m.answer(t("prov.ask_categories", lang), reply_markup=await categories_kb(s, lang, "pcat", selected, done=True))


@router.callback_query(Prov.categories, F.data.startswith("pcat:"))
async def prov_categories(c: CallbackQuery, state: FSMContext, s, lang: str):
    value = parts(c)[1]
    selected = set((await state.get_data()).get("categories", []))
    if value == "done":
        if not selected:
            await c.answer(t("prov.need_category", lang), show_alert=True)
            return
        await c.answer()
        await state.set_state(Prov.radius)
        kb = InlineKeyboardBuilder()
        for r in sv.RADII:
            kb.button(text=f"{r} km", callback_data=f"prad:{r}")
        kb.adjust(5)
        await c.message.answer(t("prov.ask_radius", lang), reply_markup=kb.as_markup())
        return
    cid = as_int(value)
    selected.symmetric_difference_update({cid})
    await state.update_data(categories=sorted(selected))
    await c.answer()
    try:
        await c.message.edit_reply_markup(reply_markup=await categories_kb(s, lang, "pcat", selected, done=True))
    except TelegramBadRequest:
        pass


@router.callback_query(Prov.radius, F.data.startswith("prad:"))
async def prov_radius(c: CallbackQuery, state: FSMContext, lang: str):
    r = as_int(parts(c)[1])
    await state.update_data(radius=r if r in sv.RADII else 25)
    await state.set_state(Prov.price_type)
    await c.answer()
    await c.message.answer(t("prov.ask_price_type", lang), reply_markup=ikb([(t("btn.price_hourly", lang), "ptype:hourly")],
                                                                           [(t("btn.price_quote", lang), "ptype:quote")]))


@router.callback_query(Prov.price_type, F.data.startswith("ptype:"))
async def prov_price_type(c: CallbackQuery, state: FSMContext, lang: str):
    kind = "hourly" if parts(c)[1] == "hourly" else "quote"
    await state.update_data(price_type=kind)
    await c.answer()
    if kind == "hourly":
        await state.set_state(Prov.rate)
        await c.message.answer(t("prov.ask_rate", lang), reply_markup=cancel_kb(lang))
    else:
        await ask_prov_availability(c.message, state, lang)


@router.message(Prov.rate)
async def prov_rate(m: Message, state: FSMContext, lang: str):
    try:
        rate = float((m.text or "").replace("€", "").replace(",", ".").strip())
        assert 0 < rate < 100_000
    except (ValueError, AssertionError):
        await m.answer(t("prov.bad_rate", lang))
        return
    await state.update_data(rate=rate)
    await ask_prov_availability(m, state, lang)


async def ask_prov_availability(m: Message, state: FSMContext, lang: str):
    await state.set_state(Prov.availability)
    await m.answer(t("prov.ask_availability", lang), reply_markup=cancel_kb(lang))


@router.message(Prov.availability)
async def prov_availability(m: Message, state: FSMContext, s, user: User, lang: str):
    txt = text_ok(m, lang, 255)
    if not txt:
        await m.answer(t("too_long", lang, n=255))
        return
    data = await state.get_data()
    await state.clear()
    prof = await sv.get_provider(s, user.id)
    if not prof:
        prof = ProviderProfile(user_id=user.id)
        s.add(prof)
    prof.business_name = data["business"]
    if data.get("photo"):
        prof.photo_file_id = data["photo"]
    prof.description = data["description"]
    prof.category_ids = data["categories"]
    prof.radius_km = data.get("radius", 25)
    prof.price_type = data.get("price_type", "quote")
    prof.hourly_rate = data.get("rate") if prof.price_type == "hourly" else None
    prof.availability = txt
    user.is_provider = True
    await s.flush()
    await show_menu(m, lang, t("prov.done", lang))


# ----------------------------------------------------------------------- 📍 localização
async def menu_location(m: Message, state: FSMContext, lang: str, **_):
    await state.set_state(Loc.city)
    await m.answer(t("ask_location", lang), reply_markup=location_kb(lang, t("btn.cancel", lang)))


@router.message(Loc.city, F.text.in_(all_variants("btn.cancel")))
async def location_cancel(m: Message, state: FSMContext, lang: str):
    await state.clear()
    await show_menu(m, lang, t("cancelled", lang))


@router.message(Loc.city)
async def location_set(m: Message, state: FSMContext, s, user: User, lang: str):
    if not await save_location_message(m, s, user, lang):
        return
    await state.clear()
    await show_menu(m, lang, t("location_saved", lang, city=e(user.city)))


# ----------------------------------------------------------------------- 👥 convites
async def menu_invite(m: Message, s, user: User, lang: str, bot: Bot, **_):
    st = await sv.referral_stats(s, user)
    link = await deep_link(bot, f"ref_{user.referral_code}")
    top = "\n".join(f"{i}. {e(cut(u.name, 20))} — {n}" for i, (u, n) in enumerate(st["top"], start=1)) or "—"
    await m.answer(t("invite_text", lang, link=link, total=st["total"], valid=st["valid"], rank=st["rank"] or "—", top=top),
                   reply_markup=ikb([(t("btn.share_invite", lang), "url:" + share_url(link, t("share_invite_msg", lang)))]),
                   disable_web_page_preview=True)


# ----------------------------------------------------------------------- 🌐 idioma
async def menu_language(m: Message, lang: str, **_):
    kb = InlineKeyboardBuilder()
    for code in LANGS:
        kb.button(text=LANG_NAMES[code], callback_data=f"lang:{code}")
    kb.adjust(2)
    await m.answer(t("choose_language", lang), reply_markup=kb.as_markup())


# ----------------------------------------------------------------------- 🆘 suporte
async def menu_support(m: Message, lang: str, **_):
    await m.answer(t("support_text", lang, terms=public_url("/terms", lang), privacy=public_url("/privacy", lang)),
                   reply_markup=support_kb(lang), disable_web_page_preview=True)


def support_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[(t("btn.contact_support", lang), "sup:new")]]
    contact = settings.support_contact.strip()
    if contact.startswith("@") and len(contact) > 1:
        rows.append([(f"💬 {contact}", f"url:https://t.me/{contact[1:]}")])
    return ikb(*rows)


@router.callback_query(F.data == "sup:new")
async def cb_support(c: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(Sup.text)
    await c.answer()
    await c.message.answer(t("support_ask", lang), reply_markup=cancel_kb(lang))


@router.message(Sup.text)
async def support_text(m: Message, state: FSMContext, s, user: User, lang: str, bot: Bot):
    txt = text_ok(m, lang, 2000)
    if not txt:
        await m.answer(t("too_long", lang, n=2000))
        return
    await state.clear()
    ticket = await sv.create_report(s, user, txt, kind="support")
    await show_menu(m, lang, t("support_sent", lang))
    await notify_admins(bot, f"🆘 Suporte #{ticket.id} de {e(user.name)} [{user.id}]\n{e(cut(txt, 1000))}\n\n"
                             f"Responder: <code>/reply {ticket.id} texto</code>", s)


@router.message(Command("reply"))
async def cmd_reply(m: Message, command: CommandObject, s, bot: Bot):
    if not is_admin_user(m.from_user):
        return
    ticket_id, _, text = (command.args or "").partition(" ")
    from models import Report
    ticket = await s.get(Report, as_int(ticket_id))
    if not ticket or not text.strip():
        await m.answer("Uso: /reply <id> <texto>")
        return
    target = await s.get(User, ticket.reporter_id) if ticket.reporter_id else None
    if target and await notify(bot, s, target, t("support_reply", target.language, text=e(text.strip()))):
        ticket.status = "resolved"
        await m.answer("✅")
    else:
        await m.answer("❌")


@router.message(Command("admin"))
async def cmd_admin(m: Message, s):
    if not is_admin_user(m.from_user):
        return
    st = await sv.stats(s)
    await m.answer("🛠 <b>Admin</b>\n" + "\n".join(f"{k}: <b>{v}</b>" for k, v in st.items())
                   + (f"\n\n{settings.webhook_base_url}/admin" if settings.webhook_base_url else ""))


# ----------------------------------------------------------------------- 💳 planos (Telegram Stars, desligado por padrão)
@router.callback_query(F.data == "pl:list")
async def cb_plans(c: CallbackQuery, s, user: User, lang: str):
    await c.answer()
    promo_row = [(t("btn.promo", lang), "pl:promo")]
    if not await sv.monetization_enabled(s):
        await c.message.answer(t("plans_free", lang), reply_markup=ikb(promo_row))
        return
    plans = [p for p in await sv.active_plans(s) if p.code != "free"]
    lines, rows = [], []
    for p in plans:
        name = PLAN_NAMES.get(p.code, {}).get(lang, p.name)
        lines.append(f"• <b>{e(name)}</b> — {p.price_eur:.2f} € / {p.price_stars} ⭐ (30 d)")
        rows.append([(t("btn.subscribe", lang, plan=name), f"pl:buy:{p.code}")])
    current = PLAN_NAMES.get(user.plan_code, {}).get(lang, user.plan_code)
    await c.message.answer(t("plans_list", lang, current=current, plans="\n".join(lines)), reply_markup=ikb(*rows, promo_row))


@router.callback_query(F.data.startswith("pl:buy:"))
async def cb_plan_buy(c: CallbackQuery, s, lang: str):
    if not await sv.monetization_enabled(s):
        await c.answer(t("monetization_off", lang), show_alert=True)
        return
    plan = (await s.execute(select(Plan).where(Plan.code == parts(c)[2], Plan.active.is_(True)))).scalar_one_or_none()
    await c.answer()
    if not plan or plan.price_stars <= 0:
        return
    name = PLAN_NAMES.get(plan.code, {}).get(lang, plan.name)
    # consentimento explícito antes de qualquer cobrança
    await c.message.answer(t("plan_consent", lang, plan=e(name), stars=plan.price_stars, eur=f"{plan.price_eur:.2f}"),
                           reply_markup=ikb([(t("btn.confirm", lang), f"pl:ok:{plan.code}"), (t("btn.cancel", lang), "cancel")]))


@router.callback_query(F.data.startswith("pl:ok:"))
async def cb_plan_invoice(c: CallbackQuery, s, user: User, lang: str):
    if not await sv.monetization_enabled(s):
        await c.answer(t("monetization_off", lang), show_alert=True)
        return
    plan = (await s.execute(select(Plan).where(Plan.code == parts(c)[2], Plan.active.is_(True)))).scalar_one_or_none()
    await c.answer()
    if not plan or plan.price_stars <= 0:
        return
    name = PLAN_NAMES.get(plan.code, {}).get(lang, plan.name)
    await c.message.answer_invoice(title=f"ServiceConnect {name}", description=f"{name} · 30 dias", currency="XTR",
                                   payload=f"plan:{plan.code}:{user.id}:{plan.price_stars}",
                                   prices=[LabeledPrice(label=name, amount=plan.price_stars)], provider_token="")


@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery, s, user: User):
    ok = False
    try:
        _, code, uid, amount = q.invoice_payload.split(":")
        plan = (await s.execute(select(Plan).where(Plan.code == code, Plan.active.is_(True)))).scalar_one_or_none()
        ok = (await sv.monetization_enabled(s) and plan is not None and int(uid) == user.id
              and int(amount) == plan.price_stars == q.total_amount and q.currency == "XTR")
    except ValueError:
        ok = False
    await q.answer(ok=ok, error_message=None if ok else "Plano indisponível.")


@router.message(F.successful_payment)
async def successful_payment(m: Message, s, user: User, lang: str):
    sp = m.successful_payment
    _, code, _uid, _amount = sp.invoice_payload.split(":")
    sub = await sv.activate_plan(s, user, code, 30, source="stars", stars=sp.total_amount,
                                 charge_id=sp.telegram_payment_charge_id, consent=True)
    name = PLAN_NAMES.get(code, {}).get(lang, code)
    await m.answer(t("plan_activated", lang, plan=e(name), until=f"{sub.ends_at:%d/%m/%Y}"))


@router.callback_query(F.data == "pl:promo")
async def cb_promo(c: CallbackQuery, state: FSMContext, lang: str):
    await state.set_state(Promo.code)
    await c.answer()
    await c.message.answer(t("promo_ask", lang), reply_markup=cancel_kb(lang))


@router.message(Promo.code)
async def promo_code(m: Message, state: FSMContext, s, user: User, lang: str):
    await state.clear()
    try:
        sub = await sv.redeem_promo(s, user, m.text or "")
    except sv.BusinessError as ex:
        await show_menu(m, lang, t(ex.code, lang))
        return
    name = PLAN_NAMES.get(sub.plan_code, {}).get(lang, sub.plan_code)
    await show_menu(m, lang, t("plan_activated", lang, plan=e(name), until=f"{sub.ends_at:%d/%m/%Y}"))


# ----------------------------------------------------------------------- outros
@router.my_chat_member()
async def on_member(update: ChatMemberUpdated, user: User):
    if update.chat.type == "private":
        user.blocked_bot = update.new_chat_member.status in ("kicked", "left")


@router.message(StateFilter(None))
async def fallback(m: Message, user: User, lang: str, state: FSMContext):
    if not user.accepted_terms_at:
        await state.set_state(Onb.terms)
        await send_welcome(m, lang)
        return
    if not user.onboarded:
        await m.answer(t("need_onboarding", lang))
        return
    await show_menu(m, lang)


@router.message()
async def fallback_in_state(m: Message, lang: str):
    await m.answer(t("send_text", lang))


@router.callback_query()
async def fallback_callback(c: CallbackQuery, lang: str):
    await c.answer(t("not_found", lang))


# ======================================================================= montagem
async def tolerate_old_callbacks(make_request, bot, method):
    """Se o servidor demorou (ex.: a acordar), o Telegram expira o 'answerCallbackQuery'.
    Isso não deve impedir o bot de responder ao clique."""
    from aiogram.methods import AnswerCallbackQuery
    try:
        return await make_request(bot, method)
    except TelegramBadRequest as ex:
        if isinstance(method, AnswerCallbackQuery) and ("too old" in str(ex) or "query ID is invalid" in str(ex)):
            return True
        raise


def create_bot(token: str | None = None) -> Bot:
    bot = Bot(token or settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(tolerate_old_callbacks)
    return bot


def create_dispatcher(database) -> Dispatcher:
    # PostgreSQL: estado persistente (sobrevive a reinícios). SQLite (dev/testes): memória, pois só aceita 1 escritor.
    storage = DBStorage(database) if database.is_postgres else MemoryStorage()
    dp = Dispatcher(storage=storage)
    dp.update.outer_middleware(ThrottleMiddleware(settings.rate_limit_per_minute))
    dp.update.outer_middleware(ContextMiddleware(database))
    import sam_sol  # robô SAM SOL (/sol, só administradores) antes do router principal
    sam_sol.router._parent_router = None  # um Dispatcher novo (testes) pode reutilizar o router
    dp.include_router(sam_sol.router)
    dp.include_router(router)

    @dp.errors()
    async def on_error(event):  # noqa: ANN001
        log.exception("Erro ao processar update: %s", event.exception)
        upd = event.update
        lang = "pt"
        try:
            src = upd.message or (upd.callback_query and upd.callback_query.message)
            fu = (upd.message and upd.message.from_user) or (upd.callback_query and upd.callback_query.from_user)
            lang = norm_lang(fu.language_code if fu else None)
            if src:
                await src.answer(t("error", lang))
        except Exception:  # noqa: BLE001
            pass
        return True

    return dp


async def setup_bot_profile(bot: Bot) -> None:
    """Comandos e descrição do bot em cada idioma."""
    for lang in LANGS:
        cmds = [BotCommand(command="start", description=t("menu.title", lang).split("\n")[0].replace("<b>", "").replace("</b>", "")),
                BotCommand(command="menu", description=t("menu.find", lang)),
                BotCommand(command="cancel", description=t("btn.cancel", lang)),
                BotCommand(command="help", description=t("menu.support", lang))]
        try:
            await bot.set_my_commands(cmds, language_code=None if lang == "en" else lang)
            if lang == "en":
                await bot.set_my_commands(cmds)
        except Exception as ex:  # noqa: BLE001
            log.warning("set_my_commands(%s): %s", lang, ex)


async def broadcast(bot: Bot, database, text: str, audience: str = "all", broadcast_id: int | None = None) -> tuple[int, int]:
    """Comunicado aos usuários que aceitaram receber comunicados (opt-out no perfil)."""
    from models import Broadcast
    sent = failed = 0
    async with database.session() as s:
        q = select(User).where(User.announcements_opt_in.is_(True), User.blocked_bot.is_(False), User.is_banned.is_(False),
                               User.onboarded.is_(True))
        if audience == "providers":
            q = q.where(User.is_provider.is_(True))
        elif audience == "clients":
            q = q.where(User.is_provider.is_(False))
        users = (await s.execute(q)).scalars().all()
        for u in users:
            if await notify(bot, s, u, t("announcement", u.language, text=e(text))):
                sent += 1
            else:
                failed += 1
            await asyncio.sleep(0.05)
        if broadcast_id:
            b = await s.get(Broadcast, broadcast_id)
            if b:
                b.sent, b.failed = sent, failed
        await s.commit()
    return sent, failed
