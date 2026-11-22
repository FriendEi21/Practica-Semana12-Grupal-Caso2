"""Script de carga inicial Caso 2: 8 médicos, 15 pacientes, 30 citas y grupos."""

import os
from datetime import date, time, timedelta
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth.models import Group, Permission, User  # pylint: disable=wrong-import-position
from django.utils import timezone  # pylint: disable=wrong-import-position
from consultas.models import Cita, ConsultaMedica, Medico, Paciente  # pylint: disable=wrong-import-position


def poblar_caso2() -> None:
    """Crea grupos/permisos, 8 médicos, 15 pacientes, 30 citas y consultas."""
    hoy = None
    g_admins = None
    g_medicos = None
    g_recep = None
    g_pacientes = None
    p_hist = None
    p_agendar = None
    p_cancelar = None
    p_reportes = None
    admin_user = None
    recep_user = None
    creado = False
    medicos_lista = []
    pacientes_lista = []
    especialidades = []
    horas_slot = []
    idx = 0
    fecha_cita = None
    cita_obj = None

    hoy = timezone.localdate()

    g_admins, _ = Group.objects.get_or_create(name="Admins")
    g_medicos, _ = Group.objects.get_or_create(name="Médicos")
    g_recep, _ = Group.objects.get_or_create(name="Recepcionistas")
    g_pacientes, _ = Group.objects.get_or_create(name="Pacientes")

    p_hist = Permission.objects.get(codename="ver_historial_clinico")
    p_agendar = Permission.objects.get(codename="agendar_cita")
    p_cancelar = Permission.objects.get(codename="cancelar_cita")
    p_reportes = Permission.objects.get(codename="generar_reportes")

    g_admins.permissions.set([p_hist, p_agendar, p_cancelar, p_reportes])
    g_medicos.permissions.set([p_hist, p_cancelar])
    g_recep.permissions.set([p_agendar, p_cancelar])
    g_pacientes.permissions.set([p_hist, p_agendar, p_cancelar])

    admin_user, creado = User.objects.get_or_create(
        username="director_cmu",
        defaults={"email": "director@uncp.edu.pe", "is_staff": True, "is_superuser": True},
    )
    if creado:
        admin_user.set_password("Uncp2026!")
        admin_user.save()
    admin_user.groups.add(g_admins)

    recep_user, creado = User.objects.get_or_create(
        username="recepcion1",
        defaults={"email": "recepcion1@uncp.edu.pe", "is_staff": True},
    )
    if creado:
        recep_user.set_password("Uncp2026!")
        recep_user.save()
    recep_user.groups.add(g_recep)

    especialidades = [
        ("medicina_general", "Carlos Mendoza Rivas", "C-101"),
        ("medicina_general", "Lucía Paredes Soto", "C-102"),
        ("odontologia", "Miguel Huamán Quispe", "C-103"),
        ("odontologia", "Rosa Torres Villanueva", "C-104"),
        ("psicologia", "Elena Castro Salas", "C-201"),
        ("nutricion", "Javier Rojas Salazar", "C-202"),
        ("ginecologia", "Patricia Flores Limaylla", "C-203"),
        ("medicina_general", "Fernando Vera Ramos", "C-105"),
    ]

    for idx, (esp, nombre_med, cons) in enumerate(especialidades, start=1):
        u_med, creado = User.objects.get_or_create(
            username=f"medico{idx}",
            defaults={"email": f"medico{idx}@uncp.edu.pe"},
        )
        if creado:
            u_med.set_password("Uncp2026!")
            u_med.save()
        u_med.groups.add(g_medicos)

        med_obj, _ = Medico.objects.get_or_create(
            usuario=u_med,
            defaults={
                "cmp": f"{54320 + idx}",
                "nombres_completos": nombre_med,
                "especialidad": esp,
                "consultorio": cons,
            },
        )
        medicos_lista.append(med_obj)

    for idx in range(1, 16):
        es_docente = idx > 12
        tipo_p = "docente" if es_docente else "estudiante"
        u_pac, creado = User.objects.get_or_create(
            username=f"paciente{idx}",
            defaults={"email": f"paciente{idx}@uncp.edu.pe"},
        )
        if creado:
            u_pac.set_password("Uncp2026!")
            u_pac.save()
        u_pac.groups.add(g_pacientes)

        pac_obj, _ = Paciente.objects.get_or_create(
            usuario=u_pac,
            defaults={
                "dni": f"{71000000 + idx}",
                "nombres": f"Nombre{idx}",
                "apellidos": f"Apellido{idx}",
                "fecha_nacimiento": date(1985 if es_docente else 2003, (idx % 12) + 1, (idx % 25) + 1),
                "tipo": tipo_p,
                "codigo_uncp": f"2022{idx:05d}I",
                "email": f"paciente{idx}@uncp.edu.pe",
                "alergias_conocidas": "Penicilina" if idx % 4 == 0 else "Ninguna conocida",
            },
        )
        pacientes_lista.append(pac_obj)

    if Cita.objects.count() == 0:
        horas_slot = [time(8, 30), time(9, 30), time(10, 30), time(11, 30), time(15, 0), time(16, 0)]
        for idx in range(30):
            # Distribuimos en días hábiles pasados y futuros evitando domingos
            desplazamiento = (idx - 18)
            fecha_cita = hoy + timedelta(days=desplazamiento)
            if fecha_cita.weekday() == 6:
                fecha_cita = fecha_cita + timedelta(days=1)

            estado_c = "completada" if idx < 16 else ("pendiente" if idx < 27 else "cancelada")
            pac = pacientes_lista[idx % len(pacientes_lista)]
            med = medicos_lista[idx % len(medicos_lista)]
            hora_c = horas_slot[idx % len(horas_slot)]

            # Garantizar que paciente no repita mismo día
            while Cita.objects.filter(paciente=pac, fecha=fecha_cita).exists():
                fecha_cita = fecha_cita + timedelta(days=1)
                if fecha_cita.weekday() == 6:
                    fecha_cita = fecha_cita + timedelta(days=1)

            cita_obj = Cita.objects.create(
                paciente=pac,
                medico=med,
                fecha=fecha_cita,
                hora=hora_c,
                motivo_consulta=f"Evaluación clínica periódica y control de síntomas generales #{idx + 1}.",
                estado=estado_c,
                agendada_por=recep_user,
            )

            if estado_c == "completada":
                ConsultaMedica.objects.create(
                    cita=cita_obj,
                    diagnostico="Cuadro estable sin complicaciones agudas detectadas.",
                    tratamiento="Hidratación, reposo relativo y control ambulatorio.",
                    medicamentos_recetados="Paracetamol 500mg c/8h por 3 días",
                    proxima_cita_control=fecha_cita + timedelta(days=15),
                    archivos_adjuntos=f"receta_cmu_{cita_obj.id}.pdf",
                    registrada_por=med.usuario,
                )

    print(
        f"[OK] Poblado Caso 2: {Medico.objects.count()} médicos, "
        f"{Paciente.objects.count()} pacientes, {Cita.objects.count()} citas, "
        f"{ConsultaMedica.objects.count()} consultas."
    )
# Fin def poblar_caso2()


if __name__ == "__main__":
    poblar_caso2()
