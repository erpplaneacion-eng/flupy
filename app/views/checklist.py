"""
Pantalla del checklist de calidad e inocuidad del PAE.
Agrupa las preguntas por categoría y permite responder SI/NO/NA
con observaciones opcionales por ítem.
"""
import flet as ft
from app.db.models import Visita, ItemChecklist, agregar_a_cola_sync

# ── Preguntas del checklist por categoría ─────────────────────────────────
CHECKLIST_PAE = {
    "instalaciones": {
        "titulo": "Instalaciones",
        "icono": ft.Icons.HOME,
        "preguntas": [
            "Las instalaciones de la cocina se encuentran limpias y en buen estado",
            "Paredes, pisos y techos limpios, sin humedad ni plagas",
            "Hay buena ventilación e iluminación en la cocina",
            "Los residuos sólidos están correctamente almacenados y separados",
            "El área de preparación está separada del área de consumo",
        ],
    },
    "manipuladores": {
        "titulo": "Manipuladores de Alimentos",
        "icono": ft.Icons.PERSON,
        "preguntas": [
            "Los manipuladores usan uniforme completo (delantal, cofia, tapabocas)",
            "Los manipuladores tienen las manos limpias y uñas cortas",
            "No se evidencian joyas, maquillaje o accesorios durante la preparación",
            "Los manipuladores cuentan con carné de manipulación de alimentos vigente",
            "Se observa correcto lavado de manos durante la preparación",
        ],
    },
    "alimentos": {
        "titulo": "Almacenamiento de Alimentos",
        "icono": ft.Icons.INVENTORY,
        "preguntas": [
            "Los alimentos están almacenados de forma adecuada (temperatura, envases)",
            "No se encuentran alimentos vencidos o en mal estado",
            "Los alimentos están identificados con fecha de ingreso y vencimiento",
            "Los alimentos crudos y cocidos están correctamente separados",
            "El cuarto frío o nevera mantiene la temperatura adecuada",
        ],
    },
    "utensilios": {
        "titulo": "Utensilios y Equipos",
        "icono": ft.Icons.KITCHEN,
        "preguntas": [
            "Los utensilios de cocina están limpios y desinfectados",
            "Tablas de corte en buen estado y diferenciadas por color según uso",
            "Los equipos (estufa, hornos, licuadoras) están limpios y funcionando",
            "Hay suficientes utensilios para el servido de los estudiantes",
            "Los contenedores de alimentos tienen tapa y están en buen estado",
        ],
    },
    "proceso": {
        "titulo": "Proceso de Preparación",
        "icono": ft.Icons.LOCAL_FIRE_DEPARTMENT,
        "preguntas": [
            "Los alimentos se preparan con la anticipación adecuada (no más de 2h)",
            "La cocción de alimentos alcanza la temperatura correcta",
            "El servido se realiza con utensilios limpios (no con las manos)",
            "Las porciones servidas corresponden a las minutas establecidas",
            "Se llevan registros de temperatura y control del proceso",
        ],
    },
}


