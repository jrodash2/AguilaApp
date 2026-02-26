from django.core.management.base import BaseCommand

from afiliados_app.models import MenuView


MENU_ITEMS = [
    {'key': 'dashboard', 'label': 'Dashboard', 'url_name': 'afiliados:dahsboard', 'section': 'Principal'},
    {'key': 'filtros', 'label': 'Filtros', 'url_name': 'afiliados:dashboard_filtros', 'section': 'Principal'},
    {'key': 'afiliados', 'label': 'Afiliados', 'url_name': 'afiliados:afiliado_lista', 'section': 'Afiliación'},
    {'key': 'lideres', 'label': 'Líderes', 'url_name': 'afiliados:lideres_lista', 'section': 'Afiliación'},
    {'key': 'comunidades', 'label': 'Comunidades', 'url_name': 'afiliados:comunidad_lista', 'section': 'Catálogos'},
    {'key': 'sectores', 'label': 'Sectores', 'url_name': 'afiliados:sector_lista', 'section': 'Catálogos'},
    {'key': 'centros', 'label': 'Centros de Votación', 'url_name': 'afiliados:centro_lista', 'section': 'Catálogos'},
    {'key': 'comisiones', 'label': 'Comisiones', 'url_name': 'afiliados:comision_lista', 'section': 'Catálogos'},
    {'key': 'elecciones_2023', 'label': 'Elecciones 2023', 'url_name': 'afiliados:elecciones2023', 'section': 'Electoral'},
    {'key': 'cargar_padron', 'label': 'Cargar Padrón', 'url_name': 'afiliados:padron_cargar', 'section': 'Electoral'},
    {'key': 'configuracion', 'label': 'Configuración', 'url_name': 'afiliados:editar_institucion', 'section': 'Administración'},
    {'key': 'usuarios', 'label': 'Usuarios', 'url_name': 'afiliados:user_create', 'section': 'Administración'},
    {'key': 'gestor_vistas', 'label': 'Gestor de Vistas', 'url_name': 'afiliados:gestor_vistas', 'section': 'Administración'},
]


class Command(BaseCommand):
    help = 'Crea/actualiza el catálogo MenuView para control de acceso por vistas.'

    def handle(self, *args, **options):
        created_count = 0
        updated_count = 0

        for item in MENU_ITEMS:
            _, created = MenuView.objects.update_or_create(
                key=item['key'],
                defaults={
                    'label': item['label'],
                    'url_name': item['url_name'],
                    'section': item.get('section'),
                    'is_active': True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seed completado. Creadas: {created_count} | Actualizadas: {updated_count} | Total catálogo: {len(MENU_ITEMS)}'
        ))
