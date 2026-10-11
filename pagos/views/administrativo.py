"""Vistas del panel administrativo (personal del colegio)."""
import datetime
import json

from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import JsonResponse
from django.db.models import Q, Count, Sum

from alumnos.models import Alumno
from usuarios.models import Usuario
from pagos.models import Pago, PensionMensual, AnioAcademico
from pagos.forms import AnioAcademicoForm
from notificaciones.models import Notificacion
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

    pendientes = PensionMensual.objects.filter(pagado=False)
    if anio_id:
        pendientes = pendientes.filter(anio_academico_id=anio_id)
        pagos_recientes = Pago.objects.filter(pension__anio_academico_id=anio_id).order_by('-fecha_registro')[:5]
        anio_label = f"Año {AnioAcademico.objects.get(id=anio_id).anio}"
    else:
        pagos_recientes = Pago.objects.order_by('-fecha_registro')[:5]
        anio_label = 'Todos los años'

    pensiones_pendientes = pendientes.count()
    alumnos_con_deuda = pendientes.values('alumno').distinct().count()

    context = {
        'total_alumnos': total_alumnos,
        'pagos_recientes': pagos_recientes,
        'pensiones_pendientes': pensiones_pendientes,
        'alumnos_con_deuda': alumnos_con_deuda,
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


@login_required
@user_passes_test(is_admin)
def deudores(request):
    """Listado de alumnos con cuotas impagas (morosos) del año seleccionado.

    Solo lectura: agrupa las pensiones no pagadas por alumno y muestra cuántas
    cuotas debe y el monto total, ordenado de mayor a menor deuda."""
    anio_id, anios = anio_filtrado(request)

    pendientes = PensionMensual.objects.filter(pagado=False)
    if anio_id:
        pendientes = pendientes.filter(anio_academico_id=anio_id)

    filas = (pendientes
             .values('alumno')
             .annotate(n_cuotas=Count('id'), total=Sum('monto_deuda'))
             .order_by('-total'))

    alumnos = {
        a.id: a
        for a in Alumno.objects.filter(id__in=[f['alumno'] for f in filas]).select_related('padre')
    }
    deudas = [
        {'alumno': alumnos[f['alumno']], 'n_cuotas': f['n_cuotas'], 'total': f['total']}
        for f in filas if f['alumno'] in alumnos
    ]

    if anio_id:
        anio_label = f"Año {AnioAcademico.objects.get(id=anio_id).anio}"
    else:
        anio_label = 'Todos los años'

    context = {
        'deudas': deudas,
        'anios': anios,
        'anio_seleccionado': anio_id,
        'anio_label': anio_label,
        'total_alumnos_deuda': len(deudas),
        'total_general': sum((d['total'] for d in deudas), 0),
    }
    return render(request, 'administrador/pagos_deudores.html', context)


@login_required
@user_passes_test(is_admin)
def enviar_notificacion(request):
    """Envía notificaciones a los padres/apoderados."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            destinatarios = data.get('destinatarios', 'todos')  # 'todos' o 'seleccionados'
            padres_ids = data.get('padres_ids', [])
            titulo = data.get('titulo', '').strip()
            mensaje = data.get('mensaje', '').strip()
            
            if not titulo or not mensaje:
                return JsonResponse({'success': False, 'error': 'Título y mensaje son obligatorios.'})
            
            # Determinar destinatarios
            if destinatarios == 'todos':
                padres = Usuario.objects.filter(es_padre=True)
            else:
                padres = Usuario.objects.filter(id__in=padres_ids, es_padre=True)
            
            if not padres.exists():
                return JsonResponse({'success': False, 'error': 'No hay destinatarios válidos.'})
            
            # Crear notificaciones
            notificaciones_creadas = 0
            for padre in padres:
                Notificacion.objects.create(
                    padre=padre,
                    titulo=titulo,
                    mensaje=mensaje
                )
                notificaciones_creadas += 1
            
            return JsonResponse({
                'success': True,
                'mensaje': f'Se enviaron {notificaciones_creadas} notificación(es).'
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Datos inválidos.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # GET: devolver lista de padres para el modal
    if request.method == 'GET':
        padres = Usuario.objects.filter(es_padre=True).values('id', 'username', 'first_name', 'last_name', 'telefono')
        return JsonResponse({'padres': list(padres)})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido.'})
