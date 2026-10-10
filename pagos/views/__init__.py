"""Utilidades compartidas entre las vistas de pagos."""

def is_admin(user):
    return user.is_authenticated and not user.es_padre

def is_padre(user):
    return user.is_authenticated and user.es_padre

MESES_NOMBRES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}
