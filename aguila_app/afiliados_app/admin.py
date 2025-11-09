from django.contrib import admin
from .models import (
    Institucion, Perfil, FraseMotivacional,
    Comunidad, CentroVotacion, Comision, Afiliado
)

# -------------------------------
# Admin para Institucion
# -------------------------------
class InstitucionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'direccion', 'telefono')
    search_fields = ('nombre', 'direccion')

admin.site.register(Institucion, InstitucionAdmin)

# -------------------------------
# Admin para Perfil
# -------------------------------
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('user', 'cargo')
    search_fields = ('user__username', 'cargo')

admin.site.register(Perfil, PerfilAdmin)

# -------------------------------
# Admin para FraseMotivacional
# -------------------------------
class FraseMotivacionalAdmin(admin.ModelAdmin):
    list_display = ('frase', 'personaje')
    search_fields = ('frase', 'personaje')
    ordering = ('personaje',)

admin.site.register(FraseMotivacional, FraseMotivacionalAdmin)

# -------------------------------
# Admin para Comunidad
# -------------------------------
class ComunidadAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',)

admin.site.register(Comunidad, ComunidadAdmin)

# -------------------------------
# Admin para Centro de Votacion
# -------------------------------
class CentroVotacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'ubicacion')
    search_fields = ('nombre', 'ubicacion')

admin.site.register(CentroVotacion, CentroVotacionAdmin)

# -------------------------------
# Admin para Comision
# -------------------------------
class ComisionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)

admin.site.register(Comision, ComisionAdmin)


# -------------------------------
# Admin para Afiliado
# -------------------------------
class AfiliadoAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'dpi', 'comunidad','centro_votacion', 'empadronado', 'comisiones_list')
    search_fields = ('nombre_completo', 'dpi', 'comunidad__nombre', 'centro_votacion__nombre')
    list_filter = ('empadronado', 'comunidad','centro_votacion')
    filter_horizontal = ('comisiones',)

    def comisiones_list(self, obj):
        return ", ".join([c.nombre for c in obj.comisiones.all()])
    comisiones_list.short_description = 'Comisiones'

admin.site.register(Afiliado, AfiliadoAdmin)
