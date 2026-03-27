"""
Pantalla principal de Supervi.
Muestra la lista de comedores asignados al supervisor
y permite iniciar una nueva visita.
"""
import asyncio
import flet as ft
from app.db.models import Supervisor, Comedor, Visita, inicializar_db


def _crear_datos_prueba():
    """Inserta comedores de prueba si la tabla está vacía."""
    if Comedor.select().count() == 0:
        comedores_prueba = [
            {"nombre": "Comedor IE Simón Bolívar", "municipio": "Bogotá",
             "institucion": "IE Simón Bolívar", "direccion": "Cra 15 #45-20"},
            {"nombre": "Comedor IE La Merced", "municipio": "Soacha",
             "institucion": "IE La Merced", "direccion": "Cl 8 #12-10"},
            {"nombre": "Comedor IE San José", "municipio": "Facatativá",
             "institucion": "IE San José", "direccion": "Av Principal #3-40"},
        ]
        for c in comedores_prueba:
            Comedor.create(**c)


def vista_home(page: ft.Page, supervisor: Supervisor, al_nueva_visita, al_historial, al_cerrar_sesion):
    """
    Construye y retorna la pantalla principal.

    Args:
        page: La página principal de Flet
        supervisor: El supervisor autenticado
        al_nueva_visita: Función llamada con (comedor) al iniciar visita
        al_historial: Función llamada al ver el historial de visitas
        al_cerrar_sesion: Función llamada al cerrar sesión
    """
    _crear_datos_prueba()

    # ── Motor de sincronización ────────────────────────────────────────────
    from app.db.sync import MotorSync

    def al_cambiar_conexion(online: bool):
        """Actualiza el chip de estado cuando cambia la conexión."""
        if online:
            chip_conexion.label = ft.Text("Online", size=11, color=ft.Colors.GREEN_800)
            chip_conexion.leading = ft.Icon(ft.Icons.WIFI, size=14, color=ft.Colors.GREEN_700)
            chip_conexion.bgcolor = ft.Colors.GREEN_100
        else:
            chip_conexion.label = ft.Text("Sin conexión", size=11, color=ft.Colors.ORANGE_800)
            chip_conexion.leading = ft.Icon(ft.Icons.WIFI_OFF, size=14, color=ft.Colors.ORANGE_700)
            chip_conexion.bgcolor = ft.Colors.ORANGE_50
        page.update()

    motor = MotorSync(
        token=supervisor.token_jwt,
        on_estado_cambio=al_cambiar_conexion,
    )

    # ── Estado de conexión ─────────────────────────────────────────────────
    chip_conexion = ft.Chip(
        label=ft.Text("Sin conexión", size=11, color=ft.Colors.ORANGE_800),
        leading=ft.Icon(ft.Icons.WIFI_OFF, size=14, color=ft.Colors.ORANGE_700),
        bgcolor=ft.Colors.ORANGE_50,
        disabled_color=ft.Colors.ORANGE_50,
        disabled=True,
    )

    async def al_montar(e):
        """Arranca el motor de sync cuando la pantalla se muestra."""
        await motor.iniciar()

    page.on_view_pop = lambda e: asyncio.create_task(motor.detener())

    # ── Tarjeta de cada comedor ────────────────────────────────────────────
    def tarjeta_comedor(comedor: Comedor):
        visitas_count = Visita.select().where(Visita.comedor == comedor).count()

        return ft.Card(
            content=ft.Container(
                content=ft.ListTile(
                    leading=ft.CircleAvatar(
                        content=ft.Icon(ft.Icons.RESTAURANT, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.GREEN_600,
                    ),
                    title=ft.Text(comedor.nombre, weight=ft.FontWeight.W_600),
                    subtitle=ft.Column(
                        controls=[
                            ft.Text(comedor.municipio, size=12, color=ft.Colors.GREY_600),
                            ft.Text(
                                f"{visitas_count} visita(s) registrada(s)",
                                size=11,
                                color=ft.Colors.GREEN_700,
                            ),
                        ],
                        spacing=2,
                    ),
                    trailing=ft.IconButton(
                        icon=ft.Icons.PLAY_CIRCLE,
                        icon_color=ft.Colors.GREEN_700,
                        tooltip="Iniciar visita",
                        on_click=lambda e, c=comedor: al_nueva_visita(c),
                    ),
                ),
                padding=ft.padding.symmetric(vertical=4),
            ),
            elevation=2,
        )

    # ── Lista de comedores ─────────────────────────────────────────────────
    comedores = list(Comedor.select().where(Comedor.activo == True))

    lista_comedores = ft.Column(
        controls=[tarjeta_comedor(c) for c in comedores],
        spacing=8,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    if not comedores:
        lista_comedores = ft.Column(
            controls=[
                ft.Container(height=40),
                ft.Icon(ft.Icons.INFO_OUTLINE, size=48, color=ft.Colors.GREY_400),
                ft.Text(
                    "No tienes comedores asignados.\nSincroniza cuando tengas conexión.",
                    text_align=ft.TextAlign.CENTER,
                    color=ft.Colors.GREY_500,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    # ── AppBar ─────────────────────────────────────────────────────────────
    page.appbar = ft.AppBar(
        leading=ft.Icon(ft.Icons.RESTAURANT_MENU, color=ft.Colors.WHITE),
        title=ft.Text("Supervi", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
        actions=[
            chip_conexion,
            ft.IconButton(
                icon=ft.Icons.SYNC,
                icon_color=ft.Colors.WHITE,
                tooltip="Sincronizar ahora",
                on_click=lambda e: asyncio.create_task(motor.sync_ahora()),
            ),
            ft.IconButton(
                icon=ft.Icons.HISTORY,
                icon_color=ft.Colors.WHITE,
                tooltip="Historial de visitas",
                on_click=lambda e: al_historial(),
            ),
            ft.IconButton(
                icon=ft.Icons.LOGOUT,
                icon_color=ft.Colors.WHITE,
                tooltip="Cerrar sesión",
                on_click=lambda e: al_cerrar_sesion(),
            ),
        ],
    )

    # ── Layout ─────────────────────────────────────────────────────────────
    contenido = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.PERSON, color=ft.Colors.GREEN_700),
                        ft.Text(
                            f"Hola, {supervisor.nombre}",
                            weight=ft.FontWeight.W_500,
                            color=ft.Colors.GREEN_900,
                        ),
                    ]
                ),
                padding=ft.padding.symmetric(horizontal=4, vertical=8),
            ),
            ft.Text(
                "Comedores asignados",
                size=16,
                weight=ft.FontWeight.BOLD,
                color=ft.Colors.GREEN_900,
            ),
            ft.Container(height=4),
            lista_comedores,
        ],
        expand=True,
    )

    contenedor = ft.Container(
        content=contenido,
        padding=ft.padding.all(16),
        expand=True,
    )
    # on_mount: arranca el motor de sync cuando el contenedor se muestra
    contenedor.on_click = None  # placeholder para que Flet registre el control
    page.run_task(motor.iniciar)
    return contenedor
