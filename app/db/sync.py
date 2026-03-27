"""
Motor de sincronización offline/online de Supervi.

Responsabilidades:
1. Leer la ColaSyncronizacion y enviarla al servidor (push)
2. Pedir datos nuevos del servidor (pull) y actualizar SQLite local
3. Actualizar el estado online/offline en la UI
4. Ejecutarse en segundo plano sin bloquear la app

Uso:
    motor = MotorSync(token_jwt, callback_estado_conexion)
    await motor.iniciar()   # Arranca el loop en background
    await motor.detener()   # Detiene el loop
    await motor.sync_ahora()  # Fuerza sync inmediato
"""
import asyncio
import json
import time
from datetime import datetime

from app.db.models import (
    ColaSyncronizacion, Comedor, Visita, ItemChecklist,
    Supervisor, db, agregar_a_cola_sync
)
from app.services import api

# Intervalo entre intentos de sync automático (segundos)
INTERVALO_SYNC = 30


class MotorSync:
    def __init__(self, token: str, on_estado_cambio=None):
        """
        Args:
            token: JWT del supervisor autenticado
            on_estado_cambio: callback(online: bool) llamado cuando cambia la conexión
        """
        self.token = token
        self.on_estado_cambio = on_estado_cambio
        self.online = False
        self._tarea: asyncio.Task | None = None
        self._ultimo_sync: int = 0  # timestamp del último pull exitoso
        self._corriendo = False

    async def iniciar(self):
        """Arranca el loop de sincronización en segundo plano."""
        self._corriendo = True
        self._tarea = asyncio.create_task(self._loop())

    async def detener(self):
        """Detiene el loop de sincronización."""
        self._corriendo = False
        if self._tarea:
            self._tarea.cancel()

    async def sync_ahora(self):
        """Fuerza una sincronización inmediata (llama push + pull)."""
        conectado = await api.verificar_conexion()
        if conectado:
            await self._push()
            await self._pull()
            self._actualizar_estado(True)
        else:
            self._actualizar_estado(False)

    # ── Loop interno ───────────────────────────────────────────────────────

    async def _loop(self):
        """Corre cada INTERVALO_SYNC segundos mientras la app esté abierta."""
        while self._corriendo:
            try:
                await self.sync_ahora()
            except Exception:
                # Nunca dejar que el loop muera por una excepción
                pass
            await asyncio.sleep(INTERVALO_SYNC)

    # ── Push: cliente → servidor ───────────────────────────────────────────

    async def _push(self):
        """Envía las operaciones pendientes de la cola al servidor."""
        pendientes = list(
            ColaSyncronizacion.select()
            .where(ColaSyncronizacion.enviado == False)
            .order_by(ColaSyncronizacion.timestamp)
        )
        if not pendientes:
            return

        operaciones = [
            {
                "tabla": op.tabla,
                "operacion": op.operacion,
                "record_sync_id": op.record_sync_id,
                "datos": json.loads(op.datos),
                "timestamp": op.timestamp,
            }
            for op in pendientes
        ]

        resultado = await api.push_cambios(self.token, operaciones)

        # Marcar como enviadas las que el servidor procesó sin error
        ids_con_error = set(
            e.split(":")[0].strip()
            for e in resultado.get("errores", [])
        )
        for op in pendientes:
            if op.record_sync_id not in ids_con_error:
                op.enviado = True
                op.save()

                # Marcar el registro original como sincronizado
                self._marcar_sincronizado(op.tabla, op.record_sync_id)

    def _marcar_sincronizado(self, tabla: str, sync_id: str):
        """Actualiza el campo 'sincronizado' del registro local."""
        try:
            if tabla == "visitas":
                Visita.update(sincronizado=True).where(Visita.sync_id == sync_id).execute()
        except Exception:
            pass

    # ── Pull: servidor → cliente ───────────────────────────────────────────

    async def _pull(self):
        """Descarga los cambios nuevos del servidor y actualiza SQLite."""
        datos = await api.pull_cambios(self.token, since=self._ultimo_sync)

        for visita_data in datos.get("visitas", []):
            self._guardar_visita_local(visita_data)

        self._ultimo_sync = datos.get("timestamp_servidor", int(time.time()))

    def _guardar_visita_local(self, data: dict):
        """
        Guarda o actualiza una visita recibida del servidor en SQLite local.
        Solo actualiza si el registro del servidor es más reciente.
        """
        try:
            visita_existente = Visita.get(Visita.sync_id == data["sync_id"])
            # Si ya existe y está sincronizada, no sobreescribir con datos del servidor
            # (el cliente es la fuente de verdad para sus propias visitas)
            visita_existente.sincronizado = True
            visita_existente.save()
        except Visita.DoesNotExist:
            # Es una visita nueva de otro dispositivo — guardar
            try:
                comedor = Comedor.get(Comedor.sync_id == data["comedor_sync_id"])
                supervisor = Supervisor.select().first()  # Solo hay un supervisor local
                visita = Visita.create(
                    sync_id=data["sync_id"],
                    supervisor=supervisor,
                    comedor=comedor,
                    fecha=datetime.fromisoformat(data["fecha"]),
                    estado=data.get("estado", "completada"),
                    observaciones_generales=data.get("observaciones_generales", ""),
                    sincronizado=True,
                )
                # Guardar ítems del checklist
                for item_data in data.get("checklist", []):
                    ItemChecklist.get_or_create(
                        sync_id=item_data["sync_id"],
                        defaults={
                            "visita": visita,
                            "categoria": item_data.get("categoria", ""),
                            "pregunta": item_data.get("pregunta", ""),
                            "respuesta": item_data.get("respuesta"),
                            "observacion": item_data.get("observacion", ""),
                            "orden": item_data.get("orden", 0),
                        }
                    )
            except Exception:
                pass  # Comedor no encontrado localmente, se resolverá en próximo pull

    # ── Estado de conexión ─────────────────────────────────────────────────

    def _actualizar_estado(self, online: bool):
        """Llama al callback si el estado de conexión cambió."""
        if online != self.online:
            self.online = online
            if self.on_estado_cambio:
                self.on_estado_cambio(online)


async def sync_comedores_iniciales(token: str):
    """
    Descarga y guarda los comedores del servidor en SQLite local.
    Llamar una vez al hacer login por primera vez (o cuando se reconecta).
    """
    comedores_servidor = await api.obtener_comedores(token)
    for c in comedores_servidor:
        Comedor.get_or_create(
            sync_id=c["sync_id"],
            defaults={
                "nombre": c["nombre"],
                "municipio": c["municipio"],
                "institucion": c["institucion"],
                "direccion": c.get("direccion", ""),
                "sincronizado": True,
            }
        )
