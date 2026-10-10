from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from alumnos.models import Alumno
from pagos.models import Pago, PensionMensual, AnioAcademico
from .forms import AnioAcademicoForm

def is_admin(user):
    return user.is_authenticated and not user.es_padre

@login_required
@user_passes_test(is_admin)
def admin_dashboard(request):
    total_alumnos = Alumno.objects.filter(activo=True).count()
    pagos_recientes = Pago.objects.order_by('-fecha_registro')[:5]
    pensiones_pendientes = PensionMensual.objects.filter(pagado=False).count()
    
    context = {
        'total_alumnos': total_alumnos,
        'pagos_recientes': pagos_recientes,
        'pensiones_pendientes': pensiones_pendientes,
    }
    return render(request, 'pagos/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def crear_anio(request):
    if request.method == 'POST':
        form = AnioAcademicoForm(request.POST)
        if form.is_valid():
            anio_obj = form.save()
            
            # Generar pensiones de Marzo a Diciembre para los alumnos activos
            import datetime
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
            return redirect('lista_alumnos')
    else:
        form = AnioAcademicoForm()
    
    return render(request, 'pagos/crear_anio.html', {'form': form})

@login_required
@user_passes_test(is_admin)
def pensiones_alumno(request, alumno_id):
    alumno = get_object_or_404(Alumno, id=alumno_id)
    pensiones = PensionMensual.objects.filter(alumno=alumno).order_by('-anio_academico__anio', 'mes')
    
    context = {
        'alumno': alumno,
        'pensiones': pensiones,
    }
    return render(request, 'pagos/pensiones.html', context)
