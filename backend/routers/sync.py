"""
Endpoints de sincronización offline/online.

POST /sync/push  → el cliente envía sus cambios pendientes al servidor
GET  /sync/pull  → el cliente pide los datos nuevos desde su último sync
GET  /sync/comedores → el cliente descarga los comedores asignados
"""
import os
import time
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
from pydantic import BaseModel

from backend.database import get_db
from backend.models import Supervisor, Comedor, Visita, ItemChecklist

router = APIRouter(prefix="/sync", tags=["sincronización"])

SECRET_KEY = os.getenv("SECRET_KEY", "supervi-clave-secreta-cambiar-en-produccion")
ALGORITHM = "HS256"


# ── Autenticación ──────────────────────────────────────────────────────────

async def supervisor_actual(
    authorization: str = Header(...),
    db: AsyncSession = Depends(get_db),
) -> Supervisor:
    """Extrae el supervisor del JWT enviado en el header Authorization."""
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sync_id: str = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    resultado = await db.execute(select(Supervisor).where(Supervisor.sync_id == sync_id))
    supervisor = resultado.scalar_one_or_none()

    if not supervisor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supervisor no encontrado")

    return supervisor


# ── Schemas ────────────────────────────────────────────────────────────────

class OperacionSync(BaseModel):
    tabla: str
    operacion: str          # INSERT, UPDATE, DELETE
    record_sync_id: str
    datos: dict[str, Any]
    timestamp: int


class PushRequest(BaseModel):
    operaciones: list[OperacionSync]


class PushResponse(BaseModel):
    procesadas: int
    errores: list[str]


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/comedores")
async def obtener_comedores(
    supervisor: Supervisor = Depends(supervisor_actual),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve todos los comedores activos asignados al supervisor.
    El cliente los guarda en SQLite local para usarlos offline.
    """
    resultado = await db.execute(
        select(Comedor).where(Comedor.activo == True)
    )
    comedores = resultado.scalars().all()

    return [
        {
            "sync_id": c.sync_id,
            "nombre": c.nombre,
            "municipio": c.municipio,
            "institucion": c.institucion,
            "direccion": c.direccion,
        }
        for c in comedores
    ]


@router.post("/push", response_model=PushResponse)
async def push_cambios(
    body: PushRequest,
    supervisor: Supervisor = Depends(supervisor_actual),
    db: AsyncSession = Depends(get_db),
):
    """
    Recibe las operaciones pendientes del cliente (INSERT/UPDATE de visitas y checklist).
    Procesa cada una y guarda en PostgreSQL.
    Ignora duplicados (idempotente — si el cliente reenvía algo ya procesado, no falla).
    """
    procesadas = 0
    errores = []

    for op in body.operaciones:
        try:
            if op.tabla == "visitas":
                await _procesar_visita(op, supervisor, db)
            elif op.tabla == "checklist_items":
                await _procesar_item_checklist(op, db)
            else:
                errores.append(f"Tabla desconocida: {op.tabla}")
                continue
            procesadas += 1
        except Exception as exc:
            errores.append(f"{op.record_sync_id}: {str(exc)}")

    await db.commit()
    return PushResponse(procesadas=procesadas, errores=errores)


@router.get("/pull")
async def pull_cambios(
    since: int = 0,
    supervisor: Supervisor = Depends(supervisor_actual),
    db: AsyncSession = Depends(get_db),
):
    """
    Devuelve los cambios nuevos desde el timestamp dado.
    El cliente usa esto para recibir actualizaciones de otros dispositivos o del admin.
    since=0 descarga todo (primera sincronización).
    """
    since_dt = datetime.fromtimestamp(since) if since > 0 else datetime(2000, 1, 1)

    # Visitas del supervisor actualizadas después del último sync
    res_visitas = await db.execute(
        select(Visita).where(
            Visita.supervisor_sync_id == supervisor.sync_id,
            Visita.actualizado_en >= since_dt,
        )
    )
    visitas = res_visitas.scalars().all()

    visitas_data = []
    for v in visitas:
        res_items = await db.execute(
            select(ItemChecklist).where(ItemChecklist.visita_sync_id == v.sync_id)
        )
        items = res_items.scalars().all()

        visitas_data.append({
            "sync_id": v.sync_id,
            "comedor_sync_id": v.comedor_sync_id,
            "fecha": v.fecha.isoformat(),
            "estado": v.estado,
            "observaciones_generales": v.observaciones_generales,
            "checklist": [
                {
                    "sync_id": i.sync_id,
                    "categoria": i.categoria,
                    "pregunta": i.pregunta,
                    "respuesta": i.respuesta,
                    "observacion": i.observacion,
                    "orden": i.orden,
                }
                for i in items
            ],
        })

    return {
        "timestamp_servidor": int(time.time()),
        "visitas": visitas_data,
    }


# ── Procesadores internos ──────────────────────────────────────────────────

async def _procesar_visita(op: OperacionSync, supervisor: Supervisor, db: AsyncSession):
    """Inserta o actualiza una visita en PostgreSQL."""
    datos = op.datos

    # Verificar que el comedor exista en el servidor
    res = await db.execute(
        select(Comedor).where(Comedor.sync_id == datos.get("comedor_sync_id"))
    )
    comedor = res.scalar_one_or_none()
    if not comedor:
        raise ValueError(f"Comedor no encontrado: {datos.get('comedor_sync_id')}")

    # Idempotencia: si ya existe con ese sync_id, actualizar en vez de duplicar
    res_existente = await db.execute(
        select(Visita).where(Visita.sync_id == op.record_sync_id)
    )
    existente = res_existente.scalar_one_or_none()

    if existente:
        # UPDATE
        existente.estado = datos.get("estado", existente.estado)
        existente.observaciones_generales = datos.get("observaciones_generales", existente.observaciones_generales)
        existente.actualizado_en = datetime.now()
    else:
        # INSERT
        visita = Visita(
            sync_id=op.record_sync_id,
            supervisor_sync_id=supervisor.sync_id,
            comedor_sync_id=datos["comedor_sync_id"],
            fecha=datetime.fromisoformat(datos["fecha"]) if isinstance(datos.get("fecha"), str) else datetime.now(),
            estado=datos.get("estado", "borrador"),
            observaciones_generales=datos.get("observaciones_generales", ""),
        )
        db.add(visita)


async def _procesar_item_checklist(op: OperacionSync, db: AsyncSession):
    """Inserta o actualiza un ítem del checklist en PostgreSQL."""
    datos = op.datos

    res_existente = await db.execute(
        select(ItemChecklist).where(ItemChecklist.sync_id == op.record_sync_id)
    )
    existente = res_existente.scalar_one_or_none()

    if existente:
        existente.respuesta = datos.get("respuesta", existente.respuesta)
        existente.observacion = datos.get("observacion", existente.observacion)
    else:
        item = ItemChecklist(
            sync_id=op.record_sync_id,
            visita_sync_id=datos["visita_sync_id"],
            categoria=datos.get("categoria", ""),
            pregunta=datos.get("pregunta", ""),
            respuesta=datos.get("respuesta"),
            observacion=datos.get("observacion", ""),
            orden=datos.get("orden", 0),
        )
        db.add(item)
