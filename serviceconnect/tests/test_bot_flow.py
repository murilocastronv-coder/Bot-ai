"""Simula usuários reais a carregar nos botões do bot (sem rede: a API do Telegram é falsa)."""
import itertools
from datetime import datetime

from sqlalchemy import select

from bot import create_dispatcher
from i18n import t
from models import Conversation, Message as DbMessage, Proposal, ProviderProfile, Report, Review, ServiceRequest, User

_ids = itertools.count(1)
CLIENT, PRO = 1001, 2002


def _user(uid, name, lang="pt"):
    return {"id": uid, "is_bot": False, "first_name": name, "language_code": lang}


def msg_update(uid, text=None, name="User", location=None, photo=None, lang="pt"):
    m = {"message_id": next(_ids), "date": int(datetime.now().timestamp()), "chat": {"id": uid, "type": "private"},
         "from": _user(uid, name, lang)}
    if text is not None:
        m["text"] = text
        if text.startswith("/"):
            m["entities"] = [{"type": "bot_command", "offset": 0, "length": len(text.split()[0])}]
    if location:
        m["location"] = {"latitude": location[0], "longitude": location[1]}
    if photo:
        m["photo"] = [{"file_id": photo, "file_unique_id": photo + "u", "width": 10, "height": 10}]
    return {"update_id": next(_ids), "message": m}


def cb_update(uid, data, name="User", lang="pt"):
    return {"update_id": next(_ids), "callback_query": {
        "id": str(next(_ids)), "from": _user(uid, name, lang), "chat_instance": "ci", "data": data,
        "message": {"message_id": next(_ids), "date": int(datetime.now().timestamp()), "chat": {"id": uid, "type": "private"},
                    "from": {"id": 42, "is_bot": True, "first_name": "Bot"}, "text": "x"}}}


class Harness:
    def __init__(self, db, bot, session):
        self.db, self.bot, self.session = db, bot, session
        from bot import router
        router._parent_router = None  # permite um Dispatcher novo por teste
        self.dp = create_dispatcher(db)

    async def send(self, raw):
        from aiogram.types import Update
        await self.dp.feed_update(self.bot, Update.model_validate(raw, context={"bot": self.bot}))

    async def text(self, uid, text, **kw):
        await self.send(msg_update(uid, text, **kw))

    async def click(self, uid, data, **kw):
        await self.send(cb_update(uid, data, **kw))

    def last_markup_callbacks(self, uid) -> list[str]:
        for call in reversed(self.session.sent_to(uid)):
            rm = getattr(call, "reply_markup", None)
            if rm is not None and hasattr(rm, "inline_keyboard"):
                return [b.callback_data for row in rm.inline_keyboard for b in row if b.callback_data]
        return []

    async def user(self, tg):
        async with self.db.session() as s:
            return (await s.execute(select(User).where(User.telegram_id == tg))).scalar_one()


async def onboard(h: Harness, uid, name, role, city="Lisboa", ref=None):
    await h.text(uid, f"/start {ref}" if ref else "/start", name=name)
    assert any("ServiceConnect" in x for x in h.session.texts_to(uid))
    await h.click(uid, "terms:ok", name=name)
    await h.text(uid, name, name=name)
    await h.click(uid, f"role:{role}", name=name)
    await h.text(uid, city, name=name)


