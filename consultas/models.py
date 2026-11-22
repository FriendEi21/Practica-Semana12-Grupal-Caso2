"""Modelos ORM para la Plataforma de Consultas Médicas e Historial Clínico."""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from consultas.utils import validar_cmp_regex, validar_dni_regex


class Paciente(models.Model):
    """Representa un estudiante o docente atendido en el Centro Médico UNCP."""

    TIPOS_PACIENTE = [
        ("estudiante", "Estudiante"),
        ("docente", "Docente"),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_paciente",
    )
    dni = models.CharField(max_length=8, unique=True, validators=[validar_dni_regex])
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80)
    fecha_nacimiento = models.DateField()
    tipo = models.CharField(max_length=15, choices=TIPOS_PACIENTE)
    codigo_uncp = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    alergias_conocidas = models.TextField(blank=True, default="Ninguna registrada")

    objects = models.Manager()

    class Meta:
        """Metadatos y permisos granulares de historial clínico (RF3)."""

        verbose_name_plural = "Pacientes"
        ordering = ["apellidos", "nombres"]
        permissions = [
            ("ver_historial_clinico", "Puede visualizar el historial clínico de pacientes"),
            ("generar_reportes", "Puede generar reportes y estadísticas médicas"),
        ]
    # Fin class Meta

    @property
    def edad(self) -> int:
        """Calcula la edad exacta del paciente en años."""
        hoy = None
        anios = 0
        cumplio = False

        hoy = timezone.localdate()
        cumplio = (hoy.month, hoy.day) >= (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
        anios = hoy.year - self.fecha_nacimiento.year - (0 if cumplio else 1)
        return max(anios, 0)
    # Fin def edad(self)

    @property
    def dias_desde_ultima_consulta(self):
        """Calcula los días transcurridos desde la última consulta atendida."""
        ultima = None
        hoy = None
        dias = 0

        ultima = (
            ConsultaMedica.objects.filter(cita__paciente=self)
            .order_by("-fecha_registro")
            .first()
        )
        if not ultima:
            return None

        hoy = timezone.localdate()
        dias = (hoy - ultima.fecha_registro.date()).days
        return max(dias, 0)
    # Fin def dias_desde_ultima_consulta(self)

    def __str__(self) -> str:
        """Retorna nombre completo y DNI del paciente."""
        etiqueta = ""
        etiqueta = f"{self.apellidos}, {self.nombres} (DNI: {self.dni})"
        return etiqueta
    # Fin def __str__(self)
# Fin class Paciente


class Medico(models.Model):
    """Profesional de salud registrado en el Centro Médico Universitario."""

    ESPECIALIDADES = [
        ("medicina_general", "Medicina General"),
        ("odontologia", "Odontología"),
        ("psicologia", "Psicología"),
        ("nutricion", "Nutrición"),
        ("ginecologia", "Ginecología"),
    ]

    usuario = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="perfil_medico",
    )
    cmp = models.CharField(max_length=10, unique=True, validators=[validar_cmp_regex])
    nombres_completos = models.CharField(max_length=120)
    especialidad = models.CharField(max_length=30, choices=ESPECIALIDADES)
    horarios_atencion = models.CharField(max_length=100, default="L-V 08:00-18:00 / Sáb 08:00-13:00")
    consultorio = models.CharField(max_length=30)

    objects = models.Manager()

    class Meta:
        """Metadatos del modelo Medico."""

        verbose_name_plural = "Médicos"
        ordering = ["especialidad", "nombres_completos"]
    # Fin class Meta

    def __str__(self) -> str:
        """Retorna nombre del médico, CMP y especialidad."""
        etiqueta = ""
        etiqueta = f"Dr(a). {self.nombres_completos} - {self.get_especialidad_display()} (CMP {self.cmp})"
        return etiqueta
    # Fin def __str__(self)
# Fin class Medico


