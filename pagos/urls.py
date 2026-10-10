from django.urls import path
from . import views

urlpatterns = [
    path('anio/crear/', views.crear_anio, name='crear_anio'),
    path('pensiones/alumno/<int:alumno_id>/', views.pensiones_alumno, name='pensiones_alumno'),
]
