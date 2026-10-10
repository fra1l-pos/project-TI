from django import forms
from .models import AnioAcademico

class AnioAcademicoForm(forms.ModelForm):
    class Meta:
        model = AnioAcademico
        fields = ['anio', 'pension_base']
        widgets = {
            'anio': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500'}),
            'pension_base': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-colegio-500 focus:border-colegio-500', 'step': '0.01'}),
        }
