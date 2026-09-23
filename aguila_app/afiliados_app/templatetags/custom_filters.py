from django import template

from afiliados_app.fotos import obtener_foto_persona

register = template.Library()


@register.filter
def foto_persona(obj):
    return obtener_foto_persona(obj)

@register.filter
def dict_get(d, key):
    try:
        return d.get(key)
    except Exception:
        return ''


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(str(key))  # key convertido a string, pues stock_dict tiene claves string
    except Exception:
        return 0
