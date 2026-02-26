from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse


def _store_access_denied_context(request, perms=None, groups=None):
    request.session['access_denied_required_perms'] = perms or []
    request.session['access_denied_required_groups'] = groups or []
    request.session['access_denied_next'] = request.get_full_path()


def require_perms(perms, any_of=False):
    """Requiere uno o varios permisos y redirige a no_autorizado con contexto en sesión."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            checks = [request.user.has_perm(perm) for perm in perms]
            allowed = any(checks) if any_of else all(checks)
            if allowed:
                return view_func(request, *args, **kwargs)

            _store_access_denied_context(request, perms=perms)
            return redirect(reverse('afiliados:no_autorizado'))

        return _wrapped

    return decorator


def require_group(groups):
    """Requiere pertenecer a uno de los grupos indicados."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.groups.filter(name__in=groups).exists():
                return view_func(request, *args, **kwargs)

            _store_access_denied_context(request, groups=groups)
            return redirect(reverse('afiliados:no_autorizado'))

        return _wrapped

    return decorator
