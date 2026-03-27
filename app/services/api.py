"""
Cliente HTTP async para comunicarse con el backend FastAPI.
Usa aiohttp (async) para no bloquear la UI de Flet.

Todas las funciones son async — deben llamarse con await.
"""
import os
import json
import aiohttp

# URL del backend — se cambia a la URL de Railway en producción
# Puede sobreescribirse con la variable de entorno SUPERVI_API_URL
API_URL = os.getenv("SUPERVI_API_URL", "http://localhost:8000")

# Tiempo máximo de espera por request (en segundos)
TIMEOUT = aiohttp.ClientTimeout(total=15)


class ErrorAPI(Exception):
    """Error al comunicarse con el servidor."""
    pass


async def login(cedula: str, password: str) -> dict:
    """
    Autentica al supervisor contra el servidor.
    Devuelve {"token": "...", "supervisor": {...}}
    Lanza ErrorAPI si las credenciales son incorrectas o no hay conexión.
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(
            f"{API_URL}/auth/login",
            json={"cedula": cedula, "password": password},
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            elif resp.status == 401:
                raise ErrorAPI("Cédula o contraseña incorrectos")
            else:
                texto = await resp.text()
                raise ErrorAPI(f"Error del servidor: {resp.status} — {texto}")


async def obtener_comedores(token: str) -> list[dict]:
    """
    Descarga la lista de comedores asignados desde el servidor.
    Devuelve lista de dicts con los datos del comedor.
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.get(
            f"{API_URL}/sync/comedores",
            headers={"Authorization": f"Bearer {token}"},
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise ErrorAPI(f"Error al obtener comedores: {resp.status}")


async def push_cambios(token: str, operaciones: list[dict]) -> dict:
    """
    Envía las operaciones pendientes de la cola de sync al servidor.
    Devuelve {"procesadas": N, "errores": [...]}
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.post(
            f"{API_URL}/sync/push",
            headers={"Authorization": f"Bearer {token}"},
            json={"operaciones": operaciones},
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise ErrorAPI(f"Error en push: {resp.status}")


async def pull_cambios(token: str, since: int = 0) -> dict:
    """
    Descarga los cambios nuevos del servidor desde el timestamp dado.
    since=0 descarga todo (primera sincronización).
    Devuelve {"timestamp_servidor": N, "visitas": [...]}
    """
    async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
        async with session.get(
            f"{API_URL}/sync/pull",
            headers={"Authorization": f"Bearer {token}"},
            params={"since": since},
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                raise ErrorAPI(f"Error en pull: {resp.status}")


async def verificar_conexion() -> bool:
    """
    Verifica si hay conexión con el servidor.
    Devuelve True si el servidor responde, False si no.
    """
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3)) as session:
            async with session.get(f"{API_URL}/health") as resp:
                return resp.status == 200
    except Exception:
        return False
