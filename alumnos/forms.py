from django import forms
from .models import Alumno

class AlumnoForm(forms.ModelForm):
    class Meta:
        model = Alumno
        fields = ['padre', 'nombres', 'apellidos', 'grado', 'mes_ingreso', 'activo']
        widgets = {
            'padre': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'nombres': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'apellidos': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'grado': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'mes_ingreso': forms.Select(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'activo': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-colegio-600 focus:ring-colegio-500 border-gray-300 rounded'}),
        }
