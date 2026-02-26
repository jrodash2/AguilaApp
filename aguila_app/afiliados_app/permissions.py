from django.contrib.auth.decorators import login_required


def require_perms(_perms, any_of=False):
    """Compatibilidad: sin bloqueo por permisos, solo autenticación."""

    def decorator(view_func):
        return login_required(view_func)

    return decorator


def require_group(_groups):
    """Compatibilidad: sin bloqueo por grupos, solo autenticación."""

    def decorator(view_func):
        return login_required(view_func)

    return decorator