class Cita(models.Model):
    """Representa una cita médica agendada en un consultorio."""

    ESTADOS_CITA = [
        ("pendiente", "Pendiente"),
        ("completada", "Completada"),
        ("cancelada", "Cancelada"),
    ]

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    medico = models.ForeignKey(
        Medico,
        on_delete=models.PROTECT,
        related_name="citas",
    )
    fecha = models.DateField()
    hora = models.TimeField()
    motivo_consulta = models.TextField()
    estado = models.CharField(max_length=15, choices=ESTADOS_CITA, default="pendiente")
    agendada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="citas_agendadas",
    )
    creada_en = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        """Metadatos y permisos granulares de agendamiento (RF3)."""

        verbose_name_plural = "Citas Médicas"
        ordering = ["-fecha", "hora"]
        permissions = [
            ("agendar_cita", "Puede agendar citas médicas"),
            ("cancelar_cita", "Puede cancelar citas médicas"),
        ]
    # Fin class Meta

    def __str__(self) -> str:
        """Retorna descripción compacta de la cita."""
        resumen = ""
        resumen = f"Cita #{self.id} | {self.fecha} {self.hora:%H:%M} - {self.paciente.dni}"
        return resumen
    # Fin def __str__(self)
# Fin class Cita


class ConsultaMedica(models.Model):
    """Registro clínico post-atención inmutable (RNF Integridad)."""

    cita = models.OneToOneField(
        Cita,
        on_delete=models.PROTECT,
        related_name="consulta",
    )
    diagnostico = models.TextField()
    tratamiento = models.TextField()
    medicamentos_recetados = models.TextField()
    proxima_cita_control = models.DateField(null=True, blank=True)
    archivos_adjuntos = models.CharField(
        max_length=250,
        blank=True,
        help_text="Referencias de recetas o exámenes adjuntos (simulado en texto).",
    )
    registrada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consultas_registradas",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        """Metadatos del modelo ConsultaMedica."""

        verbose_name_plural = "Consultas Médicas"
        ordering = ["-fecha_registro"]
    # Fin class Meta

    def __str__(self) -> str:
        """Retorna identificador clínico de la consulta."""
        texto = ""
        texto = f"Consulta #{self.id} - {self.cita.paciente.apellidos} ({self.cita.fecha})"
        return texto
    # Fin def __str__(self)
# Fin class ConsultaMedica


class NotaConsulta(models.Model):
    """Notas complementarias que permiten anexar seguimiento sin alterar la consulta original."""

    consulta = models.ForeignKey(
        ConsultaMedica,
        on_delete=models.CASCADE,
        related_name="notas",
    )
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    contenido = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    objects = models.Manager()

    class Meta:
        """Metadatos del modelo NotaConsulta."""

        verbose_name_plural = "Notas de Seguimiento"
        ordering = ["fecha_creacion"]
    # Fin class Meta

    def __str__(self) -> str:
        """Retorna encabezado de la nota clínica."""
        etiqueta = ""
        etiqueta = f"Nota en Consulta #{self.consulta.id} por {self.autor}"
        return etiqueta
    # Fin def __str__(self)
# Fin class NotaConsulta


class LogAuditoriaMedica(models.Model):
    """Trazabilidad legal de accesos a historiales clínicos y cambios sensibles (RF4)."""

    usuario = models.CharField(max_length=60)
    fecha_hora = models.DateTimeField(auto_now_add=True)
    direccion_ip = models.GenericIPAddressField(null=True, blank=True)
    accion = models.CharField(max_length=200)
    recurso = models.CharField(max_length=150)

    objects = models.Manager()

    class Meta:
        """Metadatos del modelo LogAuditoriaMedica."""

        verbose_name_plural = "Auditoría Médica"
        ordering = ["-fecha_hora"]
    # Fin class Meta

    def __str__(self) -> str:
        """Retorna línea resumida del log médico."""
        linea = ""
        linea = f"[{self.fecha_hora:%d/%m/%Y %H:%M}] {self.usuario} -> {self.accion}"
        return linea
    # Fin def __str__(self)
# Fin class LogAuditoriaMedica
