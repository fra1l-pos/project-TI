from django.contrib import admin
from .models import Alumno

@admin.register(Alumno)
class AlumnoAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'grado', 'padre', 'mes_ingreso', 'activo')
    list_filter = ('activo', 'grado', 'mes_ingreso')
    search_fields = ('apellidos', 'nombres', 'padre__username', 'padre__first_name', 'padre__last_name')
