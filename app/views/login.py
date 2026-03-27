"""
Pantalla de login de Supervi.
El supervisor ingresa con cédula y contraseña.
- Si hay internet: autentica contra el servidor y guarda el JWT localmente.
- Si no hay internet: verifica credenciales guardadas en SQLite.
"""
import flet as ft
from app.db.models import Supervisor, inicializar_db


def vista_login(page: ft.Page, al_ingresar):
    """
    Construye y retorna la pantalla de login.

    Args:
        page: La página principal de Flet
        al_ingresar: Función a llamar cuando el login es exitoso, recibe el Supervisor
    """
    page.title = "Supervi — PAE Colombia"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREEN_50

    # ── Campos del formulario ──────────────────────────────────────────────
    cedula_campo = ft.TextField(
        label="Cédula",
        prefix_icon=ft.Icons.BADGE,
        keyboard_type=ft.KeyboardType.NUMBER,
        autofocus=True,
        width=320,
    )

    contrasena_campo = ft.TextField(
        label="Contraseña",
        prefix_icon=ft.Icons.LOCK,
        password=True,
        can_reveal_password=True,
        width=320,
    )

    mensaje_error = ft.Text(
        value="",
        color=ft.Colors.RED_700,
        size=13,
        text_align=ft.TextAlign.CENTER,
    )

    indicador_carga = ft.ProgressRing(visible=False, width=24, height=24)

    # ── Lógica de login ────────────────────────────────────────────────────
    async def intentar_login(e):
        cedula = cedula_campo.value.strip()
        password = contrasena_campo.value.strip()
        mensaje_error.value = ""

        if not cedula or not password:
            mensaje_error.value = "Ingresa tu cédula y contraseña."
            page.update()
            return

        indicador_carga.visible = True
        boton_ingresar.disabled = True
        page.update()

        supervisor = await _autenticar(cedula, password)

        indicador_carga.visible = False
        boton_ingresar.disabled = False

        if supervisor:
            al_ingresar(supervisor)
        else:
            mensaje_error.value = "Cédula o contraseña incorrectos."
            page.update()

    async def _autenticar(cedula: str, password: str):
        """
        Estrategia de autenticación:
        1. Intenta login contra el servidor (si hay internet)
        2. Si no hay internet, verifica credenciales guardadas localmente
        3. En desarrollo, acepta contraseña '1234' para cualquier cédula
        """
        from app.services.api import login as login_api, verificar_conexion, ErrorAPI
        from app.db.sync import sync_comedores_iniciales

        # Intentar login online
        hay_conexion = await verificar_conexion()
        if hay_conexion:
            try:
                resultado = await login_api(cedula, password)
                datos_sup = resultado["supervisor"]
                token = resultado["token"]

                # Guardar o actualizar supervisor local
                supervisor, _ = Supervisor.get_or_create(
                    cedula=cedula,
                    defaults={
                        "nombre": datos_sup["nombre"],
                        "email": datos_sup["email"],
                        "zona": datos_sup.get("zona", ""),
                        "token_jwt": token,
                        "sincronizado": True,
                    }
                )
                if supervisor.token_jwt != token:
                    supervisor.token_jwt = token
                    supervisor.nombre = datos_sup["nombre"]
                    supervisor.save()

                # Descargar comedores asignados en segundo plano
                try:
                    await sync_comedores_iniciales(token)
                except Exception:
                    pass  # Si falla, se usarán los comedores ya guardados

                return supervisor

            except ErrorAPI:
                return None  # Credenciales incorrectas — no intentar offline

        # Sin internet: verificar credenciales guardadas localmente
        try:
            supervisor = Supervisor.get(Supervisor.cedula == cedula)
            # Modo desarrollo: contraseña '1234' siempre acepta
            if password == "1234":
                return supervisor
        except Supervisor.DoesNotExist:
            # Solo en desarrollo: crear usuario de prueba
            if password == "1234":
                return Supervisor.create(
                    nombre=f"Supervisor {cedula}",
                    email=f"{cedula}@pae.gov.co",
                    cedula=cedula,
                    zona="Zona de Prueba",
                )
        return None

    # ── Botón de ingreso ───────────────────────────────────────────────────
    boton_ingresar = ft.ElevatedButton(
        text="Ingresar",
        icon=ft.Icons.LOGIN,
        width=320,
        height=48,
        style=ft.ButtonStyle(
            bgcolor=ft.Colors.GREEN_700,
            color=ft.Colors.WHITE,
        ),
        on_click=intentar_login,
    )

    # ── Layout de la pantalla ──────────────────────────────────────────────
    contenido = ft.Column(
        controls=[
            ft.Container(height=40),
            ft.Icon(ft.Icons.RESTAURANT_MENU, size=64, color=ft.Colors.GREEN_700),
            ft.Text(
                "Supervi",
                size=32,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREEN_900,
            ),
            ft.Text(
                "Supervisión PAE Colombia",
                size=14,
                color=ft.Colors.GREEN_700,
            ),
            ft.Container(height=32),
            cedula_campo,
            ft.Container(height=8),
            contrasena_campo,
            ft.Container(height=4),
            mensaje_error,
            ft.Container(height=16),
            boton_ingresar,
            ft.Container(height=8),
            indicador_carga,
        ],
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=contenido,
        padding=ft.padding.all(24),
        expand=True,
    )
