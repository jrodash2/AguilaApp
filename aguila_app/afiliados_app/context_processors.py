import random

from django.conf import settings

from .access import user_has_view
from .models import FraseMotivacional, Institucion, MenuView


MENU_KEYS_FALLBACK = {
    'dashboard',
    'afiliados',
    'lideres',
    'comunidades',
    'sectores',
    'centros',
    'comisiones',
    'elecciones_2023',
    'filtros',
    'cargar_padron',
    'configuracion',
    'usuarios',
    'gestor_vistas',
}


def frase_del_dia(request):
    frases = FraseMotivacional.objects.all()
    frase = random.choice(frases) if frases.exists() else None
    return {'frase_del_dia': frase}


def grupo_usuario(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'es_departamento': request.user.groups.filter(name='Departamento').exists(),
        'es_administrador': request.user.groups.filter(name='Administrador').exists(),
        'es_afiliados': request.user.groups.filter(name='afiliados').exists(),
    }


def datos_institucion(request):
    institucion = Institucion.objects.first()
    return {'institucion': institucion}


def menu_access(request):
    if not request.user.is_authenticated:
        return {'es_admin': False, 'allowed_menu_keys': set(), 'debug': settings.DEBUG}

    es_admin = request.user.groups.filter(name='Administrador').exists() or request.user.is_superuser

    active_keys = set(MenuView.objects.filter(is_active=True).values_list('key', flat=True))

    if es_admin:
        # Admin siempre ve todo: catálogo activo o fallback completo.
        allowed_keys = active_keys if active_keys else set(MENU_KEYS_FALLBACK)
        return {'es_admin': True, 'allowed_menu_keys': allowed_keys, 'debug': settings.DEBUG}

    if active_keys:
        allowed_keys = {key for key in active_keys if user_has_view(request.user, key)}
    else:
        # Fallback mínimo para no-admin cuando no hay catálogo.
        allowed_keys = {'dashboard', 'filtros'}

    return {'es_admin': False, 'allowed_menu_keys': allowed_keys, 'debug': settings.DEBUG}
