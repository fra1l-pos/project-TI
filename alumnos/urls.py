from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_alumnos, name='lista_alumnos'),
    path('crear/', views.crear_alumno, name='crear_alumno'),
    path('editar/<int:id>/', views.editar_alumno, name='editar_alumno'),
    path('carga-masiva/', views.carga_masiva_alumnos, name='carga_masiva_alumnos'),
    path('descargar-plantilla/', views.descargar_plantilla_excel, name='descargar_plantilla_excel'),
    path('api/buscar-apoderado/', views.buscar_apoderado_por_dni, name='buscar_apoderado_por_dni'),
]


