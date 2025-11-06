from django.apps import AppConfig

class afiliadosAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'afiliados_app'

    # def ready(self):
    #     import afiliados_app.signals  # 👈 importa tus signals aquí