def vista_checklist(page: ft.Page, visita: Visita, al_finalizar, al_volver):
    """
    Construye el checklist de calidad e inocuidad para una visita.

    Args:
        page: La página principal de Flet
        visita: La visita activa (ya guardada en SQLite)
        al_finalizar: Función llamada al completar y guardar el checklist
        al_volver: Función llamada al cancelar
    """

    # ── Pre-crear ítems en SQLite para esta visita ─────────────────────────
    # (se guardan como null hasta que el supervisor responda)
    items_db = {}  # categoria_orden → ItemChecklist

    orden = 0
    for categoria, datos in CHECKLIST_PAE.items():
        for pregunta in datos["preguntas"]:
            item = ItemChecklist.create(
                visita=visita,
                categoria=categoria,
                pregunta=pregunta,
                respuesta=None,
                observacion="",
                orden=orden,
            )
            items_db[f"{categoria}_{orden}"] = item
            orden += 1

    # ── Controles de respuesta por ítem ───────────────────────────────────
    def fila_item(item: ItemChecklist, categoria: str, idx_orden: int):
        """Crea la fila de un ítem del checklist con botones SI/NO/NA."""

        estado_respuesta = {"valor": item.respuesta}

        btn_si = ft.ElevatedButton(
            text="SI",
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200, color=ft.Colors.BLACK87),
            height=34,
        )
        btn_no = ft.ElevatedButton(
            text="NO",
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200, color=ft.Colors.BLACK87),
            height=34,
        )
        btn_na = ft.ElevatedButton(
            text="N/A",
            style=ft.ButtonStyle(bgcolor=ft.Colors.GREY_200, color=ft.Colors.BLACK87),
            height=34,
        )

        obs_campo = ft.TextField(
            hint_text="Observación (opcional)",
            dense=True,
            border_color=ft.Colors.GREY_300,
            visible=False,
        )

        def actualizar_botones(seleccionado: str):
            """Resalta el botón seleccionado y guarda en SQLite."""
            estado_respuesta["valor"] = seleccionado

            # Colores de cada botón según selección
            btn_si.style = ft.ButtonStyle(
                bgcolor=ft.Colors.GREEN_600 if seleccionado == "SI" else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if seleccionado == "SI" else ft.Colors.BLACK87,
            )
            btn_no.style = ft.ButtonStyle(
                bgcolor=ft.Colors.RED_600 if seleccionado == "NO" else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if seleccionado == "NO" else ft.Colors.BLACK87,
            )
            btn_na.style = ft.ButtonStyle(
                bgcolor=ft.Colors.GREY_500 if seleccionado == "NA" else ft.Colors.GREY_200,
                color=ft.Colors.WHITE if seleccionado == "NA" else ft.Colors.BLACK87,
            )

            # Mostrar campo de observación si responde NO
            obs_campo.visible = seleccionado == "NO"

            # Guardar inmediatamente en SQLite
            item.respuesta = seleccionado
            item.save()

            page.update()

        btn_si.on_click = lambda e: actualizar_botones("SI")
        btn_no.on_click = lambda e: actualizar_botones("NO")
        btn_na.on_click = lambda e: actualizar_botones("NA")

        def guardar_observacion(e):
            item.observacion = obs_campo.value
            item.save()

        obs_campo.on_blur = guardar_observacion

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(item.pregunta, size=13, color=ft.Colors.GREY_800),
                    ft.Row(
                        controls=[btn_si, btn_no, btn_na],
                        spacing=8,
                    ),
                    obs_campo,
                    ft.Divider(height=1, color=ft.Colors.GREY_200),
                ],
                spacing=6,
            ),
            padding=ft.padding.symmetric(vertical=8),
        )

    # ── Sección por categoría ──────────────────────────────────────────────
    def seccion_categoria(categoria: str, datos: dict, items_de_categoria: list):
        return ft.ExpansionTile(
            title=ft.Text(datos["titulo"], weight=ft.FontWeight.W_600),
            leading=ft.Icon(datos["icono"], color=ft.Colors.GREEN_700),
            bgcolor=ft.Colors.WHITE,
            collapsed_bgcolor=ft.Colors.GREEN_50,
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=items_de_categoria,
                        spacing=0,
                    ),
                    padding=ft.padding.symmetric(horizontal=16),
                )
            ],
        )

    # ── Construir controles de todas las categorías ────────────────────────
    secciones = []
    orden_actual = 0
    for categoria, datos in CHECKLIST_PAE.items():
        items_fila = []
        for _ in datos["preguntas"]:
            key = f"{categoria}_{orden_actual}"
            item = items_db[key]
            items_fila.append(fila_item(item, categoria, orden_actual))
            orden_actual += 1
        secciones.append(seccion_categoria(categoria, datos, items_fila))

    # ── Finalizar visita ───────────────────────────────────────────────────
    def finalizar_visita(e):
        """Marca la visita como completada y agrega items a la cola de sync."""
        visita.estado = "completada"
        visita.save()

        # Agregar todos los ítems a la cola de sync
        for item in ItemChecklist.select().where(ItemChecklist.visita == visita):
            agregar_a_cola_sync(
                tabla="checklist_items",
                operacion="INSERT",
                record_sync_id=item.sync_id,
                datos={
                    "sync_id": item.sync_id,
                    "visita_sync_id": visita.sync_id,
                    "categoria": item.categoria,
                    "pregunta": item.pregunta,
                    "respuesta": item.respuesta,
                    "observacion": item.observacion,
                    "orden": item.orden,
                }
            )

        al_finalizar()

    # ── AppBar ─────────────────────────────────────────────────────────────
    page.appbar = ft.AppBar(
        leading=ft.IconButton(
            icon=ft.Icons.ARROW_BACK,
            icon_color=ft.Colors.WHITE,
            on_click=lambda e: al_volver(),
        ),
        title=ft.Text("Checklist Calidad e Inocuidad", color=ft.Colors.WHITE),
        bgcolor=ft.Colors.GREEN_700,
    )

    # ── Layout ─────────────────────────────────────────────────────────────
    contenido = ft.Column(
        controls=[
            ft.Text(
                f"Comedor: {visita.comedor.nombre}",
                size=13,
                color=ft.Colors.GREY_700,
            ),
            ft.Text(
                "Responde SI, NO o N/A para cada ítem.",
                size=12,
                color=ft.Colors.GREY_500,
            ),
            ft.Container(height=8),
            *secciones,
            ft.Container(height=16),
            ft.ElevatedButton(
                text="Finalizar y Guardar Visita",
                icon=ft.Icons.SAVE,
                expand=True,
                height=48,
                style=ft.ButtonStyle(
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                ),
                on_click=finalizar_visita,
            ),
            ft.Container(height=16),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.Container(
        content=contenido,
        padding=ft.padding.all(16),
        expand=True,
    )
