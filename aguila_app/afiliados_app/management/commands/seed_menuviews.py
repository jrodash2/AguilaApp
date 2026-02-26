from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Comando deprecado: control de acceso por vistas fue removido.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('seed_menuviews está deprecado y no realiza acciones.'))
