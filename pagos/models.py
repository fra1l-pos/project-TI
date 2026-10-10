from django.db import models
from alumnos.models import Alumno

class AnioAcademico(models.Model):
    anio = models.IntegerField("Año Académico", unique=True, help_text="Ej: 2026")
    pension_base = models.DecimalField("Pensión mensual base", max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Año Académico"
        verbose_name_plural = "Años Académicos"

    def __str__(self):
        return f"Año {self.anio}"

class PensionMensual(models.Model):
    MESES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre')
    ]
    alumno = models.ForeignKey(Alumno, on_delete=models.CASCADE, related_name="pensiones", verbose_name="Alumno")
    anio_academico = models.ForeignKey(AnioAcademico, on_delete=models.CASCADE, verbose_name="Año Académico")
    mes = models.IntegerField("Mes", choices=MESES)
    monto_deuda = models.DecimalField("Monto a pagar", max_digits=10, decimal_places=2)
    fecha_vencimiento = models.DateField("Fecha de vencimiento")
    pagado = models.BooleanField("Pagado", default=False)

    class Meta:
        unique_together = ('alumno', 'anio_academico', 'mes')
        ordering = ['anio_academico', 'mes']
        verbose_name = "Pensión Mensual"
        verbose_name_plural = "Pensiones Mensuales"

    def __str__(self):
        return f"{self.get_mes_display()} {self.anio_academico.anio} - {self.alumno}"

class Pago(models.Model):
    METODOS_PAGO = [
        ('EFECTIVO', 'Efectivo'),
        ('YAPE_PLIN', 'Yape / Plin'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
    ]
    pension = models.OneToOneField(PensionMensual, on_delete=models.CASCADE, related_name="pago", verbose_name="Pensión correspondiente")
    monto_pagado = models.DecimalField("Monto pagado", max_digits=10, decimal_places=2)
    fecha_registro = models.DateTimeField("Fecha de registro", auto_now_add=True)
    metodo_pago = models.CharField("Método de pago", max_length=50, choices=METODOS_PAGO)
    numero_operacion = models.CharField("Número de operación", max_length=100, blank=True, null=True, help_text="Obligatorio para Yape/Plin o Transferencia")
    comprobante = models.FileField("Comprobante (Imagen/PDF)", upload_to='comprobantes/', blank=True, null=True, help_text="Sube la captura de Yape/Plin o el voucher")

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago de {self.pension} ({self.monto_pagado})"
