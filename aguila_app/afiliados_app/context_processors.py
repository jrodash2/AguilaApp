# context_processors.py
from .models import FraseMotivacional
import random

def frase_del_dia(request):
    # Obtener todas las frases
    frases = FraseMotivacional.objects.all()
    
    # Verificar si hay frases disponibles
    if frases.exists():
        frase = random.choice(frases)
    else:
        # Si no hay frases, puedes devolver un valor predeterminado o None
        frase = None
    
    return {
        'frase_del_dia': frase
    }

def grupo_usuario(request):
    is_authenticated = bool(getattr(request, 'user', None) and request.user.is_authenticated)

    return {
        'es_gestor': request.user.groups.filter(name='Gestor').exists() if is_authenticated else False,
        'es_administrador': request.user.groups.filter(name='Administrador').exists() if is_authenticated else False,
        'es_departamento': request.user.groups.filter(name='Departamento').exists() if is_authenticated else False,
        'es_afiliados': request.user.groups.filter(name='afiliados').exists() if is_authenticated else False,
        'es_organizacion': request.user.groups.filter(name='Organizacion').exists() if is_authenticated else False,
        'es_juventud': request.user.groups.filter(name='Jovenes').exists() if is_authenticated else False,
        'es_mujeres': request.user.groups.filter(name='Mujeres').exists() if is_authenticated else False,
        'es_logistica': request.user.groups.filter(name='Logistica').exists() if is_authenticated else False,
    }


from .models import Institucion

def datos_institucion(request):
    try:
        institucion = Institucion.objects.first()
    except Institucion.DoesNotExist:
        institucion = None

    return {
        'institucion': institucion
    }
