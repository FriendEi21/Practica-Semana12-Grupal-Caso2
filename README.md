# Caso 2: Plataforma de Gestión de Consultas Médicas (CMU - UNCP)

Aplicación web fullstack en Django 6.1.3 para la Práctica Grupal Semana 12 (IS093A). Digitaliza el agendamiento de citas, historial clínico electrónico inmutable, control granular de permisos y auditoría de confidencialidad del Centro Médico Universitario de la UNCP.

## 1. Diagrama de Roles y Permisos Implementados

+------------------+-----------------------+--------------+---------------+------------------+
| Grupo / Rol      | ver_historial_clinico | agendar_cita | cancelar_cita | generar_reportes |
+------------------+-----------------------+--------------+---------------+------------------+
| Admins           | SI (Todos)            | SI           | SI (Todas)    | SI (Exclusivo)   |
| Médicos          | SI (Todos)            | NO           | SI (Propias)  | NO               |
| Recepcionistas   | NO                    | SI           | SI (Todas)    | NO               |
| Pacientes        | SI (Solo propio)      | SI (Propias) | SI (Propias)  | NO               |
+------------------+-----------------------+--------------+---------------+------------------+

Flujo de Seguridad y Middleware:
[ Request ] -> [ AuditoriaYControlMedicoMiddleware ]
                    |-- Alerta de citas pendientes (Médicos al iniciar sesión)
                    |-- Validación de horario (L-V 08:00-18:00 / Sáb 08:00-13:00)
                    |-- Registro legal de accesos a /historial/ y bloqueos 403
            -> [ Vistas protegidas con has_perm() + Timeout de sesión 20 min ]

## 2. Reglas de Negocio y Seguridad Aplicadas
* **RF1 (Pacientes y Médicos):** Validación de DNI (8 dígitos), CMP (5-6 dígitos), fecha de nacimiento no futura y correo `@uncp.edu.pe` obligatorio para estudiantes.
* **RF2 (Agendamiento e Integridad):** Filtro de médicos por especialidad, motivo mínimo de 20 caracteres, bloqueo de citas duplicadas en el mismo día para un paciente y bloqueo de superposición horaria por médico. Las consultas médicas registradas son inmutables; solo permiten anexar notas (`NotaConsultaForm`).
* **RF5 (Django Admin):** Agenda filtrable por médico/fecha/especialidad, campos calculados (`Edad` y `Días desde última consulta`), acción masiva *"Marcar citas como completadas"* y panel estadístico en `/reportes/`.

## 3. Instalación y Datos de Prueba
1. `python -m venv venv` y `venv\Scripts\activate`
2. `pip install -r requirements.txt`
3. `python manage.py makemigrations` y `python manage.py migrate`
4. Poblar base de datos (8 médicos, 15 pacientes, 30 citas):
   `python poblar_datos.py`
5. `python manage.py runserver`

## 4. Credenciales de Prueba (Clave general: `Uncp2026!`)
* Administrador: `director_cmu`
* Médicos: `medico1` ... `medico8`
* Recepcionista: `recepcion1`
* Pacientes: `paciente1` ... `paciente15`

---
© 2026 Todos los derechos reservados por FriendEi21.