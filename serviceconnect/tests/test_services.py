import pytest
from sqlalchemy import func, select

import services as sv
from models import Category, Message, Promotion, ProviderProfile, User, utcnow


async def make_user(s, tg, name, city="Lisboa", country="PT", lat=38.7223, lon=-9.1393, provider_cats=None, radius=25):
    u, _ = await sv.get_or_create_user(s, tg, name, None, "pt")
    u.city, u.country, u.lat, u.lon = city, country, lat, lon
    u.onboarded, u.accepted_terms_at = True, utcnow()
    prof = None
    if provider_cats is not None:
        u.is_provider = True
        prof = ProviderProfile(user_id=u.id, business_name=f"{name} Lda", category_ids=provider_cats, radius_km=radius)
        s.add(prof)
    await s.flush()
    return u, prof


async def cat_id(s, key):
    return (await s.execute(select(Category.id).where(Category.key == key))).scalar_one()


def test_haversine_lisbon_porto():
    assert 270 < sv.haversine_km(38.7223, -9.1393, 41.1579, -8.6291) < 280


async def test_seed_has_18_categories_and_plans(db):
    async with db.session() as s:
        cats = await sv.list_categories(s)
        assert len(cats) == 18
        assert {c.key for c in cats} >= {"cleaning", "plumbing", "webdev", "other"}
        assert await sv.monetization_enabled(s) is False  # monetização desligada no lançamento
        plans = {p.code: p for p in await sv.active_plans(s)}
        assert plans["pro"].price_eur == 9.99 and plans["premium"].price_eur == 19.99 and plans["business"].price_eur == 39.99


async def test_resolve_city_and_nearest(db):
    async with db.session() as s:
        p = await sv.resolve_city(s, "lisboa, pt")
        assert p.city == "Lisboa" and p.lat is not None
        p2 = await sv.resolve_city(s, "Aldeia Desconhecida")
        assert p2.lat is None and p2.city == "Aldeia Desconhecida"
        near = await sv.nearest_city(s, 38.70, -9.15)
        assert near.name == "Lisboa"


async def test_search_filters_by_category_distance_and_ranks(db):
    async with db.session() as s:
        clean = await cat_id(s, "cleaning")
        client, _ = await make_user(s, 1, "Cliente")
        near, pnear = await make_user(s, 2, "Perto", lat=38.73, lon=-9.14, provider_cats=[clean])
        far, pfar = await make_user(s, 3, "Porto", city="Porto", lat=41.1579, lon=-8.6291, provider_cats=[clean], radius=100)
        other, _ = await make_user(s, 4, "Outro", lat=38.72, lon=-9.13, provider_cats=[await cat_id(s, "plumbing")])
        verified, pver = await make_user(s, 5, "Verificado", lat=38.76, lon=-9.10, provider_cats=[clean])
        pver.verified = True
        await s.flush()

        res = await sv.search_providers(s, client, clean, 10)
        names = [u.name for _, u, _ in res]
        assert names == ["Verificado", "Perto"]  # verificado primeiro; Porto fora de 10 km; canalizador excluído
        res100 = await sv.search_providers(s, client, clean, 100)
        assert "Porto" not in [u.name for _, u, _ in res100]  # 275 km
        city_only = await sv.search_providers(s, client, clean, None)
        assert {u.name for _, u, _ in city_only} == {"Perto", "Verificado"}

        # perfil banido nunca aparece
        verified.is_banned = True
        await s.flush()
        assert [u.name for _, u, _ in await sv.search_providers(s, client, clean, 25)] == ["Perto"]


