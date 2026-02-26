from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando deprecado: setup de vistas por grupo fue removido.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('setup_roles está deprecado y no realiza acciones.'))
