"""
Configuración de la conexión a PostgreSQL con SQLAlchemy async.
La URL de la base de datos se lee desde variable de entorno DATABASE_URL.
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Lee la URL de conexión desde variable de entorno
# En Railway se configura automáticamente al agregar el servicio PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/supervi"
)

# asyncpg es el driver async para PostgreSQL
# Railway entrega URLs con "postgresql://" — lo convertimos a "postgresql+asyncpg://"
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Dependencia de FastAPI: provee una sesión de base de datos por request."""
    async with SessionLocal() as session:
        yield session


async def crear_tablas():
    """Crea todas las tablas en PostgreSQL al iniciar el servidor."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
