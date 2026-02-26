"""Módulo de acceso por vistas desactivado (deprecated)."""


def user_has_view(user, key):
    return True


def vista_requerida(_key):
    def wrapper(view_func):
        return view_func
    return wrapper
