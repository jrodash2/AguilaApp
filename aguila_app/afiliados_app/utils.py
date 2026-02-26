from functools import wraps


def grupo_requerido(*_nombres_grupos):
    """Decorador deprecated: mantiene compatibilidad sin bloquear acceso por grupos."""
    def decorador(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorador
