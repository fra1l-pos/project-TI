from django.urls import path
from pagos.views import administrativo, padre

urlpatterns = [
    # ── Administrativo ──────────────────────────────────────────
    path('', administrativo.admin_dashboard, name='admin_dashboard'),
    path('anio/crear/', administrativo.crear_anio, name='crear_anio'),
    path('pensiones/alumno/<int:alumno_id>/', administrativo.pensiones_alumno, name='pensiones_alumno'),
    path('notificacion/enviar/', administrativo.enviar_notificacion, name='enviar_notificacion'),

    # ── Portal del Padre / Apoderado ────────────────────────────
    path('mis-hijos/', padre.padre_dashboard, name='padre_dashboard'),
    path('pendientes/', padre.pendientes_pago, name='pendientes_pago'),
    path('pagar/<int:pension_id>/', padre.registrar_pago, name='registrar_pago'),
    path('notificaciones/', padre.notificaciones_lista, name='notificaciones_lista'),
    path('notificaciones/todas-leidas/', padre.marcar_todas_leidas, name='marcar_todas_leidas'),
    path('notificacion/leida/<int:notificacion_id>/', padre.marcar_notificacion_leida, name='marcar_leida_notificacion'),
]
