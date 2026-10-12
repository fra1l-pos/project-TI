<div align="center">

# Portal de Pagos

**I.E. "Divino Niño Jesús"**

Sistema web para la gestión de **pensiones escolares**

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?logo=sqlite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/TailwindCSS-CDN-06B6D4?logo=tailwindcss&logoColor=white)

</div>

---

## Descripción

Portal con dos accesos: **administrador** (personal del colegio) y **apoderado**
(padres de familia). Permite registrar alumnos y apoderados, controlar las cuotas
mensuales y los pagos con comprobante, ver a los deudores y enviar notificaciones.

## Funcionalidades

### Administrador
- Registrar y editar alumnos y apoderados (validación de DNI, sin duplicados).
- Carga masiva desde **Excel/CSV** con plantilla de ejemplo.
- Crear el **año académico** y generar las pensiones mensuales.
- Ver **deudores** (alumnos con cuotas impagas) y enviar recordatorios.
- Enviar notificaciones internas a los apoderados.

### Apoderado
- Ver sus hijos y el estado de sus pagos.
- Registrar el **pago** de una cuota (método, N° de operación y comprobante).
- Recibir notificaciones (incluida la confirmación automática de pago).

## Tecnologías

| Tecnología | Uso |
|---|---|
| **Python 3.13** | Lenguaje base |
| **Django 6.1** | Framework web |
| **SQLite** | Base de datos de desarrollo |
| **TailwindCSS** | Interfaz (vía CDN) |
| **openpyxl** | Generación/lectura de Excel |

## Instalación y ejecución

```bash
# 1. Clonar el repositorio
git clone git@github.com:fra1l-pos/project-TI.git
cd project-TI

# 2. Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate        # En Windows: .venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Preparar la base de datos
python manage.py migrate
python manage.py seed            # crea datos de ejemplo (opcional)

# 5. Levantar el servidor
python manage.py runserver
```

Abrir en el navegador: **http://127.0.0.1:8000**

## Acceso de ejemplo

> Usuarios creados por el comando `seed` (datos de ejemplo).

| Rol | Usuario | Contraseña |
|---|---|---|
| Administrador | `admin` | `admin123` |
| Apoderado | `padre.ejemplo` | `padre123` |

## Estructura del proyecto

```
config/          # configuración del proyecto (settings, urls)
usuarios/        # usuario personalizado (administrador / apoderado)
alumnos/         # gestión de alumnos y carga masiva
pagos/           # años académicos, pensiones, pagos y deudores
notificaciones/  # mensajes internos al apoderado
templates/       # plantillas HTML (layout, administrador, padre)
```

> La base de datos (`db.sqlite3`) y los archivos subidos (`media/`) **no** se
> incluyen en el repositorio; se generan al ejecutar `migrate`.
