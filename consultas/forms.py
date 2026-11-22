"""Formularios clínicos con validaciones cruzadas de horarios, DNI y confidencialidad."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Cita, ConsultaMedica, Medico, Paciente
from .utils import es_horario_atencion_valido, obtener_rol_medico, sanitize_input, validar_dni_regex


class RegistroPacienteForm(forms.ModelForm):
    """ModelForm para registro de pacientes con validación de DNI, fecha y correo UNCP (RF1)."""

    username = forms.CharField(max_length=40, label="Usuario de acceso")
    password = forms.CharField(
        min_length=8,
        label="Contraseña inicial",
        widget=forms.PasswordInput(),
    )

    class Meta:
        """Campos del modelo Paciente."""

        model = Paciente
        fields = [
            "dni",
            "nombres",
            "apellidos",
            "fecha_nacimiento",
            "tipo",
            "codigo_uncp",
            "email",
            "alergias_conocidas",
        ]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "alergias_conocidas": forms.Textarea(attrs={"rows": 2}),
        }
    # Fin class Meta

    def clean_dni(self) -> str:
        """Valida formato de 8 dígitos numéricos."""
        dni_limpio = ""

        dni_limpio = sanitize_input(self.cleaned_data.get("dni", ""))
        validar_dni_regex(dni_limpio)
        return dni_limpio
    # Fin def clean_dni(self)

    def clean_fecha_nacimiento(self):
        """Impide registrar fechas de nacimiento futuras."""
        fecha_nac = None
        hoy = None

        fecha_nac = self.cleaned_data.get("fecha_nacimiento")
        hoy = timezone.localdate()
        if fecha_nac and fecha_nac > hoy:
            raise ValidationError("La fecha de nacimiento no puede ser futura.")
        return fecha_nac
    # Fin def clean_fecha_nacimiento(self)

    def clean_alergias_conocidas(self) -> str:
        """Sanitiza el campo de alergias."""
        texto = ""
        texto = sanitize_input(self.cleaned_data.get("alergias_conocidas", ""))
        return texto or "Ninguna registrada"
    # Fin def clean_alergias_conocidas(self)

    def clean(self) -> dict:
        """Valida que los estudiantes usen obligatoriamente correo institucional @uncp.edu.pe."""
        datos_limpios = {}
        tipo_pac = ""
        correo = ""

        datos_limpios = super().clean()
        tipo_pac = datos_limpios.get("tipo", "")
        correo = str(datos_limpios.get("email", "")).strip().lower()

        if tipo_pac == "estudiante" and correo and not correo.endswith("@uncp.edu.pe"):
            self.add_error(
                "email",
                "Los estudiantes deben registrar un correo institucional (@uncp.edu.pe).",
            )
        return datos_limpios
    # Fin def clean(self)
# Fin class RegistroPacienteForm


class CitaMedicaForm(forms.ModelForm):
    """ModelForm complejo para agendar citas con filtro de especialidad y cruce horario (RF2)."""

    class Meta:
        """Campos expuestos para la solicitud de cita médica."""

        model = Cita
        fields = ["paciente", "medico", "fecha", "hora", "motivo_consulta"]
        widgets = {
            "fecha": forms.DateInput(attrs={"type": "date"}),
            "hora": forms.TimeInput(attrs={"type": "time"}),
            "motivo_consulta": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Describa síntomas o motivo de consulta (mínimo 20 caracteres).",
                }
            ),
        }
    # Fin class Meta

    def __init__(self, *args, usuario_actual=None, especialidad="", **kwargs):
        """Filtra médicos por especialidad y restringe el paciente si aplica."""
        rol = ""

        super().__init__(*args, **kwargs)
        rol = obtener_rol_medico(usuario_actual)

        if especialidad:
            self.fields["medico"].queryset = Medico.objects.filter(especialidad=especialidad)
        else:
            self.fields["medico"].queryset = Medico.objects.all()

        if rol == "Pacientes" and usuario_actual and hasattr(usuario_actual, "perfil_paciente"):
            self.fields["paciente"].queryset = Paciente.objects.filter(
                id=usuario_actual.perfil_paciente.id
            )
            self.fields["paciente"].initial = usuario_actual.perfil_paciente
    # Fin def __init__(self, *args, usuario_actual=None, especialidad="", **kwargs)

    def clean_motivo_consulta(self) -> str:
        """Sanitiza y exige un mínimo de 20 caracteres en el motivo."""
        motivo_limpio = ""

        motivo_limpio = sanitize_input(self.cleaned_data.get("motivo_consulta", ""))
        if len(motivo_limpio) < 20:
            raise ValidationError(
                "El motivo de consulta debe detallar al menos 20 caracteres."
            )
        return motivo_limpio
    # Fin def clean_motivo_consulta(self)

    def clean(self) -> dict:
        """Validaciones cruzadas: horario clínico, 1 cita/día por paciente y no superposición."""
        datos_limpios = {}
        paciente = None
        medico = None
        fecha = None
        hora = None
        valido_horario = True
        msg_horario = ""
        doble_cita = False
        slot_ocupado = False

        datos_limpios = super().clean()
        paciente = datos_limpios.get("paciente")
        medico = datos_limpios.get("medico")
        fecha = datos_limpios.get("fecha")
        hora = datos_limpios.get("hora")

        if fecha and hora:
            valido_horario, msg_horario = es_horario_atencion_valido(fecha, hora)
            if not valido_horario:
                self.add_error("hora", msg_horario)

        if paciente and fecha:
            doble_cita = (
                Cita.objects.filter(paciente=paciente, fecha=fecha)
                .exclude(estado="cancelada")
                .exists()
            )
            if doble_cita:
                raise ValidationError(
                    "Regla clínica: Un paciente no puede tener 2 citas agendadas el mismo día."
                )

        if medico and fecha and hora:
            slot_ocupado = (
                Cita.objects.filter(medico=medico, fecha=fecha, hora=hora)
                .exclude(estado="cancelada")
                .exists()
            )
            if slot_ocupado:
                self.add_error(
                    "hora",
                    f"El/la {medico.nombres_completos} ya tiene una cita registrada en ese horario.",
                )

        return datos_limpios
    # Fin def clean(self)
# Fin class CitaMedicaForm


class ConsultaMedicaForm(forms.ModelForm):
    """ModelForm post-atención para diagnóstico, tratamiento, recetas y adjuntos (RF2)."""

    class Meta:
        """Campos clínicos de la consulta."""

        model = ConsultaMedica
        fields = [
            "diagnostico",
            "tratamiento",
            "medicamentos_recetados",
            "proxima_cita_control",
            "archivos_adjuntos",
        ]
        widgets = {
            "diagnostico": forms.Textarea(attrs={"rows": 3}),
            "tratamiento": forms.Textarea(attrs={"rows": 3}),
            "medicamentos_recetados": forms.Textarea(attrs={"rows": 2}),
            "proxima_cita_control": forms.DateInput(attrs={"type": "date"}),
            "archivos_adjuntos": forms.TextInput(
                attrs={"placeholder": "Ej. receta_2026_01.pdf, hemograma_lab.pdf"}
            ),
        }
    # Fin class Meta

    def clean_diagnostico(self) -> str:
        """Sanitiza el diagnóstico médico."""
        valor = ""
        valor = sanitize_input(self.cleaned_data.get("diagnostico", ""))
        return valor
    # Fin def clean_diagnostico(self)

    def clean_tratamiento(self) -> str:
        """Sanitiza el plan de tratamiento."""
        valor = ""
        valor = sanitize_input(self.cleaned_data.get("tratamiento", ""))
        return valor
    # Fin def clean_tratamiento(self)

    def clean_medicamentos_recetados(self) -> str:
        """Sanitiza los medicamentos recetados."""
        valor = ""
        valor = sanitize_input(self.cleaned_data.get("medicamentos_recetados", ""))
        return valor
    # Fin def clean_medicamentos_recetados(self)
# Fin class ConsultaMedicaForm


class NotaConsultaForm(forms.Form):
    """Formulario clásico (forms.Form) para anexar notas sin modificar la consulta inmutable."""

    contenido = forms.CharField(
        min_length=10,
        label="Nota complementaria de seguimiento",
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "placeholder": "Agregue evolución o aclaración clínica (mínimo 10 caracteres).",
            }
        ),
    )

    def clean_contenido(self) -> str:
        """Sanitiza la nota clínica antes de guardar."""
        texto = ""
        texto = sanitize_input(self.cleaned_data.get("contenido", ""))
        return texto
    # Fin def clean_contenido(self)
# Fin class NotaConsultaForm
