from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def permission_required_or_403(permission_codename):
    """Protege una vista por permiso de Django y responde 403 real."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.has_perm(permission_codename):
                return view_func(request, *args, **kwargs)
            raise PermissionDenied

        return _wrapped

    return decorator


def in_any_group(user, *group_names):
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name__in=group_names).exists()
