"""Ponto de entrada: servidor FastAPI (webhook do Telegram + painel admin + páginas legais).

Produção (Render):   uvicorn main:app --host 0.0.0.0 --port $PORT
Desenvolvimento:     python main.py --polling   (sem URL pública, usa long polling)
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import logging
import secrets
import sys
from contextlib import asynccontextmanager

from aiogram.types import Update
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

import admin
import services as sv
from bot import create_bot, create_dispatcher, setup_bot_profile
from config import settings
from database import get_db
from legal import render_legal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("serviceconnect")

# segredo do webhook: usa o do ambiente ou gera um (o Telegram reenvia-o em cada pedido)
WEBHOOK_SECRET = settings.webhook_secret or secrets.token_urlsafe(32)
WEBHOOK_SECRET = "".join(ch for ch in WEBHOOK_SECRET if ch.isalnum() or ch in "_-")[:256]


async def maintenance_loop() -> None:
    """Tarefas periódicas: expira planos e limpa estados de conversa antigos."""
    from datetime import timedelta

    from sqlalchemy import delete

    from models import FSMRecord, utcnow
    while True:
        await asyncio.sleep(60)  # não compete com o arranque
        try:
            async with get_db().session() as s:
                await sv.expire_plans(s)
                await s.execute(delete(FSMRecord).where(FSMRecord.updated_at < utcnow() - timedelta(days=14)))
                await s.commit()
        except Exception:  # noqa: BLE001
            log.exception("maintenance failed")
        await asyncio.sleep(3540)


async def keep_alive_loop() -> None:
    """Plano free do Render: o serviço dorme após 15 min sem tráfego. Um ping a cada 10 min mantém o bot rápido."""
    import aiohttp
    url = f"{settings.webhook_base_url}/health"
    await asyncio.sleep(30)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as http:
        while True:
            try:
                async with http.get(url) as r:
                    await r.read()
            except Exception as ex:  # noqa: BLE001
                log.warning("keep-alive falhou: %s", ex)
            await asyncio.sleep(600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database = get_db()
    await database.init()
    app.state.bot = None
    app.state.dp = None
    tasks = [asyncio.create_task(maintenance_loop())]
    if settings.keep_alive and settings.webhook_base_url.startswith("https://"):
        tasks.append(asyncio.create_task(keep_alive_loop()))
    if settings.bot_token:
        bot = create_bot()
        dp = create_dispatcher(database)
        app.state.bot, app.state.dp = bot, dp
        try:
            await setup_bot_profile(bot)
            if settings.webhook_url:
                await bot.set_webhook(settings.webhook_url, secret_token=WEBHOOK_SECRET, drop_pending_updates=False,
                                      allowed_updates=dp.resolve_used_update_types(), max_connections=40)
                log.info("Webhook configurado: %s", settings.webhook_url)
            else:
                log.warning("Sem WEBHOOK_BASE_URL/RENDER_EXTERNAL_URL: use `python main.py --polling` em desenvolvimento.")
        except Exception:  # noqa: BLE001
            log.exception("Falha ao configurar o bot (verifique BOT_TOKEN)")
    else:
        log.warning("BOT_TOKEN não definido: só o painel e as páginas web estão ativos.")
    yield
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)  # espera terminar antes de fechar o banco
    if app.state.bot:
        await app.state.bot.session.close()
    await database.close()


app = FastAPI(title="ServiceConnect", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(SessionMiddleware, secret_key=settings.session_secret or secrets.token_urlsafe(48),
                   session_cookie="sc_admin", max_age=60 * 60 * 12, same_site="strict",
                   https_only=settings.webhook_base_url.startswith("https"))
app.include_router(admin.router)


@app.exception_handler(admin.NeedLogin)
async def need_login(request: Request, exc: admin.NeedLogin):
    return RedirectResponse("/admin/login", status_code=303)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/admin"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.post(settings.webhook_path)
async def telegram_webhook(request: Request):
    token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not hmac.compare_digest(token, WEBHOOK_SECRET):
        raise HTTPException(status_code=403)
    bot, dp = request.app.state.bot, request.app.state.dp
    if not bot:
        raise HTTPException(status_code=503)
    update = Update.model_validate(await request.json(), context={"bot": bot})
    try:
        await dp.feed_update(bot, update)
    except Exception:  # noqa: BLE001  — nunca devolve erro ao Telegram (evita reenvios em loop)
        log.exception("update %s falhou", update.update_id)
    return JSONResponse({"ok": True})


@app.get("/")
async def home():
    return HTMLResponse('<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1"><title>ServiceConnect</title>'
                        '<body style="font-family:system-ui;max-width:640px;margin:40px auto;padding:0 16px">'
                        '<h1>ServiceConnect</h1><p>Marketplace de serviços no Telegram — 100% gratuito.</p>'
                        '<p><a href="/terms">Termos</a> · <a href="/privacy">Privacidade</a></p></body>')


@app.get("/health")
async def health():
    async with get_db().session() as s:
        from sqlalchemy import text
        await s.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/terms", response_class=HTMLResponse)
async def terms(lang: str = "pt"):
    return render_legal("terms", lang)


@app.get("/privacy", response_class=HTMLResponse)
async def privacy(lang: str = "pt"):
    return render_legal("privacy", lang)


async def run_polling() -> None:
    database = get_db()
    await database.init()
    bot, dp = create_bot(), create_dispatcher(database)
    await bot.delete_webhook(drop_pending_updates=False)
    await setup_bot_profile(bot)
    log.info("Polling iniciado")
    with contextlib.suppress(asyncio.CancelledError):
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    if "--polling" in sys.argv:
        asyncio.run(run_polling())
    else:
        import os

        import uvicorn
        uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), proxy_headers=True, forwarded_allow_ips="*")
