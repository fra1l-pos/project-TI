from django.core.management.base import BaseCommand
from usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Crea el usuario administrador por defecto'

    def handle(self, *args, **kwargs):
        if not Usuario.objects.filter(username='admin').exists():
            Usuario.objects.create_superuser('admin', 'admin@colegio.com', 'admin123', es_padre=False, first_name='Admin', last_name='Principal')
            self.stdout.write(self.style.SUCCESS('Administrador creado exitosamente: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('El administrador ya existe en la base de datos.'))
