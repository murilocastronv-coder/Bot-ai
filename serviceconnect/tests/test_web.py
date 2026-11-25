"""Painel admin, webhook e páginas públicas."""
import re

import pytest
from fastapi.testclient import TestClient

import services as sv


@pytest.fixture
def web_db(tmp_path):
    # banco criado e iniciado dentro do loop do servidor de teste (lifespan)
    from conftest import make_database
    from database import set_db
    database = make_database(tmp_path, "web")
    set_db(database)
    return database


@pytest.fixture
def client(web_db, monkeypatch):
    import config
    monkeypatch.setattr(config.settings, "bot_token", "")  # sem Telegram real nos testes
    import main
    monkeypatch.setattr(main, "get_db", lambda: web_db)
    with TestClient(main.app) as c:
        yield c


def csrf_of(html: str) -> str:
    return re.search(r'name="csrf" value="([^"]+)"', html).group(1)


def login(c):
    page = c.get("/admin/login")
    r = c.post("/admin/login", data={"username": "admin", "password": "test-password-123", "csrf": csrf_of(page.text)},
               follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    return csrf_of(c.get("/admin").text)


def test_public_pages(client):
    assert client.get("/health").json() == {"status": "ok"}
    for lang in ("pt", "en", "fr", "es"):
        assert "RGPD" in client.get(f"/privacy?lang={lang}").text or "GDPR" in client.get(f"/privacy?lang={lang}").text
        assert client.get(f"/terms?lang={lang}").status_code == 200


def test_webhook_requires_secret(client):
    assert client.post("/telegram/webhook", json={"update_id": 1}).status_code == 403
    r = client.post("/telegram/webhook", json={"update_id": 1}, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"})
    assert r.status_code == 403


def test_admin_requires_login_and_rejects_bad_password(client):
    r = client.get("/admin/users", follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin/login"
    page = client.get("/admin/login")
    client.post("/admin/login", data={"username": "admin", "password": "nope", "csrf": csrf_of(page.text)})
    assert client.get("/admin", follow_redirects=False).status_code == 303


def test_admin_pages_and_actions(client, web_db):
    csrf = login(client)
    for path in ("/admin", "/admin/users", "/admin/requests", "/admin/categories", "/admin/reports", "/admin/broadcast",
                 "/admin/monetization", "/admin/cities", "/admin/referrals"):
        assert client.get(path).status_code == 200, path

    # CSRF obrigatório em ações
    assert client.post("/admin/categories", data={"name_pt": "X", "csrf": "bad"}).status_code == 403

    # nova categoria
    r = client.post("/admin/categories", data={"csrf": csrf, "emoji": "🧪", "name_pt": "Testes", "name_en": "Tests", "sort": 1})
    assert r.status_code == 200 and "Testes" in r.text

    # monetização só ativa com confirmação explícita
    client.post("/admin/monetization/toggle", data={"csrf": csrf})
    assert "desativadas" in client.get("/admin/monetization").text
    client.post("/admin/monetization/toggle", data={"csrf": csrf, "confirm": "ATIVAR"})
    assert "cobranças ATIVAS" in client.get("/admin/monetization").text

    # editar preço de plano
    html = client.get("/admin/monetization").text
    pro_id = re.search(r'action="/admin/plans/(\d+)"[^>]*>\s*<input type="hidden" name="csrf" value="[^"]+">\s*<b[^>]*>pro<', html).group(1)
    client.post(f"/admin/plans/{pro_id}", data={"csrf": csrf, "name": "Profissional", "price_eur": "12.5", "price_stars": "600", "active": "1"})
    assert 'value="12.5"' in client.get("/admin/monetization").text

    # promoção + cidade + backup
    client.post("/admin/promotions", data={"csrf": csrf, "code": "beta2026", "plan_code": "premium", "days": 30, "max_uses": 10})
    assert "BETA2026" in client.get("/admin/monetization").text
    client.post("/admin/cities", data={"csrf": csrf, "name": "Évora", "country": "PT", "lat": 38.57, "lon": -7.91})
    assert "Évora" in client.get("/admin/cities").text
    backup = client.get("/admin/backup")
    assert backup.status_code == 200 and "categories" in backup.json()


def test_admin_user_moderation(client, web_db):
    db = web_db
    async def mk():
        async with db.session() as s:
            u, _ = await sv.get_or_create_user(s, 777, "Fraude", None, "pt")
            u.onboarded = True
            await s.commit()
            return u.id

    async def get(uid):
        async with db.session() as s:
            from models import User
            return await s.get(User, uid)

    uid = client.portal.call(mk)
    csrf = login(client)
    assert "Fraude" in client.get("/admin/users?q=Fraude").text
    assert client.get(f"/admin/users/{uid}").status_code == 200
    client.post(f"/admin/users/{uid}/action", data={"csrf": csrf, "action": "ban", "reason": "spam"})
    u = client.portal.call(get, uid)
    assert u.is_banned and u.ban_reason == "spam"
    client.post(f"/admin/users/{uid}/action", data={"csrf": csrf, "action": "grant", "plan": "premium", "days": 90})
    assert client.portal.call(get, uid).plan_code == "premium"
    client.post(f"/admin/users/{uid}/action", data={"csrf": csrf, "action": "delete"})
    assert client.portal.call(get, uid) is None
