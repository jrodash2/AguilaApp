from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse

from .models import GroupMenuView, MenuView


def user_has_view(user, key):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name='Administrador').exists():
        return True
    return GroupMenuView.objects.filter(group__in=user.groups.all(), view__key=key, view__is_active=True).exists()


def vista_requerida(key):
    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if user_has_view(request.user, key):
                return view_func(request, *args, **kwargs)

            view_obj = MenuView.objects.filter(key=key).first()
            request.session['access_denied_view_key'] = key
            request.session['access_denied_view_label'] = view_obj.label if view_obj else key
            request.session['access_denied_next'] = request.get_full_path()
            return redirect(reverse('afiliados:no_autorizado'))

        return _wrapped

    return decorator
