from django.contrib.auth.decorators import login_required


def grupo_requerido(*_nombres_grupos):
    """Compatibilidad: sin bloqueo por grupo, solo requiere login."""

    def decorador(view_func):
        return login_required(view_func)

    return decorador
