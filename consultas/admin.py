"""Personalización operativa del Django Admin para el Centro Médico UNCP (RF5)."""

from django.contrib import admin
from consultas.models import Cita, ConsultaMedica, LogAuditoriaMedica, Medico, NotaConsulta, Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    """Gestión de pacientes con búsqueda por DNI/nombre y campos calculados."""

    list_display = (
        "dni",
        "apellidos",
        "nombres",
        "tipo",
        "codigo_uncp",
        "mostrar_edad",
        "mostrar_dias_ultima_consulta",
    )
    list_filter = ("tipo",)
    search_fields = ("dni", "nombres", "apellidos", "codigo_uncp")

    @admin.display(description="Edad")
    def mostrar_edad(self, obj) -> str:
        """Campo calculado: edad actual del paciente."""
        etiqueta = ""
        etiqueta = f"{obj.edad} años"
        return etiqueta
    # Fin def mostrar_edad(self, obj)

    @admin.display(description="Días desde última consulta")
    def mostrar_dias_ultima_consulta(self, obj) -> str:
        """Campo calculado: días transcurridos desde la última atención."""
        dias = None
        etiqueta = ""

        dias = obj.dias_desde_ultima_consulta
        etiqueta = "Sin consultas" if dias is None else f"{dias} día(s)"
        return etiqueta
    # Fin def mostrar_dias_ultima_consulta(self, obj)
# Fin class PacienteAdmin


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    """Gestión de médicos y especialidades."""

    list_display = ("cmp", "nombres_completos", "especialidad", "consultorio", "horarios_atencion")
    list_filter = ("especialidad", "consultorio")
    search_fields = ("cmp", "nombres_completos")
# Fin class MedicoAdmin


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    """Vista de agenda diaria por médico y acción masiva para completar citas (RF5)."""

    list_display = ("id", "fecha", "hora", "medico", "paciente", "estado")
    list_filter = ("medico", "fecha", "estado", "medico__especialidad")
    search_fields = ("paciente__dni", "paciente__apellidos", "medico__nombres_completos")
    date_hierarchy = "fecha"
    actions = ["marcar_citas_completadas"]

    def get_queryset(self, request):
        """Optimiza las consultas de agenda con select_related."""
        queryset_base = None
        queryset_opt = None

        queryset_base = super().get_queryset(request)
        queryset_opt = queryset_base.select_related("paciente", "medico", "agendada_por")
        return queryset_opt
    # Fin def get_queryset(self, request)

    @admin.action(description="Marcar citas como completadas")
    def marcar_citas_completadas(self, request, queryset) -> None:
        """Acción masiva que marca las citas pendientes seleccionadas como completadas."""
        actualizadas = 0

        actualizadas = queryset.filter(estado="pendiente").update(estado="completada")
        self.message_user(
            request,
            f"Se marcaron {actualizadas} cita(s) como completadas.",
        )
    # Fin def marcar_citas_completadas(self, request, queryset)
# Fin class CitaAdmin


@admin.register(ConsultaMedica)
class ConsultaMedicaAdmin(admin.ModelAdmin):
    """Consultas médicas de solo lectura una vez registradas (RNF Integridad)."""

    list_display = ("id", "cita", "registrada_por", "fecha_registro", "proxima_cita_control")
    list_filter = ("fecha_registro", "cita__medico__especialidad")
    search_fields = ("cita__paciente__dni", "diagnostico")
    readonly_fields = (
        "cita",
        "diagnostico",
        "tratamiento",
        "medicamentos_recetados",
        "proxima_cita_control",
        "archivos_adjuntos",
        "registrada_por",
        "fecha_registro",
    )

    def has_change_permission(self, request, obj=None) -> bool:
        """Impide modificar consultas ya registradas para mantener integridad clínica."""
        return False
    # Fin def has_change_permission(self, request, obj=None)
# Fin class ConsultaMedicaAdmin


@admin.register(NotaConsulta)
class NotaConsultaAdmin(admin.ModelAdmin):
    """Administración de notas complementarias de seguimiento."""

    list_display = ("id", "consulta", "autor", "fecha_creacion")
    readonly_fields = ("fecha_creacion",)
# Fin class NotaConsultaAdmin


@admin.register(LogAuditoriaMedica)
class LogAuditoriaMedicaAdmin(admin.ModelAdmin):
    """Registro legal de auditoría médica de solo lectura."""

    list_display = ("fecha_hora", "usuario", "direccion_ip", "accion", "recurso")
    list_filter = ("usuario", "fecha_hora")
    search_fields = ("usuario", "accion", "recurso")
    readonly_fields = ("usuario", "fecha_hora", "direccion_ip", "accion", "recurso")

    def has_add_permission(self, request) -> bool:
        """Evita inserciones manuales en el log legal."""
        return False
    # Fin def has_add_permission(self, request)
# Fin class LogAuditoriaMedicaAdmin
