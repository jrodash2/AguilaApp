from django.contrib import admin
from .models import (
    Institucion, Perfil, FraseMotivacional
)


# Admin para Institucion
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono')
    search_fields = ('nombre', 'direccion')

admin.site.register(Institucion, InstitucionAdmin)

# Admin para Perfil
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user',)
    search_fields = ('user__username',)

admin.site.register(Perfil, PerfilAdmin)


# Admin para FraseMotivacional
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')
    search_fields = ('frase', 'personaje')
    ordering = ('personaje',)

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)