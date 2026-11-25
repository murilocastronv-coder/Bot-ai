"""Conexão PostgreSQL (SQLAlchemy assíncrono), criação de tabelas e dados iniciais."""
from __future__ import annotations

import re
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from models import Base, Category, City, Plan, Setting

DEFAULT_CATEGORIES = [
    ("cleaning", "🧹", {"pt": "Limpeza residencial", "en": "Home cleaning", "fr": "Ménage à domicile", "es": "Limpieza del hogar"}),
    ("gardening", "🌿", {"pt": "Jardinagem", "en": "Gardening", "fr": "Jardinage", "es": "Jardinería"}),
    ("moving", "🚚", {"pt": "Mudanças", "en": "Moving", "fr": "Déménagement", "es": "Mudanzas"}),
    ("painting", "🎨", {"pt": "Pintura", "en": "Painting", "fr": "Peinture", "es": "Pintura"}),
    ("construction", "🏗", {"pt": "Construção", "en": "Construction", "fr": "Construction", "es": "Construcción"}),
    ("electrical", "💡", {"pt": "Eletricidade", "en": "Electrical", "fr": "Électricité", "es": "Electricidad"}),
    ("plumbing", "🚰", {"pt": "Encanamento", "en": "Plumbing", "fr": "Plomberie", "es": "Fontanería"}),
    ("it", "💻", {"pt": "Informática", "en": "IT support", "fr": "Informatique", "es": "Informática"}),
    ("mechanics", "🔧", {"pt": "Mecânica", "en": "Mechanics", "fr": "Mécanique", "es": "Mecánica"}),
    ("transport", "🚗", {"pt": "Transporte", "en": "Transport", "fr": "Transport", "es": "Transporte"}),
    ("beauty", "💅", {"pt": "Beleza e estética", "en": "Beauty", "fr": "Beauté et esthétique", "es": "Belleza y estética"}),
    ("tutoring", "📚", {"pt": "Aulas particulares", "en": "Private lessons", "fr": "Cours particuliers", "es": "Clases particulares"}),
    ("pets", "🐾", {"pt": "Cuidados com animais", "en": "Pet care", "fr": "Soins des animaux", "es": "Cuidado de mascotas"}),
    ("furniture", "🪑", {"pt": "Montagem de móveis", "en": "Furniture assembly", "fr": "Montage de meubles", "es": "Montaje de muebles"}),
    ("repairs", "🛠", {"pt": "Reparações domésticas", "en": "Home repairs", "fr": "Réparations domestiques", "es": "Reparaciones del hogar"}),
    ("photography", "📷", {"pt": "Fotografia", "en": "Photography", "fr": "Photographie", "es": "Fotografía"}),
    ("webdev", "🌐", {"pt": "Desenvolvimento de sites", "en": "Website development", "fr": "Création de sites web", "es": "Desarrollo web"}),
    ("other", "✨", {"pt": "Outros serviços", "en": "Other services", "fr": "Autres services", "es": "Otros servicios"}),
]

DEFAULT_PLANS = [
    # code, name, eur, stars, sort, features
    ("free", "Gratuito", 0.0, 0, 0, ["basic"]),
    ("pro", "Profissional", 9.99, 500, 1, ["highlight", "priority_notifications", "stats"]),
    ("premium", "Premium", 19.99, 1000, 2, ["highlight", "sponsored", "priority_notifications", "stats", "visibility"]),
    ("business", "Empresa", 39.99, 2000, 3, ["highlight", "sponsored", "priority_notifications", "stats", "visibility", "exclusive"]),
]

