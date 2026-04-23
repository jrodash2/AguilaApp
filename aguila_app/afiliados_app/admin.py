from django.contrib import admin
from .models import (
    Institucion, Perfil, FraseMotivacional,
    Comunidad, CentroVotacion, Comision, Afiliado, Sector, OrganizacionIntegrante,
    CoordinadorOrganizacion, LiderComunitarioOrganizacion, EstructuraOrganizativa,
    ResponsableTerritorial, ReunionTerritorial, IncidenciaTerritorial,
    LogisticaIntegrante, CoordinadorLogistica, LiderLogistica, EstructuraLogistica,
    ResponsableLogistica, ReunionLogistica, IncidenciaLogistica, RecursoLogistico,
    AsignacionLogistica, SolicitudLogistica, EntregaLogistica, AgendaLogistica
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

@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Comunidad)
class ComunidadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'sector')
    list_filter = ('sector',)
    search_fields = ('nombre',)

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


@admin.register(OrganizacionIntegrante)
class OrganizacionIntegranteAdmin(admin.ModelAdmin):
    list_display = ('afiliado', 'estado', 'usuario_registro', 'usuario_modificacion', 'fecha_creacion')
    search_fields = ('afiliado__nombre_completo', 'afiliado__dpi', 'usuario_registro__username')
    list_filter = ('estado', 'fecha_creacion')


admin.site.register(CoordinadorOrganizacion)
admin.site.register(LiderComunitarioOrganizacion)
admin.site.register(EstructuraOrganizativa)
admin.site.register(ResponsableTerritorial)
admin.site.register(ReunionTerritorial)
admin.site.register(IncidenciaTerritorial)
admin.site.register(LogisticaIntegrante)
admin.site.register(CoordinadorLogistica)
admin.site.register(LiderLogistica)
admin.site.register(EstructuraLogistica)
admin.site.register(ResponsableLogistica)
admin.site.register(ReunionLogistica)
admin.site.register(IncidenciaLogistica)
admin.site.register(RecursoLogistico)
admin.site.register(AsignacionLogistica)
admin.site.register(SolicitudLogistica)
admin.site.register(EntregaLogistica)
admin.site.register(AgendaLogistica)
