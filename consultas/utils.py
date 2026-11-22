"""Módulo auxiliar para validaciones médicas, sanitización y control de horarios."""

from datetime import date, time
from django.core.validators import RegexValidator
from django.utils.html import escape


validar_dni_regex = RegexValidator(
    regex=r"^\d{8}$",
    message="El DNI debe tener exactamente 8 dígitos numéricos.",
    code="dni_invalido",
)

validar_cmp_regex = RegexValidator(
    regex=r"^\d{5,6}$",
    message="El código CMP debe contener entre 5 y 6 dígitos (ej. 12345).",
    code="cmp_invalido",
)


def sanitize_input(texto: str) -> str:
    """Elimina espacios innecesarios y escapa caracteres HTML peligrosos."""
    valor_crudo = ""
    valor_limpio = ""
    valor_seguro = ""

    if texto is None:
        return valor_seguro

    valor_crudo = str(texto)
    valor_limpio = valor_crudo.strip()
    valor_seguro = escape(valor_limpio)
    return valor_seguro
# Fin def sanitize_input(texto)


def obtener_ip_cliente(request) -> str:
    """Obtiene la IP del cliente desde cabeceras de proxy o conexión directa."""
    x_forwarded = ""
    ip_final = ""

    x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if x_forwarded:
        ip_final = x_forwarded.split(",")[0].strip()
    else:
        ip_final = request.META.get("REMOTE_ADDR", "127.0.0.1")

    return ip_final
# Fin def obtener_ip_cliente(request)


def es_horario_atencion_valido(fecha_cita: date, hora_cita: time) -> tuple:
    """Valida horario del Centro Médico: L-V 08:00-18:00 y Sáb 08:00-13:00."""
    dia_semana = 0
    hora_inicio = time(8, 0)
    hora_fin_lv = time(18, 0)
    hora_fin_sab = time(13, 0)

    dia_semana = fecha_cita.weekday()  # 0=Lunes ... 5=Sábado, 6=Domingo

    if dia_semana == 6:
        return False, "El Centro Médico no atiende los días domingo."

    if dia_semana == 5:
        if hora_inicio <= hora_cita <= hora_fin_sab:
            return True, ""
        return False, "Los sábados la atención es únicamente de 08:00 a 13:00."

    if hora_inicio <= hora_cita <= hora_fin_lv:
        return True, ""

    return False, "De lunes a viernes la atención es de 08:00 a 18:00."
# Fin def es_horario_atencion_valido(fecha_cita, hora_cita)


def obtener_rol_medico(user) -> str:
    """Retorna el grupo principal del usuario autenticado."""
    rol = "invitado"

    if not user or not user.is_authenticated:
        return rol

    if user.is_superuser or user.groups.filter(name="Admins").exists():
        rol = "Admins"
    elif user.groups.filter(name="Médicos").exists():
        rol = "Médicos"
    elif user.groups.filter(name="Recepcionistas").exists():
        rol = "Recepcionistas"
    elif user.groups.filter(name="Pacientes").exists():
        rol = "Pacientes"

    return rol
# Fin def obtener_rol_medico(user)