# Cidades com coordenadas para busca por distância (o admin pode adicionar mais)
DEFAULT_CITIES = [
    ("Lisboa", "PT", 38.7223, -9.1393), ("Porto", "PT", 41.1579, -8.6291), ("Braga", "PT", 41.5454, -8.4265),
    ("Coimbra", "PT", 40.2033, -8.4103), ("Faro", "PT", 37.0194, -7.9304), ("Setúbal", "PT", 38.5244, -8.8882),
    ("São Paulo", "BR", -23.5505, -46.6333), ("Rio de Janeiro", "BR", -22.9068, -43.1729), ("Belo Horizonte", "BR", -19.9167, -43.9345),
    ("Brasília", "BR", -15.7939, -47.8828), ("Salvador", "BR", -12.9777, -38.5016), ("Curitiba", "BR", -25.4284, -49.2733),
    ("Porto Alegre", "BR", -30.0346, -51.2177), ("Recife", "BR", -8.0476, -34.8770), ("Fortaleza", "BR", -3.7319, -38.5267),
    ("Paris", "FR", 48.8566, 2.3522), ("Lyon", "FR", 45.7640, 4.8357), ("Marseille", "FR", 43.2965, 5.3698),
    ("Toulouse", "FR", 43.6047, 1.4442), ("Nice", "FR", 43.7102, 7.2620), ("Bordeaux", "FR", 44.8378, -0.5792),
    ("Madrid", "ES", 40.4168, -3.7038), ("Barcelona", "ES", 41.3874, 2.1686), ("Valencia", "ES", 39.4699, -0.3763),
    ("Sevilla", "ES", 37.3891, -5.9845), ("London", "GB", 51.5072, -0.1276), ("Manchester", "GB", 53.4808, -2.2426),
    ("Luxembourg", "LU", 49.6116, 6.1319), ("Genève", "CH", 46.2044, 6.1432), ("Bruxelles", "BE", 50.8503, 4.3517),
    ("New York", "US", 40.7128, -74.0060), ("Miami", "US", 25.7617, -80.1918), ("Luanda", "AO", -8.8390, 13.2894),
    ("Maputo", "MZ", -25.9692, 32.5732), ("Ciudad de México", "MX", 19.4326, -99.1332), ("Buenos Aires", "AR", -34.6037, -58.3816),
]

DEFAULT_SETTINGS = {
    "monetization_enabled": False,  # cobranças DESLIGADAS no lançamento
    "currency": "EUR",
    "early_adopter_limit": 1000,
}


def normalize_url(url: str) -> str:
    """Converte postgres:// (formato do Render) para o driver asyncpg."""
    if url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    # asyncpg não aceita parâmetros libpq como ?sslmode=
    if url.startswith("postgresql+asyncpg://") and "?" in url:
        url = url.split("?", 1)[0]
    return url


def _safe_schema(name: str) -> str:
    return name if re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", name or "") else "serviceconnect"


class Database:
    def __init__(self, url: str | None = None, schema: str | None = None):
        self.url = normalize_url(url or settings.database_url)
        self.is_postgres = self.url.startswith("postgresql")
        self.schema = _safe_schema(schema or settings.db_schema) if self.is_postgres else None
        kwargs: dict = {"pool_pre_ping": True}
        if self.is_postgres:
            kwargs.update(pool_size=5, max_overflow=10, pool_recycle=1800,
                          connect_args={"server_settings": {"search_path": f"{self.schema},public"}})
        self.engine: AsyncEngine = create_async_engine(self.url, **kwargs)
        self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)

    async def init(self) -> None:
        async with self.engine.begin() as conn:
            if self.is_postgres:
                await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{self.schema}"'))
            await conn.run_sync(Base.metadata.create_all)
        await self.seed()

    async def seed(self) -> None:
        async with self.session() as s:
            if not (await s.execute(select(Category.id).limit(1))).first():
                for i, (key, emoji, names) in enumerate(DEFAULT_CATEGORIES):
                    s.add(Category(key=key, emoji=emoji, names=names, sort=i))
            if not (await s.execute(select(Plan.id).limit(1))).first():
                for code, name, eur, stars, sort, feats in DEFAULT_PLANS:
                    s.add(Plan(code=code, name=name, price_eur=eur, price_stars=stars, sort=sort, features=feats))
            if not (await s.execute(select(City.id).limit(1))).first():
                for name, cc, lat, lon in DEFAULT_CITIES:
                    s.add(City(name=name, country=cc, lat=lat, lon=lon))
            for k, v in DEFAULT_SETTINGS.items():
                if await s.get(Setting, k) is None:
                    s.add(Setting(key=k, value=v))
            await s.commit()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.sessionmaker() as s:
            try:
                yield s
            except Exception:
                await s.rollback()
                raise

    async def close(self) -> None:
        await self.engine.dispose()


db: Database | None = None


def get_db() -> Database:
    global db
    if db is None:
        db = Database()
    return db


def set_db(new: Database) -> None:
    global db
    db = new