async def test_full_job_lifecycle(db):
    async with db.session() as s:
        clean = await cat_id(s, "cleaning")
        client, _ = await make_user(s, 10, "Ana")
        pu1, p1 = await make_user(s, 11, "Bruno", lat=38.73, lon=-9.14, provider_cats=[clean])
        pu2, p2 = await make_user(s, 12, "Carla", lat=38.74, lon=-9.15, provider_cats=[clean])
        _, p_off = await make_user(s, 13, "Sem notif", lat=38.74, lon=-9.15, provider_cats=[clean])
        p_off.notify_new_requests = False

        req = await sv.create_request(s, client, category_id=clean, description="Limpeza T2", photos=["f1"],
                                      place=sv.Place("Lisboa", "PT", 38.7223, -9.1393), budget="80 €", desired_date="sábado",
                                      urgency="high")
        matches = await sv.matching_providers(s, req)
        assert {u.name for _, u, _ in matches} == {"Bruno", "Carla"}  # respeita preferência de notificação

        prop1 = await sv.create_proposal(s, req, p1, pu1, price="90 €", availability="sábado", message="Olá")
        prop2 = await sv.create_proposal(s, req, p2, pu2, price="70 €", availability="domingo", message="")
        with pytest.raises(sv.BusinessError) as ex:
            await sv.create_proposal(s, req, p1, pu1, price="1", availability="", message="")
        assert ex.value.code == "prop.already"
        assert await sv.count_proposals(s, req.id) == 2
        ordered = await sv.proposals_for_request(s, req.id)
        assert [p.price for p, _, _ in ordered] == ["70 €", "90 €"]  # mais barata primeiro com mesma avaliação

        # avaliação antes de concluir: proibida
        with pytest.raises(sv.BusinessError):
            await sv.add_review(s, req, client, 5, "cedo demais")

        # só o dono do pedido pode contratar
        with pytest.raises(sv.BusinessError):
            await sv.accept_proposal(s, prop1, pu2)
        rejected = await sv.accept_proposal(s, prop1, client)
        assert [r.id for r in rejected] == [prop2.id] and req.status == "assigned"

        # profissional recusa → pedido reabre e propostas voltam a valer
        await sv.provider_respond(s, req, p1, accept=False)
        assert req.status == "open" and prop2.status == "pending"

        await sv.accept_proposal(s, prop2, client)
        await sv.provider_respond(s, req, p2, accept=True)
        assert req.provider_confirmed
        await sv.complete_request(s, req, client)
        assert req.status == "completed" and p2.jobs_done == 1

        assert await sv.can_review(s, req, client)
        assert not await sv.can_review(s, req, pu1)
        await sv.add_review(s, req, client, 4, "Bom trabalho")
        assert p2.rating_avg == 4.0 and p2.rating_count == 1
        with pytest.raises(sv.BusinessError):  # só uma avaliação por serviço
            await sv.add_review(s, req, client, 5, "de novo")
        assert await sv.pending_reviews(s, client) == []

        jobs = await sv.open_jobs_for_provider(s, p1, pu1)
        assert req.id not in [r.id for r, _ in jobs]


async def test_cannot_bid_on_own_request_and_daily_limit(db):
    async with db.session() as s:
        clean = await cat_id(s, "cleaning")
        u, p = await make_user(s, 20, "Dupla", provider_cats=[clean])
        req = await sv.create_request(s, u, category_id=clean, description="Teste próprio", photos=[],
                                      place=sv.Place("Lisboa", "PT", None, None), budget=None, desired_date=None, urgency="normal")
        with pytest.raises(sv.BusinessError) as ex:
            await sv.create_proposal(s, req, p, u, price="1", availability="", message="")
        assert ex.value.code == "prop.own_request"
        for _ in range(2):
            await sv.create_request(s, u, category_id=clean, description="spam spam", photos=[], place=sv.Place("Lisboa", "PT", None, None),
                                    budget=None, desired_date=None, urgency="normal", max_per_day=3)
        with pytest.raises(sv.BusinessError) as ex:
            await sv.create_request(s, u, category_id=clean, description="spam spam", photos=[], place=sv.Place("Lisboa", "PT", None, None),
                                    budget=None, desired_date=None, urgency="normal", max_per_day=3)
        assert ex.value.code == "daily_limit"


async def test_matching_without_coordinates_uses_city(db):
    async with db.session() as s:
        clean = await cat_id(s, "cleaning")
        client, _ = await make_user(s, 30, "C", city="Vila Nova", country="PT", lat=None, lon=None)
        _, p = await make_user(s, 31, "P", city="vila nova", country="PT", lat=None, lon=None, provider_cats=[clean])
        _, p2 = await make_user(s, 32, "Q", city="Outra", country="PT", lat=None, lon=None, provider_cats=[clean])
        req = await sv.create_request(s, client, category_id=clean, description="Sem GPS", photos=[],
                                      place=sv.Place("Vila Nova", "PT", None, None), budget=None, desired_date=None, urgency="low")
        assert [u.name for _, u, _ in await sv.matching_providers(s, req)] == ["P"]


