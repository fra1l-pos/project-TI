from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from usuarios.models import Usuario
from alumnos.models import Alumno


class Command(BaseCommand):
    help = 'Crea datos iniciales: el administrador y un padre de familia con dos hijos'

    def handle(self, *args, **kwargs):
        # --- Administrador ---
        if not Usuario.objects.filter(username='admin').exists():
            Usuario.objects.create_superuser(
                'admin', 'admin@colegio.com', 'admin123',
                es_padre=False, first_name='Admin', last_name='Principal'
            )
            self.stdout.write(self.style.SUCCESS('Administrador creado exitosamente: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('El administrador ya existe en la base de datos.'))

        # --- Padre de familia ---
        padre, creado = Usuario.objects.get_or_create(
            username='padre.ejemplo',
            defaults={
                'first_name': 'Juan',
                'last_name': 'Pérez',
                'email': 'juan.perez@ejemplo.com',
                'telefono': '987654321',
                'es_padre': True,
                'password': make_password('padre123'),
            },
        )
        if creado:
            self.stdout.write(self.style.SUCCESS('Padre creado: padre.ejemplo / padre123'))
        else:
            self.stdout.write(self.style.WARNING('El padre.ejemplo ya existe en la base de datos.'))

        # --- Hijos ---
        hijos = [
            {'nombres': 'Ana', 'apellidos': 'Pérez García', 'grado': '3ro Primaria A', 'mes_ingreso': 3},
            {'nombres': 'Luis', 'apellidos': 'Pérez García', 'grado': '1ro Secundaria B', 'mes_ingreso': 3},
        ]
        for datos in hijos:
            alumno, creado = Alumno.objects.get_or_create(
                padre=padre,
                nombres=datos['nombres'],
                apellidos=datos['apellidos'],
                defaults={
                    'grado': datos['grado'],
                    'mes_ingreso': datos['mes_ingreso'],
                    'activo': True,
                },
            )
            if creado:
                self.stdout.write(self.style.SUCCESS(f'Alumno creado: {alumno}'))
            else:
                self.stdout.write(self.style.WARNING(f'El alumno {alumno} ya existe.'))