async def test_end_to_end_marketplace(db, fake_bot):
    bot, session = fake_bot
    h = Harness(db, bot, session)

    # ---- cliente faz cadastro (aceita termos, nome, tipo, cidade)
    await onboard(h, CLIENT, "Ana", "client")
    ana = await h.user(CLIENT)
    assert ana.onboarded and ana.city == "Lisboa" and ana.lat is not None and ana.accepted_terms_at
    assert any(t("onboard_done", "pt", name="Ana") in x for x in session.texts_to(CLIENT))

    # ---- profissional entra pelo link de convite da Ana e cria perfil profissional
    await onboard(h, PRO, "Bruno", "provider", ref=f"ref_{ana.referral_code}")
    assert any(t("referral_joined", "pt") in x for x in session.texts_to(CLIENT))
    await h.text(PRO, "Bruno Limpezas", name="Bruno")           # nome profissional
    await h.send(msg_update(PRO, photo="profile-photo", name="Bruno"))  # foto
    await h.text(PRO, "10 anos de experiência em limpezas", name="Bruno")
    async with db.session() as s:
        from services import list_categories
        cats = {c.key: c.id for c in await list_categories(s)}
    await h.click(PRO, f"pcat:{cats['cleaning']}")
    await h.click(PRO, "pcat:done")
    await h.click(PRO, "prad:25")
    await h.click(PRO, "ptype:hourly")
    await h.text(PRO, "15")
    await h.text(PRO, "Seg-Sáb 8h-18h")
    bruno = await h.user(PRO)
    assert bruno.is_provider and bruno.referred_by_id == ana.id
    async with db.session() as s:
        prof = (await s.execute(select(ProviderProfile).where(ProviderProfile.user_id == bruno.id))).scalar_one()
        assert prof.category_ids == [cats["cleaning"]] and prof.hourly_rate == 15 and prof.photo_file_id == "profile-photo"

    # ---- cliente encontra o profissional
    await h.text(CLIENT, t("menu.find", "pt"))
    await h.click(CLIENT, f"fc:{cats['cleaning']}")
    await h.click(CLIENT, f"fr:{cats['cleaning']}:10:0")
    assert any("Bruno Limpezas" in x for x in session.texts_to(CLIENT))
    assert f"pv:{prof.id}" in h.last_markup_callbacks(CLIENT)

    # ---- cliente publica um pedido → profissional é notificado
    before = len(session.sent_to(PRO))
    await h.text(CLIENT, t("menu.publish", "pt"))
    await h.click(CLIENT, f"pc:{cats['cleaning']}")
    await h.text(CLIENT, "Limpeza completa de apartamento T2")
    await h.send(msg_update(CLIENT, photo="req-photo-1"))
    await h.click(CLIENT, "rq:photos")
    await h.text(CLIENT, "🏙 Lisboa")
    await h.text(CLIENT, "100 €")
    await h.click(CLIENT, "rq:skip")  # data
    await h.click(CLIENT, "ru:urgent")
    await h.click(CLIENT, "rq:confirm")
    async with db.session() as s:
        req = (await s.execute(select(ServiceRequest))).scalar_one()
        assert req.photo_file_ids == ["req-photo-1"] and req.budget == "100 €" and req.urgency == "urgent" and req.notified_count == 1
    notif = session.texts_to(PRO)[before:]
    assert any(t("new_request_notify", "pt") in x for x in notif)

    # ---- marketplace: qualquer pessoa vê os anúncios abertos e os profissionais
    await h.text(PRO, t("menu.market", "pt"))
    assert "mk:r:0:0" in h.last_markup_callbacks(PRO)
    await h.click(PRO, "mk:r:0:0")
    assert any("Limpeza completa" in x for x in session.texts_to(PRO)[-1:])
    assert f"jb:{req.id}" in h.last_markup_callbacks(PRO)
    await h.click(PRO, "mk:f")
    await h.click(PRO, f"mk:r:{cats['plumbing']}:0")
    assert "mk:f" in h.last_markup_callbacks(PRO)  # nenhum anúncio nessa categoria
    await h.click(CLIENT, "mk:p:0")
    assert f"pv:{prof.id}" in h.last_markup_callbacks(CLIENT)

    # ---- profissional vê trabalhos e envia orçamento
    await h.text(PRO, t("menu.jobs", "pt"))
    assert f"jb:{req.id}" in h.last_markup_callbacks(PRO)
    await h.click(PRO, f"pp:{req.id}")
    await h.text(PRO, "95 €")
    await h.text(PRO, "Sábado de manhã")
    await h.text(PRO, "Incluo produtos")
    assert any(t("prop.sent", "pt") in x for x in session.texts_to(PRO))
    async with db.session() as s:
        prop = (await s.execute(select(Proposal))).scalar_one()
    assert f"hire:{prop.id}" in h.last_markup_callbacks(CLIENT)

    # ---- chat interno (sem expor telefone)
    await h.click(CLIENT, f"cp:{prop.id}")
    await h.text(CLIENT, "Pode vir às 9h?")
    await h.text(PRO, t("menu.messages", "pt"))
    async with db.session() as s:
        conv = (await s.execute(select(Conversation))).scalar_one()
        assert (await s.execute(select(DbMessage))).scalar_one().text == "Pode vir às 9h?"
    assert any("Pode vir às 9h?" in x for x in session.texts_to(PRO))
    await h.click(PRO, f"cv:{conv.id}")
    await h.text(PRO, "Sim, combinado!")
    assert any("Sim, combinado!" in x for x in session.texts_to(CLIENT))
    await h.text(PRO, t("btn.exit_chat", "pt"))

    # ---- contratar → profissional aceita → concluir → avaliar
    await h.text(CLIENT, t("btn.exit_chat", "pt"))
    await h.click(CLIENT, f"hire:{prop.id}")
    assert f"pj:{req.id}:1" in h.last_markup_callbacks(PRO)
    await h.click(PRO, f"pj:{req.id}:1")
    assert f"done:{req.id}" in h.last_markup_callbacks(CLIENT)
    await h.click(CLIENT, f"done:{req.id}")
    await h.click(CLIENT, f"rs:{req.id}:5")
    await h.text(CLIENT, "Excelente!")
    async with db.session() as s:
        review = (await s.execute(select(Review))).scalar_one()
        prof = await s.get(ProviderProfile, prof.id)
        assert review.rating == 5 and prof.rating_avg == 5 and prof.jobs_done == 1
        assert (await s.get(ServiceRequest, req.id)).status == "completed"

    # ---- todos os botões do menu respondem
    for key in ("menu.profile", "menu.requests", "menu.reviews", "menu.invite", "menu.language", "menu.support", "menu.location"):
        n = len(session.sent_to(CLIENT))
        await h.text(CLIENT, t(key, "pt"))
        assert len(session.sent_to(CLIENT)) > n, key
    await h.text(CLIENT, "Porto")  # responde à pergunta de localização
    assert (await h.user(CLIENT)).city == "Porto"

    # ---- denúncia e suporte chegam à moderação
    await h.click(CLIENT, f"rp:u:{bruno.id}")
    await h.text(CLIENT, "Perfil suspeito")
    await h.click(CLIENT, "sup:new")
    await h.text(CLIENT, "Preciso de ajuda")
    async with db.session() as s:
        kinds = sorted(r.kind for r in (await s.execute(select(Report))).scalars())
    assert kinds == ["report", "support"]
    assert session.sent_to(999)  # admin recebeu aviso

    # ---- idioma
    await h.click(CLIENT, "lang:fr")
    assert (await h.user(CLIENT)).language == "fr"
    await h.text(CLIENT, t("menu.profile", "fr"))

    # ---- planos: tudo gratuito, sem fatura
    await h.click(CLIENT, "pl:list")
    assert any("100 %" in x for x in session.texts_to(CLIENT)[-1:])
    await h.click(CLIENT, "pl:buy:pro")
    assert not [c for c in session.calls if type(c).__name__ == "SendInvoice"]

    # ---- exclusão de conta (RGPD)
    await h.click(PRO, "pr:del2")
    async with db.session() as s:
        assert (await s.execute(select(User).where(User.telegram_id == PRO))).scalar_one_or_none() is None


