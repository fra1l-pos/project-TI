from django.db import models
from django.conf import settings

class Alumno(models.Model):
    padre = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="alumnos", 
        limit_choices_to={'es_padre': True},
        verbose_name="Padre o Apoderado"
    )
    nombres = models.CharField("Nombres", max_length=100)
    apellidos = models.CharField("Apellidos", max_length=100)
    grado = models.CharField("Grado/Sección", max_length=50)
    mes_ingreso = models.IntegerField(
        "Mes de ingreso (1-12)", 
        help_text="Mes en que ingresó el estudiante (ej. 3 para Marzo)",
        choices=[(i, str(i)) for i in range(1, 13)],
        default=3
    )
    activo = models.BooleanField("Activo", default=True)

    class Meta:
        verbose_name = "Alumno"
        verbose_name_plural = "Alumnos"

    def __str__(self):
        return f"{self.apellidos}, {self.nombres} ({self.grado})"
