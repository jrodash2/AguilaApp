import re

from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions

from .models import Afiliado, FotoPersona


def normalizar_dpi(dpi):
    return re.sub(r'\D', '', str(dpi or ''))


def obtener_foto_persona(obj):
    """Resuelve una foto sin duplicarla: objeto, afiliado relacionado, afiliado por DPI y fallback central."""
    foto = getattr(obj, 'foto', None)
    if foto:
        return foto
    afiliado = getattr(obj, 'afiliado', None)
    if afiliado and afiliado.foto:
        return afiliado.foto
    dpi = normalizar_dpi(getattr(obj, 'dpi', None) or getattr(afiliado, 'dpi', None))
    if len(dpi) != 13:
        return None
    afiliado = Afiliado.objects.filter(dpi=dpi).only('foto').first()
    if afiliado and afiliado.foto:
        return afiliado.foto
    registro = FotoPersona.objects.filter(dpi=dpi).only('foto').first()
    return registro.foto if registro else None


def guardar_foto_persona(obj, archivo=None, eliminar=False):
    """Guarda en Afiliado cuando existe; de lo contrario usa el almacén único por DPI."""
    if archivo and archivo.size > 5 * 1024 * 1024:
        raise ValidationError('La fotografía no puede superar 5 MB.')
    afiliado = obj if isinstance(obj, Afiliado) else getattr(obj, 'afiliado', None)
    dpi = normalizar_dpi(getattr(obj, 'dpi', None) or getattr(afiliado, 'dpi', None))
    if not afiliado and len(dpi) == 13:
        afiliado = Afiliado.objects.filter(dpi=dpi).first()
    if afiliado:
        if eliminar and afiliado.foto:
            afiliado.foto.delete(save=False)
            afiliado.foto = None
        if archivo:
            get_image_dimensions(archivo)
            if afiliado.foto:
                afiliado.foto.delete(save=False)
            afiliado.foto = archivo
        if eliminar or archivo:
            afiliado.save(update_fields=['foto'])
        foto_previa = FotoPersona.objects.filter(dpi=dpi).first()
        if foto_previa:
            foto_previa.foto.delete(save=False)
            foto_previa.delete()
        return afiliado.foto
    if len(dpi) != 13:
        if archivo:
            raise ValidationError('Se requiere un DPI válido para guardar la fotografía.')
        return None
    registro = FotoPersona.objects.filter(dpi=dpi).first()
    if eliminar:
        if registro:
            registro.foto.delete(save=False)
            registro.delete()
        return None
    if archivo:
        get_image_dimensions(archivo)
        registro, _ = FotoPersona.objects.get_or_create(dpi=dpi, defaults={'foto': archivo})
        if registro.foto != archivo:
            if registro.foto:
                registro.foto.delete(save=False)
            registro.foto = archivo
            registro.save(update_fields=['foto', 'fecha_actualizacion'])
        return registro.foto
    return registro.foto if registro else None


def asignar_fotos_personas(objetos):
    """Resuelve fotos de un listado con dos consultas como máximo, evitando N+1."""
    objetos = list(objetos)
    dpis = {normalizar_dpi(getattr(obj, 'dpi', None)) for obj in objetos}
    dpis.discard('')
    afiliados = {
        normalizar_dpi(item.dpi): item.foto
        for item in Afiliado.objects.filter(dpi__in=dpis).only('dpi', 'foto')
        if item.foto
    }
    fotos = {
        item.dpi: item.foto
        for item in FotoPersona.objects.filter(dpi__in=dpis.difference(afiliados)).only('dpi', 'foto')
    }
    for obj in objetos:
        dpi = normalizar_dpi(getattr(obj, 'dpi', None))
        obj.foto_resuelta = getattr(obj, 'foto', None) or afiliados.get(dpi) or fotos.get(dpi)
    return objetos
