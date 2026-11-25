import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "test-password-123")
os.environ.setdefault("SESSION_SECRET", "test-session-secret")
os.environ.setdefault("WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("ADMIN_TELEGRAM_IDS", "999")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000")

import pytest  # noqa: E402
from aiogram import Bot  # noqa: E402
from aiogram.client.session.base import BaseSession  # noqa: E402
from aiogram.types import Chat, Message, User as TgUser  # noqa: E402

from database import Database, set_db  # noqa: E402


def make_database(tmp_path, name="test"):
    """SQLite por padrão; com TEST_DATABASE_URL usa PostgreSQL real num esquema temporário."""
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        import uuid
        return Database(url, schema=f"t_{uuid.uuid4().hex[:10]}")
    return Database(f"sqlite+aiosqlite:///{tmp_path}/{name}.db")


async def drop_schema(database):
    if database.is_postgres:
        from sqlalchemy import text
        async with database.engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{database.schema}" CASCADE'))


@pytest.fixture
async def db(tmp_path):
    database = make_database(tmp_path)
    await database.init()
    set_db(database)
    yield database
    await drop_schema(database)
    await database.close()


class FakeSession(BaseSession):
    """Sessão HTTP falsa do aiogram: regista todas as chamadas à API do Telegram."""

    def __init__(self):
        super().__init__()
        self.calls: list = []
        self._mid = 100

    async def make_request(self, bot, method, timeout=None):
        self.calls.append(method)
        ret = getattr(method, "__returning__", None)
        name = getattr(ret, "__name__", str(ret))
        chat_id = getattr(method, "chat_id", 1) or 1
        if ret is Message or "Message" == name:
            self._mid += 1
            return Message(message_id=self._mid, date=datetime.now(), chat=Chat(id=chat_id, type="private"),
                           text=getattr(method, "text", None))
        if "list" in str(ret) and "Message" in str(ret):
            self._mid += 1
            return [Message(message_id=self._mid, date=datetime.now(), chat=Chat(id=chat_id, type="private"))]
        if ret is TgUser:
            return TgUser(id=42, is_bot=True, first_name="ServiceConnect", username="ServiceConnectBot")
        return True

    async def close(self):
        pass

    async def stream_content(self, *a, **k):  # pragma: no cover
        yield b""

    def sent_to(self, chat_id: int) -> list:
        return [c for c in self.calls if getattr(c, "chat_id", None) == chat_id]

    def texts_to(self, chat_id: int) -> list[str]:
        return [getattr(c, "text", None) or getattr(c, "caption", None) or "" for c in self.sent_to(chat_id)]


@pytest.fixture
def fake_bot():
    session = FakeSession()
    bot = Bot("123456:TEST-TOKEN", session=session)
    return bot, session