async def test_banned_user_is_blocked(db, fake_bot):
    bot, session = fake_bot
    h = Harness(db, bot, session)
    await onboard(h, 3003, "Mau", "client")
    async with db.session() as s:
        u = (await s.execute(select(User).where(User.telegram_id == 3003))).scalar_one()
        u.is_banned = True
        await s.commit()
    await h.text(3003, t("menu.publish", "pt"))
    assert t("banned", "pt") in session.texts_to(3003)[-1]


async def test_language_auto_detected(db, fake_bot):
    bot, session = fake_bot
    h = Harness(db, bot, session)
    await h.text(4004, "/start", lang="es")
    assert (await h.user(4004)).language == "es"
    assert "Bienvenido" in session.texts_to(4004)[-1]


async def test_throttle_blocks_flood():
    from bot import ThrottleMiddleware
    mw = ThrottleMiddleware(per_minute=3)
    calls = []

    async def handler(event, data):
        calls.append(1)

    class U:
        id, language_code = 5, "pt"
    for _ in range(10):
        await mw(handler, object(), {"event_from_user": U()})
    assert len(calls) == 3


async def test_support_goes_to_admin_by_username(db, fake_bot, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "admin_usernames", ["murilocastronv"])
    monkeypatch.setattr(config.settings, "support_contact", "@Murilocastronv")
    bot, session = fake_bot
    h = Harness(db, bot, session)
    admin_raw = msg_update(5005, "/start", name="Murilo")
    admin_raw["message"]["from"]["username"] = "Murilocastronv"
    await h.send(admin_raw)
    await onboard(h, 6006, "Cliente", "client")
    await h.text(6006, t("menu.support", "pt"))
    rm = session.sent_to(6006)[-1].reply_markup
    assert any(b.url == "https://t.me/Murilocastronv" for row in rm.inline_keyboard for b in row)
    await h.click(6006, "sup:new")
    await h.text(6006, "Preciso de ajuda urgente")
    assert any("Preciso de ajuda urgente" in x for x in session.texts_to(5005))
