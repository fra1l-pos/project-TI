from django.db import models
from django.conf import settings

class Notificacion(models.Model):
    padre = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="notificaciones",
        verbose_name="Padre/Apoderado"
    )
    titulo = models.CharField("Título", max_length=200)
    mensaje = models.TextField("Mensaje")
    leido = models.BooleanField("Leído", default=False)
    fecha_envio = models.DateTimeField("Fecha de envío", auto_now_add=True)

    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-fecha_envio']

    def __str__(self):
        return f"{self.titulo} para {self.padre}"
