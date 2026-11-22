"""Rutas de la aplicación consultas médicas."""

from django.urls import path
from consultas.views import (
    agenda_view,
    agendar_cita_view,
    cancelar_cita_view,
    historial_clinico_view,
    login_view,
    logout_view,
    registrar_consulta_view,
    registrar_paciente_view,
    reportes_view,
)

urlpatterns = [
    path("", agenda_view, name="agenda"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("citas/agendar/", agendar_cita_view, name="agendar_cita"),
    path("citas/<int:cita_id>/cancelar/", cancelar_cita_view, name="cancelar_cita"),
    path("citas/<int:cita_id>/consulta/", registrar_consulta_view, name="registrar_consulta"),
    path("pacientes/nuevo/", registrar_paciente_view, name="registrar_paciente"),
    path("historial/<int:paciente_id>/", historial_clinico_view, name="historial_clinico"),
    path("reportes/", reportes_view, name="reportes"),
]
