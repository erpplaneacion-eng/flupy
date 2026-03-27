"""
Pantalla para iniciar y registrar una nueva visita de supervisión.
El supervisor elige la fecha y agrega observaciones generales,
luego pasa al checklist de calidad e inocuidad.
"""
import flet as ft
from datetime import datetime
from app.db.models import Supervisor, Comedor, Visita, agregar_a_cola_sync


def vista_nueva_visita(page: ft.Page, supervisor: Supervisor, comedor: Comedor, al_volver):
    """
    Construye el formulario de nueva visita.

    Args:
        page: La página principal de Flet
        supervisor: Supervisor autenticado
        comedor: Comedor que se va a visitar
        al_volver: Función llamada al regresar al home
    """

    # ── Campos del formulario ──────────────────────────────────────────────
    fecha_texto = ft.Text(
        value=datetime.now().strftime("%d/%m/%Y %H:%M"),
        size=14,
        color=ft.Colors.GREY_700,
    )

    observaciones_campo = ft.TextField(
        label="Observaciones generales",
        hint_text="Condiciones generales encontradas al llegar al comedor...",
        multiline=True,
        min_lines=4,
        max_lines=8,
        width=None,
        expand=True,
    )

    mensaje = ft.Text(value="", color=ft.Colors.RED_700, size=13)

    # ── Lógica de guardado ─────────────────────────────────────────────────
    def guardar_y_continuar(e):
        """Crea la visita en SQLite y navega al checklist."""
        visita = Visita.create(
            supervisor=supervisor,
            comedor=comedor,
            fecha=datetime.now(),
            estado="borrador",
            observaciones_generales=observaciones_campo.value.strip(),
        )

        # Registrar en cola de sync para enviar al servidor cuando haya conexión
        agregar_a_cola_sync(
            tabla="visitas",
            operacion="INSERT",
            record_sync_id=visita.sync_id,
            datos={
                "sync_id": visita.sync_id,
                "supervisor_sync_id": supervisor.sync_id,
                "comedor_sync_id": comedor.sync_id,
                "fecha": str(visita.fecha),
                "estado": visita.estado,
                "observaciones_generales": visita.observaciones_generales,
            }
        )

        # Ir al checklist de calidad e inocuidad
        from app.views.checklist import vista_checklist
        page.controls.clear()
        page.add(
            vista_checklist(
                page,
                visita=visita,
                al_finalizar=al_volver,
                al_volver=al_volver,
            )
        )
        page.update()

    # ── AppBar ─────────────────────────────────────────────────────────────
    page.appbar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.WHITE,
            on_click=lambda e: al_volver(),
        ),
        title=ft.Text("Nueva Visita", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
    )

    # ── Layout ─────────────────────────────────────────────────────────────
    contenido = ft.Column(
        controls=[
            # Info del comedor
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    ft.Icon(ft.Icons.RESTAURANT, color=ft.Colors.GREEN_700),
                                    ft.Text(
                                        comedor.nombre,
                                        weight=ft.FontWeight.BOLD,
                                        size=16,
                                        color=ft.Colors.GREEN_900,
                                    ),
                                ]
                            ),
                            ft.Text(
                                comedor.municipio,
                                size=13,
                                color=ft.Colors.GREY_600,
                            ),
                            ft.Text(
                                comedor.institucion,
                                size=13,
                                color=ft.Colors.GREY_600,
                            ),
                        ],
                        spacing=4,
                    ),
                    padding=ft.padding.all(16),
                ),
                elevation=2,
            ),

            ft.Container(height=8),

            # Fecha y hora
            ft.Row(
                controls=[
                    ft.Icon(ft.Icons.CALENDAR_TODAY, color=ft.Colors.GREEN_700, size=18),
                    ft.Text("Fecha y hora:", weight=ft.FontWeight.W_500),
                    fecha_texto,
                ],
                spacing=8,
            ),

            ft.Container(height=12),

            # Observaciones
            ft.Text("Observaciones generales", weight=ft.FontWeight.W_500),
            observaciones_campo,

            ft.Container(height=8),
            mensaje,

            ft.Container(height=16),

            # Botón continuar al checklist
            ft.ElevatedButton(
                text="Continuar al Checklist",
                icon=ft.Icons.CHECKLIST,
                width=None,
                expand=True,
                height=48,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                ),
                on_click=guardar_y_continuar,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.Container(
        content=contenido,
        padding=ft.padding.all(16),
        expand=True,
    )
