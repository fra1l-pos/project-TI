from django.urls import path
from alumnos.views import administrativo

urlpatterns = [
    path('', administrativo.lista_alumnos, name='lista_alumnos'),
    path('crear/', administrativo.crear_alumno, name='crear_alumno'),
    path('editar/<int:id>/', administrativo.editar_alumno, name='editar_alumno'),
    path('carga-masiva/', administrativo.carga_masiva_alumnos, name='carga_masiva_alumnos'),
    path('descargar-plantilla/', administrativo.descargar_plantilla_excel, name='descargar_plantilla_excel'),
    path('api/buscar-apoderado/', administrativo.buscar_apoderado_por_dni, name='buscar_apoderado_por_dni'),
]