from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Información Adicional', {'fields': ('telefono', 'es_padre')}),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'es_padre')
    list_filter = ('es_padre', 'is_staff', 'is_active')
