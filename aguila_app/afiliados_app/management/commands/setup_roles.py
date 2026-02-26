from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from afiliados_app.models import GroupMenuView, MenuView


DEFAULT_BY_GROUP = {
    'Administrador': '__all__',
    'Gestor': {'dashboard', 'filtros', 'afiliados', 'lideres', 'comunidades', 'sectores', 'centros', 'comisiones'},
    'afiliados': {'dashboard', 'filtros', 'afiliados', 'lideres', 'comunidades', 'sectores', 'centros', 'comisiones'},
    'Coordinador': {'dashboard', 'filtros'},
    'Digitador': {'dashboard', 'filtros', 'afiliados'},
    'Consulta': {'dashboard', 'filtros'},
}


class Command(BaseCommand):
    help = 'Crea/actualiza grupos base y sincroniza vistas habilitadas por grupo (idempotente).'

    def handle(self, *args, **options):
        for group_name in DEFAULT_BY_GROUP.keys():
            group, _ = Group.objects.get_or_create(name=group_name)
            keys = DEFAULT_BY_GROUP[group_name]

            if keys == '__all__':
                views = MenuView.objects.filter(is_active=True)
            else:
                views = MenuView.objects.filter(key__in=keys, is_active=True)

            GroupMenuView.objects.filter(group=group).exclude(view__in=views).delete()
            for mv in views:
                GroupMenuView.objects.get_or_create(group=group, view=mv)

            self.stdout.write(self.style.SUCCESS(f'Grupo {group_name} sincronizado con {views.count()} vistas.'))

        self.stdout.write(self.style.SUCCESS('setup_roles ejecutado correctamente.'))
