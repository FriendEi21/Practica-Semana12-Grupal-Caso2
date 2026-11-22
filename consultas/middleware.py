"""Middleware especializado para auditoría médica, horarios y alertas (RF4)."""

from datetime import datetime
from django.contrib import messages
from django.shortcuts import redirect
from .models import Cita, LogAuditoriaMedica
from .utils import es_horario_atencion_valido, obtener_ip_cliente, obtener_rol_medico


class AuditoriaYControlMedicoMiddleware:
    """Ejecuta las 3 capas del RF4: auditoría clínica, horario de citas y alertas."""

    def __init__(self, get_response):
        """Guarda el siguiente handler de la cadena de middleware."""
        self.get_response = get_response
    # Fin def __init__(self, get_response)

    def __call__(self, request):
        """Intercepta request/response validando horario, alertas y confidencialidad."""
        ip_cliente = ""
        usuario_actual = "anonimo"
        rol = ""
        pendientes = 0
        fecha_raw = ""
        hora_raw = ""
        fecha_obj = None
        hora_obj = None
        horario_ok = True
        mensaje_err = ""
        response = None
        accion_log = ""

        ip_cliente = obtener_ip_cliente(request)
        if hasattr(request, "user") and request.user.is_authenticated:
            usuario_actual = request.user.username
            rol = obtener_rol_medico(request.user)

            # 1. Middleware de alertas: notificar al médico citas pendientes al iniciar sesión
            if rol == "Médicos" and not request.session.get("alerta_citas_mostrada", False):
                if hasattr(request.user, "perfil_medico"):
                    pendientes = Cita.objects.filter(
                        medico=request.user.perfil_medico,
                        estado="pendiente",
                    ).count()
                    if pendientes > 0:
                        messages.warning(
                            request,
                            f"Recordatorio de Agenda: Tiene {pendientes} cita(s) pendiente(s) de atención.",
                        )
                request.session["alerta_citas_mostrada"] = True
                request.session.modified = True

        # 2. Middleware de validación de horario al intentar agendar cita (POST)
        if request.method == "POST" and "/citas/agendar/" in request.path:
            fecha_raw = request.POST.get("fecha", "")
            hora_raw = request.POST.get("hora", "")
            if fecha_raw and hora_raw:
                try:
                    fecha_obj = datetime.strptime(fecha_raw, "%Y-%m-%d").date()
                    hora_obj = datetime.strptime(hora_raw[:5], "%H:%M").time()
                    horario_ok, mensaje_err = es_horario_atencion_valido(fecha_obj, hora_obj)
                    if not horario_ok:
                        self._registrar_log(
                            usuario_actual,
                            ip_cliente,
                            f"BLOQUEO DE HORARIO FUERA DE ATENCIÓN ({fecha_raw} {hora_raw})",
                            request.path,
                        )
                        messages.error(request, f"[Control Horario] {mensaje_err}")
                        return redirect("agendar_cita")
                except ValueError:
                    pass

        response = self.get_response(request)

        # 3. Middleware de auditoría médica y accesos a información sensible
        if "/historial/" in request.path:
            if response.status_code == 200:
                accion_log = "ACCESO AUTORIZADO A HISTORIAL CLÍNICO"
            elif response.status_code == 403:
                accion_log = "ACCESO DENEGADO A HISTORIAL CLÍNICO (403)"
        elif "/reportes/" in request.path and response.status_code == 403:
            accion_log = "INTENTO NO AUTORIZADO A REPORTES MÉDICOS (403)"
        elif request.method == "POST" and response.status_code in (200, 302):
            if "/consulta/" in request.path:
                accion_log = "REGISTRO DE CONSULTA O NOTA CLÍNICA"
            elif "/cancelar/" in request.path:
                accion_log = "CANCELACIÓN DE CITA MÉDICA"

        if accion_log:
            self._registrar_log(usuario_actual, ip_cliente, accion_log, request.path)

        return response
    # Fin def __call__(self, request)

    def _registrar_log(self, usuario: str, ip_addr: str, accion: str, recurso: str) -> None:
        """Persiste la traza legal en SQLite y la emite en consola."""
        LogAuditoriaMedica.objects.create(
            usuario=usuario,
            direccion_ip=ip_addr,
            accion=accion,
            recurso=recurso,
        )
        print(
            f"[AUDITORÍA MÉDICA CMU-UNCP] Usuario: {usuario} | IP: {ip_addr} | "
            f"Acción: {accion} | Recurso: {recurso}"
        )
    # Fin def _registrar_log(self, usuario, ip_addr, accion, recurso)
# Fin class AuditoriaYControlMedicoMiddleware
