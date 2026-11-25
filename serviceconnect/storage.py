"""Armazenamento do estado das conversas (FSM) no PostgreSQL — nada se perde quando o Render reinicia."""
from __future__ import annotations

from typing import Any, Mapping

from aiogram.fsm.state import State
from aiogram.fsm.storage.base import BaseStorage, StateType, StorageKey

from models import FSMRecord, utcnow


def key_str(key: StorageKey) -> str:
    return f"{key.bot_id}:{key.chat_id}:{key.user_id}:{key.thread_id or 0}:{key.destiny}"


class DBStorage(BaseStorage):
    def __init__(self, database):
        self.db = database

    async def _get(self, s, key: StorageKey) -> FSMRecord | None:
        return await s.get(FSMRecord, key_str(key))

    async def set_state(self, key: StorageKey, state: StateType = None) -> None:
        value = state.state if isinstance(state, State) else state
        async with self.db.session() as s:
            rec = await self._get(s, key)
            if rec is None:
                if value is None:
                    return
                rec = FSMRecord(key=key_str(key), state=value, data={})
                s.add(rec)
            else:
                rec.state = value
                rec.updated_at = utcnow()
            await s.commit()

    async def get_state(self, key: StorageKey) -> str | None:
        async with self.db.session() as s:
            rec = await self._get(s, key)
            return rec.state if rec else None

    async def set_data(self, key: StorageKey, data: Mapping[str, Any]) -> None:
        async with self.db.session() as s:
            rec = await self._get(s, key)
            if rec is None:
                if not data:
                    return
                rec = FSMRecord(key=key_str(key), state=None, data=dict(data))
                s.add(rec)
            else:
                rec.data = dict(data)
                rec.updated_at = utcnow()
            await s.commit()

    async def get_data(self, key: StorageKey) -> dict[str, Any]:
        async with self.db.session() as s:
            rec = await self._get(s, key)
            return dict(rec.data or {}) if rec else {}

    async def close(self) -> None:  # o engine é fechado pelo Database
        return None
