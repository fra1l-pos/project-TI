import re

from django.db import migrations


NIVELES_CANONICOS = {
    '3 años Inicial', '4 años Inicial', '5 años Inicial',
    '1ro Primaria', '2do Primaria', '3ro Primaria', '4to Primaria', '5to Primaria', '6to Primaria',
    '1ro Secundaria', '2do Secundaria', '3ro Secundaria', '4to Secundaria', '5to Secundaria',
}

ORDINALES = {'1': '1ro', '2': '2do', '3': '3ro', '4': '4to', '5': '5to', '6': '6to'}


def _nivel(grado):
    """Devuelve el nivel sin la sección ('3ro Primaria A' -> '3ro Primaria')."""
    partes = grado.rsplit(' ', 1)
    if len(partes) == 2 and len(partes[1]) == 1:
        return partes[0]
    return grado


def _normalizar(grado):
    """Lleva el grado al formato canónico 'Nivel Sección'.

    - Une el separador 'Nivel - Sección' a 'Nivel Sección'.
    - Convierte ordinales con '°' ('1°' -> '1ro', '3°' -> '3ro', ...).
    """
    s = (grado or '').strip()
    if not s:
        return s
    # 'Nivel - Sección' -> 'Nivel Sección'
    s = re.sub(r'\s+-\s+([A-Z])\s*$', r' \1', s)
    # Ordinal con '°' al inicio
    m = re.match(r'^([1-6])°\s*', s)
    if m:
        s = f"{ORDINALES[m.group(1)]} {s[m.end():]}"
        s = re.sub(r'\s+', ' ', s).strip()
    return s


def normalizar_grados(apps, schema_editor):
    Alumno = apps.get_model('alumnos', 'Alumno')
    for alumno in Alumno.objects.all():
        original = alumno.grado or ''
        nuevo = _normalizar(original)
        if nuevo == original:
            continue
        # Solo aplicar si el resultado cae en un nivel oficial (evita romper datos raros)
        if _nivel(nuevo) in NIVELES_CANONICOS:
            alumno.grado = nuevo
            alumno.save(update_fields=['grado'])


class Migration(migrations.Migration):

    dependencies = [
        ('alumnos', '0002_initial'),
    ]

    operations = [
        migrations.RunPython(normalizar_grados, migrations.RunPython.noop),
    ]
