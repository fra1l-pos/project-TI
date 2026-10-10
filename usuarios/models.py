from django.db import models
from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    telefono = models.CharField("Teléfono", max_length=20, blank=True, null=True, help_text="Número de celular para WhatsApp")
    es_padre = models.BooleanField("Es Padre/Apoderado", default=False, help_text="Indica si este usuario es un padre de familia")
    
    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
    
    def __str__(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    @property
    def notificaciones_no_leidas_count(self):
        """Cuenta las notificaciones no leídas del usuario."""
        if self.es_padre:
            from notificaciones.models import Notificacion
            return Notificacion.objects.filter(padre=self, leido=False).count()
        return 0
