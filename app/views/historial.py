"""
Pantalla de historial de visitas del supervisor.
Muestra todas las visitas realizadas con su estado de sincronización.
"""
import flet as ft
from app.db.models import Supervisor, Visita, ItemChecklist


def vista_historial(page: ft.Page, supervisor: Supervisor, al_volver):
    """
    Construye la pantalla de historial de visitas.

    Args:
        page: La página principal de Flet
        supervisor: Supervisor autenticado
        al_volver: Función llamada al regresar al home
    """

    def chip_estado_sync(sincronizado: bool):
        if sincronizado:
            return ft.Chip(
                label=ft.Text("Sincronizado", size=10, color=ft.Colors.GREEN_800),
                bgcolor=ft.Colors.GREEN_100,
                disabled=True,
            )
        return ft.Chip(
            label=ft.Text("Pendiente sync", size=10, color=ft.Colors.ORANGE_800),
            bgcolor=ft.Colors.ORANGE_100,
            disabled=True,
        )

    def chip_estado_visita(estado: str):
        if estado == "completada":
            return ft.Chip(
                label=ft.Text("Completada", size=10, color=ft.Colors.BLUE_800),
                bgcolor=ft.Colors.BLUE_100,
                disabled=True,
            )
        return ft.Chip(
            label=ft.Text("Borrador", size=10, color=ft.Colors.GREY_700),
            bgcolor=ft.Colors.GREY_200,
            disabled=True,
        )

    def tarjeta_visita(visita: Visita):
        total_items = ItemChecklist.select().where(ItemChecklist.visita == visita).count()
        no_conformidades = ItemChecklist.select().where(
            ItemChecklist.visita == visita,
            ItemChecklist.respuesta == "NO"
        ).count()

        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Text(
                                    visita.comedor.nombre,
                                    weight=ft.FontWeight.W_600,
                                    size=14,
                                    expand=True,
                                ),
                                chip_estado_visita(visita.estado),
                            ]
                        ),
                        ft.Text(
                            visita.fecha.strftime("%d/%m/%Y %H:%M"),
                            size=12,
                            color=ft.Colors.GREY_600,
                        ),
                        ft.Row(
                            controls=[
                                ft.Text(
                                    f"{total_items} ítems · {no_conformidades} no conformidades",
                                    size=12,
                                    color=ft.Colors.RED_700 if no_conformidades > 0 else ft.Colors.GREY_500,
                                ),
                                chip_estado_sync(visita.sincronizado),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                    ],
                    spacing=6,
                ),
                padding=ft.padding.all(16),
            ),
            elevation=2,
        )

    # ── Cargar visitas ─────────────────────────────────────────────────────
    visitas = list(
        Visita.select()
        .where(Visita.supervisor == supervisor)
        .order_by(Visita.fecha.desc())
    )

    if visitas:
        contenido_lista = ft.Column(
            controls=[tarjeta_visita(v) for v in visitas],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )
    else:
        contenido_lista = ft.Column(
            controls=[
                ft.Container(height=60),
                ft.Icon(ft.Icons.HISTORY, size=64, color=ft.Colors.GREY_300),
                ft.Text(
                    "No hay visitas registradas aún.",
                    color=ft.Colors.GREY_400,
                    text_align=ft.TextAlign.CENTER,
                ),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    # ── AppBar ─────────────────────────────────────────────────────────────
    page.appbar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.WHITE,
            on_click=lambda e: al_volver(),
        ),
        title=ft.Text("Historial de Visitas", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
    )

    # ── Layout ─────────────────────────────────────────────────────────────
    contenido = ft.Column(
        controls=[
            ft.Text(
                f"{len(visitas)} visita(s) registrada(s)",
                size=13,
                color=ft.Colors.GREY_600,
            ),
            ft.Container(height=8),
            contenido_lista,
        ],
        expand=True,
    )

    return ft.Container(
        content=contenido,
        padding=ft.padding.all(16),
        expand=True,
    )