async def test_referrals_valid_only_after_onboarding(db):
    async with db.session() as s:
        inviter, _ = await make_user(s, 40, "Inviter")
        new1, _ = await sv.get_or_create_user(s, 41, "N1", None, "pt")
        assert (await sv.apply_referral(s, new1, inviter.referral_code)).id == inviter.id
        new2, _ = await sv.get_or_create_user(s, 42, "N2", None, "pt")
        await sv.apply_referral(s, new2, inviter.referral_code)
        assert await sv.apply_referral(s, inviter, inviter.referral_code) is None  # não pode convidar a si mesmo
        await s.flush()
        st = await sv.referral_stats(s, inviter)
        assert st["total"] == 2 and st["valid"] == 0
        new1.onboarded, new1.accepted_terms_at = True, utcnow()
        await s.flush()
        st = await sv.referral_stats(s, inviter)
        assert st["valid"] == 1 and st["rank"] == 1 and st["top"][0][0].id == inviter.id
        # indicação de conta suspensa deixa de contar
        new1.is_banned = True
        await s.flush()
        assert (await sv.referral_stats(s, inviter))["valid"] == 0


async def test_chat_and_gdpr_delete(db):
    async with db.session() as s:
        clean = await cat_id(s, "cleaning")
        client, _ = await make_user(s, 50, "Cli")
        pu, prof = await make_user(s, 51, "Pro", provider_cats=[clean])
        conv = await sv.get_or_create_conversation(s, client.id, pu.id, None)
        assert (await sv.get_or_create_conversation(s, client.id, pu.id, None)).id == conv.id
        await sv.add_message(s, conv, client, "Olá", None)
        await sv.add_message(s, conv, pu, None, "photo-id")
        outsider, _ = await make_user(s, 52, "Intruso")
        with pytest.raises(sv.BusinessError):
            await sv.add_message(s, conv, outsider, "hack", None)
        with pytest.raises(sv.BusinessError):
            await sv.get_or_create_conversation(s, client.id, client.id, None)
        convs = await sv.conversations_for(s, client)
        assert convs[0][2] == 1  # 1 não lida
        await sv.conversation_history(s, conv, client)
        assert (await sv.conversations_for(s, client))[0][2] == 0

        data = await sv.export_user_data(s, pu)
        assert data["provider_profile"]["business_name"] == "Pro Lda" and len(data["messages_sent"]) == 1

        await sv.delete_user_data(s, pu)
        await s.commit()
        assert await s.get(User, pu.id) is None
        assert (await s.execute(select(func.count(ProviderProfile.id)))).scalar_one() == 0
        assert (await s.execute(select(func.count(Message.id)))).scalar_one() == 0


async def test_promo_and_admin_grant_without_charging(db):
    async with db.session() as s:
        u, _ = await make_user(s, 60, "Promo")
        s.add(Promotion(code="LAUNCH", plan_code="premium", days=60, max_uses=1))
        await s.flush()
        sub = await sv.redeem_promo(s, u, "launch")
        assert u.plan_code == "premium" and sub.source == "promo" and u.has_paid_plan()
        with pytest.raises(sv.BusinessError):
            await sv.redeem_promo(s, u, "LAUNCH")
        u2, _ = await make_user(s, 61, "Other")
        with pytest.raises(sv.BusinessError):  # esgotado
            await sv.redeem_promo(s, u2, "LAUNCH")
        await sv.activate_plan(s, u2, "pro", 30, source="admin_grant")
        assert u2.plan_code == "pro" and (await sv.stats(s))["revenue_stars"] == 0


async def test_db_fsm_storage_persists(db):
    from aiogram.fsm.storage.base import StorageKey

    from storage import DBStorage
    st = DBStorage(db)
    key = StorageKey(bot_id=1, chat_id=5, user_id=5)
    assert await st.get_state(key) is None
    await st.set_state(key, "Req:city")
    await st.set_data(key, {"a": 1})
    st2 = DBStorage(db)  # "reinício"
    assert await st2.get_state(key) == "Req:city" and await st2.get_data(key) == {"a": 1}
    await st2.set_state(key, None)
    assert await st2.get_state(key) is None
