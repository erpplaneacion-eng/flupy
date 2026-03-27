"""
Endpoints de autenticación.
POST /auth/login → devuelve JWT token
POST /auth/registro → crea un nuevo supervisor (solo admin)
"""
import os
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from passlib.context import CryptContext
from jose import jwt
from pydantic import BaseModel

from backend.database import get_db
from backend.models import Supervisor

router = APIRouter(prefix="/auth", tags=["autenticación"])

# Configuración JWT
SECRET_KEY = os.getenv("SECRET_KEY", "supervi-clave-secreta-cambiar-en-produccion")
ALGORITHM = "HS256"
TOKEN_EXPIRA_HORAS = 24 * 7  # 7 días (supervisores en campo no pueden re-loguearse fácil)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Schemas Pydantic ───────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    cedula: str
    password: str


class LoginResponse(BaseModel):
    token: str
    supervisor: dict


class RegistroRequest(BaseModel):
    nombre: str
    email: str
    cedula: str
    zona: str
    password: str
    admin_key: str  # Clave para proteger el registro


# ── Utilidades ─────────────────────────────────────────────────────────────

def crear_token(supervisor: Supervisor) -> str:
    """Genera un JWT con los datos del supervisor."""
    datos = {
        "sub": supervisor.sync_id,
        "cedula": supervisor.cedula,
        "nombre": supervisor.nombre,
        "exp": datetime.utcnow() + timedelta(hours=TOKEN_EXPIRA_HORAS),
    }
    return jwt.encode(datos, SECRET_KEY, algorithm=ALGORITHM)


def verificar_password(plano: str, hash_: str) -> bool:
    return pwd_context.verify(plano, hash_)


def hashear_password(plano: str) -> str:
    return pwd_context.hash(plano)


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Autentica al supervisor con cédula y contraseña. Devuelve JWT."""
    resultado = await db.execute(
        select(Supervisor).where(Supervisor.cedula == body.cedula)
    )
    supervisor = resultado.scalar_one_or_none()

    if not supervisor or not verificar_password(body.password, supervisor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Cédula o contraseña incorrectos",
        )

    if not supervisor.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Supervisor desactivado. Contacta al administrador.",
        )

    token = crear_token(supervisor)

    return LoginResponse(
        token=token,
        supervisor={
            "sync_id": supervisor.sync_id,
            "nombre": supervisor.nombre,
            "email": supervisor.email,
            "cedula": supervisor.cedula,
            "zona": supervisor.zona,
        }
    )


@router.post("/registro", status_code=status.HTTP_201_CREATED)
async def registrar_supervisor(body: RegistroRequest, db: AsyncSession = Depends(get_db)):
    """
    Registra un nuevo supervisor. Requiere admin_key para evitar registros no autorizados.
    El admin_key se configura en la variable de entorno ADMIN_KEY.
    """
    admin_key_correcta = os.getenv("ADMIN_KEY", "supervi-admin-2024")
    if body.admin_key != admin_key_correcta:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de administrador incorrecta",
        )

    # Verificar que no exista ya el supervisor
    existente = await db.execute(
        select(Supervisor).where(
            (Supervisor.cedula == body.cedula) | (Supervisor.email == body.email)
        )
    )
    if existente.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe un supervisor con esa cédula o email",
        )

    supervisor = Supervisor(
        nombre=body.nombre,
        email=body.email,
        cedula=body.cedula,
        zona=body.zona,
        password_hash=hashear_password(body.password),
    )
    db.add(supervisor)
    await db.commit()
    await db.refresh(supervisor)

    return {"mensaje": f"Supervisor {supervisor.nombre} creado exitosamente", "sync_id": supervisor.sync_id}
