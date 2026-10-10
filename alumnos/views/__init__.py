"""Utilidades compartidas entre las vistas de alumnos."""

def is_admin(user):
    return user.is_authenticated and not user.es_padre
