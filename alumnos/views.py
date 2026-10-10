from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Alumno
from pagos.models import AnioAcademico
from .forms import AlumnoForm

def is_admin(user):
    return user.is_authenticated and not user.es_padre

@login_required
@user_passes_test(is_admin)
def lista_alumnos(request):
    anio_reciente = AnioAcademico.objects.order_by('-anio').first()
    alumnos = Alumno.objects.all().order_by('grado', 'apellidos')
    context = {
        'alumnos': alumnos,
        'anio_reciente': anio_reciente,
    }
    return render(request, 'alumnos/lista.html', context)

@login_required
@user_passes_test(is_admin)
def crear_alumno(request):
    if request.method == 'POST':
        form = AlumnoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Alumno registrado correctamente.')
            return redirect('lista_alumnos')
    else:
        form = AlumnoForm()
    return render(request, 'alumnos/form.html', {'form': form, 'titulo': 'Registrar Alumno'})

@login_required
@user_passes_test(is_admin)
def editar_alumno(request, id):
    alumno = get_object_or_404(Alumno, id=id)
    if request.method == 'POST':
        form = AlumnoForm(request.POST, instance=alumno)
        if form.is_valid():
            form.save()
            messages.success(request, 'Datos del alumno actualizados.')
            return redirect('lista_alumnos')
    else:
        form = AlumnoForm(instance=alumno)
    return render(request, 'alumnos/form.html', {'form': form, 'titulo': 'Editar Alumno'})
