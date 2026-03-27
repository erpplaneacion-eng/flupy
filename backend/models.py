"""
Modelos de base de datos del servidor (PostgreSQL) con SQLAlchemy.
Son el espejo exacto de los modelos SQLite del cliente,
pero con tipos de PostgreSQL y relaciones declaradas con SQLAlchemy.
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, DateTime, Integer, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Supervisor(Base):
    __tablename__ = "supervisores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_id: Mapped[str] = mapped_column(String(36), unique=True, default=gen_uuid)
    nombre: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    cedula: Mapped[str] = mapped_column(String(20), unique=True)
    zona: Mapped[str] = mapped_column(String(100), default="")
    password_hash: Mapped[str] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    visitas: Mapped[list["Visita"]] = relationship("Visita", back_populates="supervisor")


class Comedor(Base):
    __tablename__ = "comedores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_id: Mapped[str] = mapped_column(String(36), unique=True, default=gen_uuid)
    nombre: Mapped[str] = mapped_column(String(200))
    municipio: Mapped[str] = mapped_column(String(100))
    institucion: Mapped[str] = mapped_column(String(200))
    direccion: Mapped[str] = mapped_column(String(300), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    visitas: Mapped[list["Visita"]] = relationship("Visita", back_populates="comedor")


class Visita(Base):
    __tablename__ = "visitas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_id: Mapped[str] = mapped_column(String(36), unique=True, default=gen_uuid)
    supervisor_sync_id: Mapped[str] = mapped_column(String(36), ForeignKey("supervisores.sync_id"))
    comedor_sync_id: Mapped[str] = mapped_column(String(36), ForeignKey("comedores.sync_id"))
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    estado: Mapped[str] = mapped_column(String(20), default="borrador")
    observaciones_generales: Mapped[str] = mapped_column(Text, default="")
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    actualizado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    supervisor: Mapped["Supervisor"] = relationship("Supervisor", back_populates="visitas")
    comedor: Mapped["Comedor"] = relationship("Comedor", back_populates="visitas")
    checklist: Mapped[list["ItemChecklist"]] = relationship("ItemChecklist", back_populates="visita")


class ItemChecklist(Base):
    __tablename__ = "checklist_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sync_id: Mapped[str] = mapped_column(String(36), unique=True, default=gen_uuid)
    visita_sync_id: Mapped[str] = mapped_column(String(36), ForeignKey("visitas.sync_id"))
    categoria: Mapped[str] = mapped_column(String(50))
    pregunta: Mapped[str] = mapped_column(Text)
    respuesta: Mapped[str | None] = mapped_column(String(5), nullable=True)
    observacion: Mapped[str] = mapped_column(Text, default="")
    orden: Mapped[int] = mapped_column(Integer, default=0)
    creado_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    visita: Mapped["Visita"] = relationship("Visita", back_populates="checklist")
