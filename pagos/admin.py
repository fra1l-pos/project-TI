from django.contrib import admin
from .models import AnioAcademico, PensionMensual, Pago

@admin.register(AnioAcademico)
class AnioAcademicoAdmin(admin.ModelAdmin):
    list_display = ('anio', 'pension_base')

@admin.register(PensionMensual)
class PensionMensualAdmin(admin.ModelAdmin):
    list_display = ('alumno', 'anio_academico', 'mes', 'monto_deuda', 'fecha_vencimiento', 'pagado')
    list_filter = ('pagado', 'anio_academico', 'mes')
    search_fields = ('alumno__apellidos', 'alumno__nombres')

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ('pension', 'monto_pagado', 'fecha_registro', 'metodo_pago')
    list_filter = ('metodo_pago', 'fecha_registro')
