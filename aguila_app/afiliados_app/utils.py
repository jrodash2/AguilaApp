from functools import wraps
import re


def normalizar_dpi(valor):
    """Convierte espacios/guiones de un DPI válido a su forma de 13 dígitos."""
    valor_texto = str(valor or "")
    if re.search(r"[^\d\s-]", valor_texto):
        return ""
    return re.sub(r"\D", "", valor_texto)


def grupo_requerido(*_nombres_grupos):
    """Decorador deprecated: mantiene compatibilidad sin bloquear acceso por grupos."""
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorador
