from django.contrib.auth.decorators import login_required

from .models import GroupMenuView


def user_has_view(user, key):
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.groups.filter(name='Administrador').exists():
        return True
    return GroupMenuView.objects.filter(group__in=user.groups.all(), view__key=key, view__is_active=True).exists()


def vista_requerida(_key):
    """Compatibilidad: ya no restringe por key, solo exige autenticación."""

    def decorator(view_func):
        return login_required(view_func)

    return decorator
