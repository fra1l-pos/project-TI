from django import forms
from .models import Alumno

# ── Valores estandarizados compartidos ─────────────────────────────────────
GRADOS_CHOICES = [
    ('', '— Seleccionar grado —'),
    # Inicial
    ('3 años Inicial',  '3 años Inicial'),
    ('4 años Inicial',  '4 años Inicial'),
    ('5 años Inicial',  '5 años Inicial'),
    # Primaria
    ('1ro Primaria', '1ro Primaria'),
    ('2do Primaria', '2do Primaria'),
    ('3ro Primaria', '3ro Primaria'),
    ('4to Primaria', '4to Primaria'),
    ('5to Primaria', '5to Primaria'),
    ('6to Primaria', '6to Primaria'),
    # Secundaria
    ('1ro Secundaria', '1ro Secundaria'),
    ('2do Secundaria', '2do Secundaria'),
    ('3ro Secundaria', '3ro Secundaria'),
    ('4to Secundaria', '4to Secundaria'),
    ('5to Secundaria', '5to Secundaria'),
]

SECCIONES_CHOICES = [
    ('', '— Sección —'),
    ('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('E', 'E'),
]

MESES_CHOICES = [
    (1,  'Enero'),   (2,  'Febrero'),  (3,  'Marzo'),
    (4,  'Abril'),   (5,  'Mayo'),     (6,  'Junio'),
    (7,  'Julio'),   (8,  'Agosto'),   (9,  'Septiembre'),
    (10, 'Octubre'), (11, 'Noviembre'),(12, 'Diciembre'),
]

_INPUT  = 'w-full px-3 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-colegio-500 focus:border-colegio-500 text-sm bg-white'
_SELECT = 'w-full px-3 py-2.5 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-colegio-500 focus:border-colegio-500 text-sm bg-white'

# ── Formulario de edición de alumno (padre ya asignado) ────────────────────
class AlumnoEditForm(forms.Form):
    """
    Formulario para EDITAR un alumno existente.
    No incluye campo padre (ya está asignado); usa grado_nivel + seccion separados.
    """
    nombres = forms.CharField(
        label='Nombres del alumno',
        max_length=100,
        widget=forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Ej: Lucas Mateo'}),
    )
    apellidos = forms.CharField(
        label='Apellidos del alumno',
        max_length=100,
        widget=forms.TextInput(attrs={'class': _INPUT, 'placeholder': 'Ej: Mendoza Quispe'}),
    )
    grado_nivel = forms.ChoiceField(
        label='Grado',
        choices=GRADOS_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    seccion = forms.ChoiceField(
        label='Sección',
        choices=SECCIONES_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    mes_ingreso = forms.ChoiceField(
        label='Mes de ingreso',
        choices=MESES_CHOICES,
        widget=forms.Select(attrs={'class': _SELECT}),
    )
    activo = forms.BooleanField(
        label='Alumno activo',
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-colegio-600 focus:ring-colegio-500 border-gray-300 rounded'}),
    )


# ── AlumnoForm (solo para compatibilidad interna si se necesita) ───────────
class AlumnoForm(forms.ModelForm):
    class Meta:
        model  = Alumno
        fields = ['padre', 'nombres', 'apellidos', 'grado', 'mes_ingreso', 'activo']
        widgets = {
            'padre':       forms.Select(attrs={'class': _SELECT}),
            'nombres':     forms.TextInput(attrs={'class': _INPUT}),
            'apellidos':   forms.TextInput(attrs={'class': _INPUT}),
            'grado':       forms.TextInput(attrs={'class': _INPUT}),
            'mes_ingreso': forms.Select(attrs={'class': _SELECT}),
            'activo':      forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-colegio-600 border-gray-300 rounded'}),
        }

