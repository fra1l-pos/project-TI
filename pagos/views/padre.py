"""Vistas del portal del Padre / Apoderado."""
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.db import IntegrityError, transaction
from django.db.models import Prefetch
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from alumnos.models import Alumno
from pagos.models import PensionMensual
from pagos.forms import PagoForm
from notificaciones.models import Notificacion
from pagos.views import is_padre, MESES_NOMBRES


@login_required
@user_passes_test(is_padre)
def padre_dashboard(request):
    """Portal del padre: información de sus hijos y el historial de
    pensiones y pagos. Por defecto muestra el año escolar más reciente,
    con filtro para cambiar de año o ver todos."""
    hoy = timezone.now().date()
    alumnos = Alumno.objects.filter(padre=request.user).prefetch_related(
        Prefetch(
            'pensiones',
            queryset=PensionMensual.objects.select_related('anio_academico', 'pago')
                                           .order_by('-anio_academico__anio', 'mes'),
        )
    ).order_by('apellidos', 'nombres')

    # Años escolares disponibles para este padre (del más reciente al más antiguo)
    anios_disponibles = sorted(
        {p.anio_academico for a in alumnos for p in a.pensiones.all()},
        key=lambda anio: -anio.anio,
    )

    # Filtro de año: sin parámetro → año más reciente; 'todos' → todos los años
    anio_param = request.GET.get('anio')
    if anio_param == 'todos':
        anio_seleccionado = 'todos'
    elif anio_param and str(anio_param).isdigit():
        anio_id = int(anio_param)
        anio_seleccionado = anio_id if any(a.id == anio_id for a in anios_disponibles) else 'todos'
    else:
        anio_seleccionado = anios_disponibles[0].id if anios_disponibles else 'todos'

    if anio_seleccionado == 'todos':
        filtro_label = 'Todos los años'
    else:
        filtro_label = f"Año {dict((a.id, a.anio) for a in anios_disponibles).get(anio_seleccionado, '')}"

    hijos = []
    total_pendientes = 0
    total_adeudado = 0
    total_pagados = 0

    for alumno in alumnos:
        pensiones = list(alumno.pensiones.all())
        # Aplicar filtro de año (si no es 'todos')
        if anio_seleccionado != 'todos':
            pensiones = [p for p in pensiones if p.anio_academico_id == anio_seleccionado]

        # Agrupar por año académico con estadísticas de avance
        por_anio = {}
        for p in pensiones:
            datos = por_anio.setdefault(p.anio_academico, {
                'anio': p.anio_academico, 'pensiones': [], 'pagados': 0, 'pendientes': 0,
            })
            datos['pensiones'].append(p)
            if p.pagado:
                datos['pagados'] += 1
                total_pagados += 1
            else:
                datos['pendientes'] += 1

        anios = sorted(por_anio.values(), key=lambda d: -d['anio'].anio)
        for d in anios:
            d['total'] = d['pagados'] + d['pendientes']

        pendientes = [p for p in pensiones if not p.pagado]
        deuda_total = sum(p.monto_deuda for p in pendientes)
        total_pendientes += len(pendientes)
        total_adeudado += deuda_total

        hijos.append({
            'alumno': alumno,
            'mes_ingreso_nombre': MESES_NOMBRES.get(alumno.mes_ingreso, str(alumno.mes_ingreso)),
            'anios': anios,
            'pendientes': len(pendientes),
            'deuda_total': deuda_total,
        })

    # Notificaciones del padre (no leídas primero, luego leídas)
    notificaciones = Notificacion.objects.filter(padre=request.user).order_by('leido', '-fecha_envio')[:10]

    return render(request, 'padre/hijos.html', {
        'hijos': hijos,
        'hoy': hoy,
        'anios': anios_disponibles,
        'anio_seleccionado': anio_seleccionado,
        'filtro_label': filtro_label,
        'total_hijos': len(hijos),
        'total_pendientes': total_pendientes,
        'total_adeudado': total_adeudado,
        'total_pagados': total_pagados,
        'notificaciones': notificaciones,
    })


