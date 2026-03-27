"""
Supervi — App de Supervisión PAE Colombia
Punto de entrada principal de la aplicación Flet.

Maneja la navegación entre pantallas:
  Login → Home → Nueva Visita → Checklist → Historial
"""
import flet as ft
from app.db.models import inicializar_db, Supervisor
from app.views.login import vista_login
from app.views.home import vista_home


def main(page: ft.Page):
    # ── Configuración global de la página ─────────────────────────────────
    page.title = "Supervi"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.bgcolor = ft.Colors.GREEN_50

    # Tamaño de ventana para simular celular en desarrollo
    page.window.width = 390
    page.window.height = 844

    # ── Inicializar base de datos local ───────────────────────────────────
    inicializar_db()

    # ── Estado global de la app ───────────────────────────────────────────
    supervisor_activo: list[Supervisor] = []  # lista de 1 elemento para mutabilidad

    # ── Funciones de navegación ───────────────────────────────────────────

    def ir_a_login():
        """Muestra la pantalla de login."""
        page.appbar = None
        page.controls.clear()
        page.add(vista_login(page, al_ingresar=ir_a_home))
        page.update()

    def ir_a_home(supervisor: Supervisor):
        """Muestra la pantalla principal con comedores del supervisor."""
        supervisor_activo.clear()
        supervisor_activo.append(supervisor)

        page.controls.clear()
        page.add(
            vista_home(
                page,
                supervisor=supervisor,
                al_nueva_visita=ir_a_nueva_visita,
                al_historial=ir_a_historial,
                al_cerrar_sesion=ir_a_login,
            )
        )
        page.update()

    def ir_a_nueva_visita(comedor):
        """Navega al formulario de nueva visita (FASE 2)."""
        # Importación diferida para evitar imports circulares
        from app.views.nueva_visita import vista_nueva_visita
        page.controls.clear()
        page.add(
            vista_nueva_visita(
                page,
                supervisor=supervisor_activo[0],
                comedor=comedor,
                al_volver=lambda: ir_a_home(supervisor_activo[0]),
            )
        )
        page.update()

    def ir_a_historial():
        """Navega al historial de visitas (FASE 2)."""
        from app.views.historial import vista_historial
        page.controls.clear()
        page.add(
            vista_historial(
                page,
                supervisor=supervisor_activo[0],
                al_volver=lambda: ir_a_home(supervisor_activo[0]),
            )
        )
        page.update()

    # ── Inicio ────────────────────────────────────────────────────────────
    ir_a_login()


if __name__ == "__main__":
    ft.app(target=main)
