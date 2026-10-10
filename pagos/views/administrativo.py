"""Vistas del panel administrativo (personal del colegio)."""
import datetime

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from alumnos.models import Alumno
from pagos.models import Pago, PensionMensual, AnioAcademico
from pagos.forms import AnioAcademicoForm
from pagos.views import is_admin


def anio_filtrado(request):
    """Determina el año escolar a mostrar: por defecto el más reciente.
    Retorna (anio_id —o None para 'todos—, queryset de años)."""
    anios = AnioAcademico.objects.order_by('-anio')
    anio_param = request.GET.get('anio')
    if anio_param == 'todos':
        return None, anios
    if anio_param and str(anio_param).isdigit():
        anio_id = int(anio_param)
        if anios.filter(id=anio_id).exists():
            return anio_id, anios
    # Por defecto: el año escolar más reciente
    return (anios.first().id if anios.exists() else None), anios


@login_required
def admin_dashboard(request):
    # Si un padre llega aquí (ej. tras el login), lo redirigimos a su portal
    if request.user.es_padre:
        return redirect('padre_dashboard')

    anio_id, anios = anio_filtrado(request)

    total_alumnos = Alumno.objects.filter(activo=True).count()
    if anio_id:
        pensiones_pendientes = PensionMensual.objects.filter(anio_academico_id=anio_id, pagado=False).count()
        pagos_recientes = Pago.objects.filter(pension__anio_academico_id=anio_id).order_by('-fecha_registro')[:5]
        anio_label = f"Año {AnioAcademico.objects.get(id=anio_id).anio}"
    else:
        pensiones_pendientes = PensionMensual.objects.filter(pagado=False).count()
        pagos_recientes = Pago.objects.order_by('-fecha_registro')[:5]
        anio_label = 'Todos los años'

    context = {
        'total_alumnos': total_alumnos,
        'pagos_recientes': pagos_recientes,
        'pensiones_pendientes': pensiones_pendientes,
        'anios': anios,
        'anio_seleccionado': anio_id,
        'anio_label': anio_label,
    }
    return render(request, 'administrador/pagos_dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def crear_anio(request):
    if request.method == 'POST':
        form = AnioAcademicoForm(request.POST)
        if form.is_valid():
            anio_obj = form.save()

            # Generar pensiones de Marzo a Diciembre para los alumnos activos
            alumnos_activos = Alumno.objects.filter(activo=True)
            pensiones_creadas = 0
            for alumno in alumnos_activos:
                mes_inicio = max(3, alumno.mes_ingreso)
                for mes in range(mes_inicio, 13):
                    # Día 28 como fecha de vencimiento referencial
                    fecha_venc = datetime.date(anio_obj.anio, mes, 28)
                    _, created = PensionMensual.objects.get_or_create(
                        alumno=alumno,
                        anio_academico=anio_obj,
                        mes=mes,
                        defaults={
                            'monto_deuda': anio_obj.pension_base,
                            'fecha_vencimiento': fecha_venc,
                            'pagado': False
                        }
                    )
                    if created:
                        pensiones_creadas += 1

            if pensiones_creadas > 0:
                messages.success(request, f'¡Año Académico {anio_obj.anio} aperturado con éxito! Se generaron {pensiones_creadas} pensiones para los alumnos activos.')
            else:
                messages.success(request, f'¡Año Académico {anio_obj.anio} aperturado con éxito!')
            # Cargar el panel en el año escolar recién creado (el más reciente)
            return redirect(f"{reverse('admin_dashboard')}?anio={anio_obj.id}")
    else:
        form = AnioAcademicoForm()

    return render(request, 'administrador/pagos_crear_anio.html', {'form': form})


@login_required
@user_passes_test(is_admin)
def pensiones_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)

    # Filtro de año: por defecto el año escolar más reciente
    anio_id, anios = anio_filtrado(request)
    pensiones = PensionMensual.objects.filter(alumno=alumno)
    if anio_id:
        pensiones = pensiones.filter(anio_academico_id=anio_id)
    pensiones = pensiones.select_related('anio_academico').order_by('-anio_academico__anio', 'mes')

    context = {
        'alumno': alumno,
        'pensiones': pensiones,
        'anios': anios,
        'anio_seleccionado': anio_id,
    }
    return render(request, 'administrador/pagos_pensiones.html', context)