@login_required
@user_passes_test(is_padre)
def pendientes_pago(request):
    """Selección inteligente de pensión: elige el hijo, el año escolar
    (por defecto el más reciente) y el mes pendiente, y continúa al
    formulario de pago."""
    hijos = Alumno.objects.filter(padre=request.user).order_by('apellidos', 'nombres')

    # Estructura de datos para los selects dependientes (Hijo → Año → Mes)
    data = []
    for alumno in hijos:
        pensiones = PensionMensual.objects.filter(
            alumno=alumno, pagado=False
        ).select_related('anio_academico').order_by('-anio_academico__anio', 'mes')
        if not pensiones:
            continue
        por_anio = {}
        for p in pensiones:
            por_anio.setdefault(p.anio_academico, []).append(p)
        data.append({
            'alumno_id': alumno.id,
            'alumno': f'{alumno.apellidos}, {alumno.nombres}',
            'grado': alumno.grado,
            'anios': [
                {
                    'anio_id': anio.id,
                    'anio': anio.anio,
                    'meses': [
                        {
                            'id': p.id,
                            'mes': p.get_mes_display(),
                            'monto': str(p.monto_deuda),
                            'vencimiento': p.fecha_vencimiento.strftime('%d %b %Y'),
                        }
                        for p in pens
                    ],
                }
                for anio, pens in sorted(por_anio.items(), key=lambda kv: -kv[0].anio)
            ],
        })

    # Si ya eligió una pensión (GET ?pension=id), validarla y continuar al pago
    pension_id = request.GET.get('pension')
    if pension_id:
        if str(pension_id).isdigit():
            pension = get_object_or_404(
                PensionMensual.objects.filter(alumno__padre=request.user, pagado=False),
                id=int(pension_id),
            )
            return redirect('registrar_pago', pension_id=pension.id)
        messages.error(request, 'Selección no válida. Elige nuevamente la pensión.')

    return render(request, 'padre/pendientes.html', {
        'data': data,
        'tiene_pendientes': bool(data),
    })


@login_required
@user_passes_test(is_padre)
def registrar_pago(request, pension_id):
    """Formulario de pago para una pensión específica de un hijo del padre."""
    pension = get_object_or_404(
        PensionMensual.objects.select_related('alumno', 'anio_academico'),
        id=pension_id, alumno__padre=request.user,
    )

    if pension.pagado:
        messages.error(request, f'La pensión de {pension.get_mes_display()} de {pension.anio_academico.anio} ya se encuentra pagada.')
        return redirect('pendientes_pago')

    if request.method == 'POST':
        form = PagoForm(request.POST, request.FILES, pension=pension)
        if form.is_valid():
            try:
                with transaction.atomic():
                    pago = form.save(commit=False)
                    pago.pension = pension
                    pago.save()
                    pension.pagado = True
                    pension.save(update_fields=['pagado'])
                    # Confirmación automática al apoderado (C4)
                    nro_operacion = f", N° {pago.numero_operacion}" if pago.numero_operacion else ""
                    Notificacion.objects.create(
                        padre=request.user,
                        titulo='Pago registrado',
                        mensaje=(
                            f'Estimado(a) apoderado(a), su pago de S/ {pago.monto_pagado} '
                            f'({pension.get_mes_display()} {pension.anio_academico.anio}) '
                            f'ha sido registrado correctamente ({pago.get_metodo_pago_display()}{nro_operacion}). '
                            'Gracias por su puntualidad.'
                        ),
                    )
                messages.success(
                    request,
                    f'Pago de S/ {pago.monto_pagado} registrado correctamente '
                    f'({pension.get_mes_display()} {pension.anio_academico.anio}).'
                )
                return redirect('padre_dashboard')
            except IntegrityError:
                # Protección ante doble envío o pago simultáneo (pago es OneToOne)
                messages.error(request, 'Esta pensión ya fue pagada. Verifica tu historial.')
                return redirect('pendientes_pago')
    else:
        form = PagoForm(pension=pension)

    return render(request, 'padre/registrar_pago.html', {'form': form, 'pension': pension})


@login_required
@user_passes_test(is_padre)
@require_POST
def marcar_notificacion_leida(request, notificacion_id):
    """Marca una notificación como leída."""
    notif = get_object_or_404(Notificacion, id=notificacion_id, padre=request.user)
    notif.leido = True
    notif.save(update_fields=['leido'])
    return redirect('padre_dashboard')


@login_required
@user_passes_test(is_padre)
def notificaciones_lista(request):
    """Página dedicada de notificaciones del padre con paginación."""
    notificaciones_qs = Notificacion.objects.filter(padre=request.user).order_by('leido', '-fecha_envio')
    
    # Estadísticas
    total = notificaciones_qs.count()
    no_leidas = notificaciones_qs.filter(leido=False).count()
    leidas = total - no_leidas
    
    # Paginación
    paginator = Paginator(notificaciones_qs, 20)
    page_number = request.GET.get('page')
    notificaciones = paginator.get_page(page_number)
    
    return render(request, 'padre/notificaciones.html', {
        'notificaciones': notificaciones,
        'total': total,
        'no_leidas': no_leidas,
        'leidas': leidas,
    })


@login_required
@user_passes_test(is_padre)
@require_POST
def marcar_todas_leidas(request):
    """Marca todas las notificaciones del padre como leídas."""
    Notificacion.objects.filter(padre=request.user, leido=False).update(leido=True)
    messages.success(request, 'Todas las notificaciones marcadas como leídas.')
    return redirect('notificaciones_lista')
