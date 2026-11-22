"""Vistas del Centro Médico Universitario con autorización granular."""

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from .forms import CitaMedicaForm, ConsultaMedicaForm, NotaConsultaForm, RegistroPacienteForm
from .models import Cita, ConsultaMedica, LogAuditoriaMedica, Medico, NotaConsulta, Paciente
from .utils import obtener_rol_medico


def login_view(request):
    """Login institucional diferenciado por grupo médico."""
    form = None
    usuario = None
    contexto = {}

    if request.user.is_authenticated:
        return redirect("agenda")

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            request.session["alerta_citas_mostrada"] = False
            request.session.modified = True
            messages.success(request, f"Sesión iniciada ({obtener_rol_medico(usuario)}): {usuario.username}.")
            return redirect("agenda")
    else:
        form = AuthenticationForm()

    contexto = {"form": form, "rol": "invitado"}
    return render(request, "login.html", contexto)
# Fin def login_view(request)


def logout_view(request):
    """Cierre seguro de sesión médica vía POST."""
    if request.method == "POST":
        logout(request)
        messages.info(request, "Sesión médica cerrada de forma segura.")
    return redirect("login")
# Fin def logout_view(request)


@login_required
def agenda_view(request):
    """Muestra citas filtradas según el rol del usuario autenticado."""
    rol = ""
    citas = None
    mi_paciente = None
    contexto = {}

    rol = obtener_rol_medico(request.user)
    if rol == "Médicos" and hasattr(request.user, "perfil_medico"):
        citas = Cita.objects.select_related("paciente", "medico").filter(
            medico=request.user.perfil_medico
        )
    elif rol == "Pacientes" and hasattr(request.user, "perfil_paciente"):
        mi_paciente = request.user.perfil_paciente
        citas = Cita.objects.select_related("paciente", "medico").filter(
            paciente=mi_paciente
        )
    else:
        citas = Cita.objects.select_related("paciente", "medico").all()

    contexto = {
        "citas": citas,
        "rol": rol,
        "mi_paciente": mi_paciente,
        "puede_agendar": request.user.has_perm("consultas.agendar_cita"),
        "puede_cancelar": request.user.has_perm("consultas.cancelar_cita"),
        "puede_reportes": request.user.has_perm("consultas.generar_reportes"),
    }
    return render(request, "agenda.html", contexto)
# Fin def agenda_view(request)


@login_required
def agendar_cita_view(request):
    """Permite agendar citas a Recepcionistas, Pacientes y Admins con filtro de especialidad."""
    rol = ""
    especialidad = ""
    form = None
    cita_obj = None
    contexto = {}

    if not request.user.has_perm("consultas.agendar_cita"):
        raise PermissionDenied("Su rol no cuenta con el permiso 'agendar_cita'.")

    rol = obtener_rol_medico(request.user)
    especialidad = request.GET.get("especialidad", "")

    if request.method == "POST":
        form = CitaMedicaForm(
            request.POST,
            usuario_actual=request.user,
            especialidad=especialidad,
        )
        if form.is_valid():
            cita_obj = form.save(commit=False)
            cita_obj.agendada_por = request.user
            cita_obj.save()
            messages.success(
                request,
                f"Cita #{cita_obj.id} agendada para el {cita_obj.fecha} a las {cita_obj.hora:%H:%M}.",
            )
            return redirect("agenda")
    else:
        form = CitaMedicaForm(usuario_actual=request.user, especialidad=especialidad)

    contexto = {
        "form": form,
        "rol": rol,
        "especialidades": Medico.ESPECIALIDADES,
        "especialidad_actual": especialidad,
    }
    return render(request, "agendar_cita.html", contexto)
# Fin def agendar_cita_view(request)


@login_required
def cancelar_cita_view(request, cita_id: int):
    """Cancela una cita verificando permiso granular y propiedad en caso de pacientes."""
    rol = ""
    cita = None

    if not request.user.has_perm("consultas.cancelar_cita"):
        raise PermissionDenied("No cuenta con permiso para cancelar citas.")

    rol = obtener_rol_medico(request.user)
    cita = get_object_or_404(Cita.objects.select_related("paciente", "medico"), id=cita_id)

    if rol == "Pacientes" and cita.paciente.usuario != request.user:
        raise PermissionDenied("Un paciente solo puede cancelar sus propias citas.")
    if rol == "Médicos" and cita.medico.usuario != request.user:
        raise PermissionDenied("Un médico solo puede cancelar citas de su propia agenda.")

    if request.method == "POST" and cita.estado == "pendiente":
        cita.estado = "cancelada"
        cita.save()
        messages.info(request, f"Cita #{cita.id} marcada como cancelada.")

    return redirect("agenda")
# Fin def cancelar_cita_view(request, cita_id)


@login_required
def registrar_paciente_view(request):
    """Registro de nuevos pacientes habilitado para Recepcionistas y Admins."""
    rol = ""
    form = None
    nuevo_user = None
    paciente_obj = None
    grupo_pac = None
    contexto = {}

    rol = obtener_rol_medico(request.user)
    if rol not in ("Recepcionistas", "Admins"):
        raise PermissionDenied("Solo Recepcionistas y Administradores pueden registrar pacientes.")

    if request.method == "POST":
        form = RegistroPacienteForm(request.POST)
        if form.is_valid():
            nuevo_user = User.objects.create_user(
                username=form.cleaned_data["username"],
                email=form.cleaned_data["email"],
                password=form.cleaned_data["password"],
            )
            grupo_pac, _ = Group.objects.get_or_create(name="Pacientes")
            nuevo_user.groups.add(grupo_pac)

            paciente_obj = form.save(commit=False)
            paciente_obj.usuario = nuevo_user
            paciente_obj.save()

            messages.success(request, f"Paciente {paciente_obj.nombres} registrado correctamente.")
            return redirect("agenda")
    else:
        form = RegistroPacienteForm()

    contexto = {"form": form, "rol": rol}
    return render(request, "registrar_paciente.html", contexto)
