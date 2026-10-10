from django.urls import path
from pagos.views import administrativo, padre

urlpatterns = [
    # ── Administrativo ──────────────────────────────────────────
    path('anio/crear/', administrativo.crear_anio, name='crear_anio'),
    path('pensiones/alumno/<int:alumno_id>/', administrativo.pensiones_alumno, name='pensiones_alumno'),

    # ── Portal del Padre / Apoderado ────────────────────────────
    path('mis-hijos/', padre.padre_dashboard, name='padre_dashboard'),
    path('pendientes/', padre.pendientes_pago, name='pendientes_pago'),
    path('pagar/<int:pension_id>/', padre.registrar_pago, name='registrar_pago'),
]
