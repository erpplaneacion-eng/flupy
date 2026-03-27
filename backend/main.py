"""
Supervi Backend — FastAPI
Servidor de sincronización para la app de supervisión PAE Colombia.

Endpoints disponibles (ver /docs cuando el servidor esté corriendo):
  POST /auth/login         → autenticación
  POST /auth/registro      → crear supervisor (requiere admin_key)
  GET  /sync/comedores     → lista de comedores
  POST /sync/push          → enviar cambios del cliente
  GET  /sync/pull          → recibir cambios nuevos del servidor
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import crear_tablas
from backend.routers import auth, sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas en PostgreSQL al arrancar el servidor."""
    await crear_tablas()
    yield


app = FastAPI(
    title="Supervi API",
    description="Backend de sincronización para la app de supervisión PAE Colombia",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: permite que la app Flet (en cualquier origen) se conecte al backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sync.router)


@app.get("/")
async def raiz():
    return {"estado": "OK", "app": "Supervi API", "version": "1.0.0"}


@app.get("/health")
async def health():
    """Railway usa este endpoint para verificar que el servidor está vivo."""
    return {"status": "healthy"}
