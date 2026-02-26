# context_processors.py
import random

from .access import user_has_view
from .models import FraseMotivacional, Institucion, MenuView


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


def allowed_menu_keys(request):
    if not request.user.is_authenticated:
        return {'allowed_menu_keys': set()}

    if request.user.is_superuser or request.user.groups.filter(name='Administrador').exists():
        keys = set(MenuView.objects.filter(is_active=True).values_list('key', flat=True))
        return {'allowed_menu_keys': keys}

    keys = {
        key for key in MenuView.objects.filter(is_active=True).values_list('key', flat=True)
        if user_has_view(request.user, key)
    }
    return {'allowed_menu_keys': keys}