# Fin def registrar_paciente_view(request)


@login_required
def registrar_consulta_view(request, cita_id: int):
    """Registra la atención post-cita (solo Médicos/Admins; inmutable tras guardado)."""
    rol = ""
    cita = None
    form = None
    consulta_obj = None
    contexto = {}

    rol = obtener_rol_medico(request.user)
    if rol not in ("Médicos", "Admins"):
        raise PermissionDenied("Solo los médicos pueden registrar consultas clínicas.")

    cita = get_object_or_404(Cita.objects.select_related("paciente", "medico"), id=cita_id)
    if rol == "Médicos" and cita.medico.usuario != request.user:
        raise PermissionDenied("Solo puede atender citas asignadas a su propia agenda.")

    if hasattr(cita, "consulta"):
        messages.warning(
            request,
            "Esta consulta ya está registrada y es inmutable. Puede anexar notas en el historial.",
        )
        return redirect("historial_clinico", paciente_id=cita.paciente.id)

    if request.method == "POST":
        form = ConsultaMedicaForm(request.POST)
        if form.is_valid():
            consulta_obj = form.save(commit=False)
            consulta_obj.cita = cita
            consulta_obj.registrada_por = request.user
            consulta_obj.save()

            cita.estado = "completada"
            cita.save()

            messages.success(request, f"Consulta clínica de {cita.paciente.apellidos} registrada.")
            return redirect("historial_clinico", paciente_id=cita.paciente.id)
    else:
        form = ConsultaMedicaForm()

    contexto = {"form": form, "cita": cita, "rol": rol}
    return render(request, "registrar_consulta.html", contexto)
# Fin def registrar_consulta_view(request, cita_id)


@login_required
def historial_clinico_view(request, paciente_id: int):
    """Acceso auditado al historial clínico: solo Médicos, Admins y el propio Paciente."""
    rol = ""
    paciente = None
    consultas = None
    form_nota = None
    consulta_id = None
    consulta_target = None
    contexto = {}

    if not request.user.has_perm("consultas.ver_historial_clinico"):
        raise PermissionDenied("No cuenta con el permiso 'ver_historial_clinico'.")

    rol = obtener_rol_medico(request.user)
    paciente = get_object_or_404(Paciente, id=paciente_id)

    if rol == "Pacientes" and paciente.usuario != request.user:
        raise PermissionDenied("Confidencialidad: No puede ver el historial clínico de otro paciente.")

    if request.method == "POST":
        if rol not in ("Médicos", "Admins"):
            raise PermissionDenied("Solo médicos pueden anexar notas clínicas de seguimiento.")
        form_nota = NotaConsultaForm(request.POST)
        consulta_id = request.POST.get("consulta_id")
        if form_nota.is_valid() and consulta_id:
            consulta_target = get_object_or_404(
                ConsultaMedica,
                id=consulta_id,
                cita__paciente=paciente,
            )
            NotaConsulta.objects.create(
                consulta=consulta_target,
                autor=request.user,
                contenido=form_nota.cleaned_data["contenido"],
            )
            messages.success(request, "Nota de seguimiento agregada sin alterar el diagnóstico original.")
            return redirect("historial_clinico", paciente_id=paciente.id)
    else:
        form_nota = NotaConsultaForm()

    consultas = (
        ConsultaMedica.objects.select_related("cita", "cita__medico", "registrada_por")
        .prefetch_related("notas", "notas__autor")
        .filter(cita__paciente=paciente)
    )
    contexto = {
        "paciente": paciente,
        "consultas": consultas,
        "form_nota": form_nota,
        "rol": rol,
    }
    return render(request, "historial_clinico.html", contexto)
# Fin def historial_clinico_view(request, paciente_id)


@login_required
def reportes_view(request):
    """Estadísticas operativas y logs de auditoría: exclusivo para permiso generar_reportes."""
    rol = ""
    citas_especialidad = None
    medicos_top = None
    pacientes_frecuentes = None
    logs = None
    contexto = {}

    if not request.user.has_perm("consultas.generar_reportes"):
        raise PermissionDenied("Acceso denegado: solo administradores pueden generar reportes.")

    rol = obtener_rol_medico(request.user)
    citas_especialidad = (
        Cita.objects.values("medico__especialidad")
        .annotate(total=Count("id"))
        .order_by("-total")
    )
    medicos_top = (
        Medico.objects.annotate(total_citas=Count("citas"))
        .order_by("-total_citas")[:5]
    )
    pacientes_frecuentes = (
        Paciente.objects.annotate(total_citas=Count("citas"))
        .order_by("-total_citas")[:5]
    )
    logs = LogAuditoriaMedica.objects.all()[:30]

    contexto = {
        "rol": rol,
        "citas_especialidad": citas_especialidad,
        "medicos_top": medicos_top,
        "pacientes_frecuentes": pacientes_frecuentes,
        "logs": logs,
    }
    return render(request, "reportes.html", contexto)
# Fin def reportes_view(request)
