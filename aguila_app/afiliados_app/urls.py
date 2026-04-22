from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


app_name = 'afiliados'

urlpatterns = [
    path('', views.home, name='home'), 
    path('dahsboard/', views.dahsboard, name='dahsboard'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    path("dashboard/", views.dashboard_elecciones, name="dashboard_elecciones"),
    path("dashboard/datos/", views.datos_centro, name="dashboard_datos_centro"),

    path("elecciones/", views.elecciones_dashboard, name="elecciones_dashboard"),

    path("elecciones/centro/<str:centro_codigo>/datos/", views.elecciones_centro_datos, name="elecciones_centro_datos"),

path("filtros/", views.dashboard_filtros, name="dashboard_filtros"),
path("filtros/export/excel/", views.exportar_filtros_excel, name="exportar_filtros_excel"),
path("filtros/export/pdf/", views.exportar_filtros_pdf, name="exportar_filtros_pdf"),
   
    # Usuarios
    path('usuario/crear/', views.user_create, name='user_create'),
    path('usuario/editar/<int:user_id>/', views.user_edit, name='user_edit'),

    path('usuario/eliminar/<int:user_id>/', views.user_delete, name='user_delete'),

    path('editar_institucion/', views.editar_institucion, name='editar_institucion'),
    # Cambiar contraseña
    path('cambiar-contraseña/', auth_views.PasswordChangeView.as_view(
        template_name='afiliados/password_change_form.html',
        success_url='/cambiar-contraseña/hecho/'  # Redirección tras éxito
    ), name='password_change'),

    path('cambiar-contraseña/hecho/', auth_views.PasswordChangeDoneView.as_view(
        template_name='afiliados/password_change_done.html'
    ), name='password_change_done'),
    path('lista/', views.afiliado_lista, name='afiliado_lista'),
    path('nuevo/', views.afiliado_nuevo, name='afiliado_nuevo'),
    path('<int:pk>/editar/', views.afiliado_editar, name='afiliado_editar'),
    path('eliminar/<int:pk>/', views.afiliado_eliminar, name='afiliado_eliminar'),
    path('detalle/<int:pk>/', views.afiliado_detalle, name='afiliado_detalle'),
    path('lideres/', views.lideres_lista, name='lideres_lista'),
    path('<int:pk>/editar-lider/', views.lider_editar, name='lider_editar'),

    # -----------------------
# CRUD Comunidad
# -----------------------
path('comunidades/', views.comunidad_lista, name='comunidad_lista'),
path('comunidades/nuevo/', views.comunidad_nueva, name='comunidad_nueva'),
path('comunidades/editar/<int:pk>/', views.comunidad_editar, name='comunidad_editar'),
path('comunidades/eliminar/<int:pk>/', views.comunidad_eliminar, name='comunidad_eliminar'),

# SECTORES
path('sectores/', views.sector_nueva, name='sector_lista'),
path('sectores/nuevo/', views.sector_nueva, name='sector_nueva'),
path('sectores/editar/<int:pk>/', views.sector_editar, name='sector_editar'),
path('sectores/eliminar/<int:pk>/', views.sector_eliminar, name='sector_eliminar'),


# -----------------------
# CRUD Centro Votacion
# -----------------------
path('centros/', views.centro_lista, name='centro_lista'),
path('centros/nuevo/', views.centro_nuevo, name='centro_nuevo'),
path('centros/editar/<int:pk>/', views.centro_editar, name='centro_editar'),
path('centros/eliminar/<int:pk>/', views.centro_eliminar, name='centro_eliminar'),

# -----------------------
# CRUD Comision
# -----------------------
path('comisiones/', views.comision_lista, name='comision_lista'),
path('comisiones/nuevo/', views.comision_nueva, name='comision_nueva'),
path('comisiones/editar/<int:pk>/', views.comision_editar, name='comision_editar'),
path('comisiones/eliminar/<int:pk>/', views.comision_eliminar, name='comision_eliminar'),

path("api/padron/", views.consultar_padron_local, name="consultar_padron_local"),
path("api/padron/verificar/", views.consultar_padron_local, name="consultar_padron_verificar"),
path("verificar-empadronamiento/", views.verificar_empadronamiento, name="verificar_empadronamiento"),
path('padron/cargar/', views.padron_cargar, name='padron_cargar'),

    # Secretaría de Organización
    path('organizacion/', views.dashboard_organizacion, name='dashboard_organizacion'),
    path('organizacion/dashboard/', views.dashboard_organizacion, name='dashboard_organizacion_home'),
    path('organizacion/integrantes/', views.lista_integrantes_organizacion, name='lista_integrantes_organizacion'),
    path('organizacion/integrantes/crear/', views.crear_integrante_organizacion, name='crear_integrante_organizacion'),
    path('organizacion/integrantes/<int:pk>/', views.detalle_integrante_organizacion, name='detalle_integrante_organizacion'),
    path('organizacion/integrantes/<int:pk>/editar/', views.editar_integrante_organizacion, name='editar_integrante_organizacion'),
    path('organizacion/integrantes/<int:pk>/estado/', views.cambiar_estado_organizacion, name='cambiar_estado_organizacion'),
    path('organizacion/buscar-dpi/', views.buscar_por_dpi_organizacion, name='buscar_por_dpi_organizacion'),
    path('organizacion/verificar-empadronamiento/', views.verificar_empadronamiento_organizacion, name='verificar_empadronamiento_organizacion'),
    path('organizacion/panorama/', views.panorama_municipal_organizacion, name='panorama_municipal_organizacion'),
    path('organizacion/estructura-territorial/', views.lista_estructura_territorial, name='lista_estructura_territorial'),
    path('organizacion/comunidades/', views.lista_comunidades, name='lista_comunidades'),
    path('organizacion/comunidades/nuevo/', views.crear_comunidad, name='crear_comunidad'),
    path('organizacion/comunidades/<int:pk>/editar/', views.editar_comunidad, name='editar_comunidad'),
    path('organizacion/sectores/', views.lista_sectores, name='lista_sectores'),
    path('organizacion/sectores/nuevo/', views.crear_sector, name='crear_sector'),
    path('organizacion/sectores/<int:pk>/editar/', views.editar_sector, name='editar_sector'),
    path('organizacion/centros/', views.lista_centros_votacion, name='lista_centros_votacion'),
    path('organizacion/centros/nuevo/', views.crear_centro_votacion, name='crear_centro_votacion'),
    path('organizacion/centros/<int:pk>/editar/', views.editar_centro_votacion, name='editar_centro_votacion'),
    path('organizacion/coordinadores/', views.lista_coordinadores, name='lista_coordinadores'),
    path('organizacion/coordinadores/nuevo/', views.crear_coordinador, name='crear_coordinador'),
    path('organizacion/coordinadores/<int:pk>/editar/', views.editar_coordinador, name='editar_coordinador'),
    path('organizacion/coordinadores/<int:pk>/', views.detalle_coordinador, name='detalle_coordinador'),
    path('organizacion/lideres/', views.lista_lideres, name='lista_lideres'),
    path('organizacion/lideres/nuevo/', views.crear_lider, name='crear_lider'),
    path('organizacion/lideres/<int:pk>/editar/', views.editar_lider, name='editar_lider'),
    path('organizacion/lideres/<int:pk>/', views.detalle_lider, name='detalle_lider'),
    path('organizacion/estructuras/', views.lista_estructuras, name='lista_estructuras'),
    path('organizacion/estructuras/nuevo/', views.crear_estructura, name='crear_estructura'),
    path('organizacion/estructuras/<int:pk>/editar/', views.editar_estructura, name='editar_estructura'),
    path('organizacion/estructuras/<int:pk>/', views.detalle_estructura, name='detalle_estructura'),
    path('organizacion/estructuras/<int:pk>/integrantes/<int:integrante_id>/eliminar/', views.eliminar_integrante_estructura, name='eliminar_integrante_estructura'),
    path('organizacion/responsables/', views.lista_responsables, name='lista_responsables'),
    path('organizacion/responsables/nuevo/', views.crear_responsable, name='crear_responsable'),
    path('organizacion/responsables/<int:pk>/editar/', views.editar_responsable, name='editar_responsable'),
    path('organizacion/responsables/<int:pk>/', views.detalle_responsable, name='detalle_responsable'),
    path('organizacion/reuniones/', views.lista_reuniones, name='lista_reuniones'),
    path('organizacion/reuniones/nuevo/', views.crear_reunion, name='crear_reunion'),
    path('organizacion/reuniones/<int:pk>/editar/', views.editar_reunion, name='editar_reunion'),
    path('organizacion/reuniones/<int:pk>/', views.detalle_reunion, name='detalle_reunion'),
    path('organizacion/incidencias/', views.lista_incidencias, name='lista_incidencias'),
    path('organizacion/incidencias/nuevo/', views.crear_incidencia, name='crear_incidencia'),
    path('organizacion/incidencias/<int:pk>/editar/', views.editar_incidencia, name='editar_incidencia'),
    path('organizacion/incidencias/<int:pk>/', views.detalle_incidencia, name='detalle_incidencia'),
    path('organizacion/reportes/cobertura-comunidades/', views.reporte_cobertura_comunidades, name='reporte_cobertura_comunidades'),
    path('organizacion/reportes/coordinadores/', views.reporte_coordinadores, name='reporte_coordinadores'),
    path('organizacion/reportes/reuniones/', views.reporte_reuniones, name='reporte_reuniones'),
    path('organizacion/reportes/crecimiento-mensual/', views.reporte_crecimiento_mensual, name='reporte_crecimiento_mensual'),
    path('organizacion/comunidad-lookup/', views.organizacion_comunidad_lookup, name='organizacion_comunidad_lookup'),

    # Secretaría de la Juventud
    path('juventud/', views.dashboard_juventud, name='dashboard_juventud'),
    path('juventud/dashboard/', views.dashboard_juventud, name='dashboard_juventud_home'),
    path('juventud/integrantes/', views.lista_integrantes_juventud, name='lista_integrantes_juventud'),
    path('juventud/integrantes/crear/', views.crear_integrante_juventud, name='crear_integrante_juventud'),
    path('juventud/integrantes/<int:pk>/', views.detalle_integrante_juventud, name='detalle_integrante_juventud'),
    path('juventud/integrantes/<int:pk>/editar/', views.editar_integrante_juventud, name='editar_integrante_juventud'),
    path('juventud/integrantes/<int:pk>/estado/', views.cambiar_estado_juventud, name='cambiar_estado_juventud'),
    path('juventud/buscar-dpi/', views.buscar_por_dpi_juventud, name='buscar_por_dpi_juventud'),
    path('juventud/verificar-empadronamiento/', views.verificar_empadronamiento_juventud, name='verificar_empadronamiento_juventud'),
    path('juventud/panorama/', views.panorama_municipal_juventud, name='panorama_municipal_juventud'),
    path('juventud/estructura-territorial/', views.lista_estructura_territorial_juventud, name='lista_estructura_territorial_juventud'),
    path('juventud/coordinadores/', views.lista_coordinadores_juventud, name='lista_coordinadores_juventud'),
    path('juventud/coordinadores/nuevo/', views.crear_coordinador_juventud, name='crear_coordinador_juventud'),
    path('juventud/coordinadores/<int:pk>/editar/', views.editar_coordinador_juventud, name='editar_coordinador_juventud'),
    path('juventud/coordinadores/<int:pk>/', views.detalle_coordinador_juventud, name='detalle_coordinador_juventud'),
    path('juventud/lideres/', views.lista_lideres_juveniles, name='lista_lideres_juveniles'),
    path('juventud/lideres/nuevo/', views.crear_lider_juvenil, name='crear_lider_juvenil'),
    path('juventud/lideres/<int:pk>/editar/', views.editar_lider_juvenil, name='editar_lider_juvenil'),
    path('juventud/lideres/<int:pk>/', views.detalle_lider_juvenil, name='detalle_lider_juvenil'),
    path('juventud/estructuras/', views.lista_estructuras_juventud, name='lista_estructuras_juventud'),
    path('juventud/estructuras/nuevo/', views.crear_estructura_juventud, name='crear_estructura_juventud'),
    path('juventud/estructuras/<int:pk>/editar/', views.editar_estructura_juventud, name='editar_estructura_juventud'),
    path('juventud/estructuras/<int:pk>/', views.detalle_estructura_juventud, name='detalle_estructura_juventud'),
    path('juventud/estructuras/<int:pk>/integrantes/<int:integrante_id>/eliminar/', views.eliminar_integrante_estructura_juventud, name='eliminar_integrante_estructura_juventud'),
    path('juventud/responsables/', views.lista_responsables_juventud, name='lista_responsables_juventud'),
    path('juventud/responsables/nuevo/', views.crear_responsable_juventud, name='crear_responsable_juventud'),
    path('juventud/responsables/<int:pk>/editar/', views.editar_responsable_juventud, name='editar_responsable_juventud'),
    path('juventud/responsables/<int:pk>/', views.detalle_responsable_juventud, name='detalle_responsable_juventud'),
    path('juventud/reuniones/', views.lista_reuniones_juventud, name='lista_reuniones_juventud'),
    path('juventud/reuniones/nuevo/', views.crear_reunion_juventud, name='crear_reunion_juventud'),
    path('juventud/reuniones/<int:pk>/editar/', views.editar_reunion_juventud, name='editar_reunion_juventud'),
    path('juventud/reuniones/<int:pk>/', views.detalle_reunion_juventud, name='detalle_reunion_juventud'),
    path('juventud/incidencias/', views.lista_incidencias_juventud, name='lista_incidencias_juventud'),
    path('juventud/incidencias/nuevo/', views.crear_incidencia_juventud, name='crear_incidencia_juventud'),
    path('juventud/incidencias/<int:pk>/editar/', views.editar_incidencia_juventud, name='editar_incidencia_juventud'),
    path('juventud/incidencias/<int:pk>/', views.detalle_incidencia_juventud, name='detalle_incidencia_juventud'),
    path('juventud/reportes/cobertura-comunidades/', views.reporte_cobertura_juventud, name='reporte_cobertura_juventud'),
    path('juventud/reportes/coordinadores/', views.reporte_coordinadores_juventud, name='reporte_coordinadores_juventud'),
    path('juventud/reportes/reuniones/', views.reporte_reuniones_juventud, name='reporte_reuniones_juventud'),
    path('juventud/reportes/crecimiento-mensual/', views.reporte_crecimiento_mensual_juventud, name='reporte_crecimiento_mensual_juventud'),
    path('juventud/comunidad-lookup/', views.juventud_comunidad_lookup, name='juventud_comunidad_lookup'),



    # Secretaría de Mujeres
    path('mujeres/', views.dashboard_mujeres, name='dashboard_mujeres'),
    path('mujeres/dashboard/', views.dashboard_mujeres, name='dashboard_mujeres_home'),
    path('mujeres/integrantes/', views.lista_integrantes_mujeres, name='lista_integrantes_mujeres'),
    path('mujeres/integrantes/crear/', views.crear_integrante_mujeres, name='crear_integrante_mujeres'),
    path('mujeres/integrantes/<int:pk>/', views.detalle_integrante_mujeres, name='detalle_integrante_mujeres'),
    path('mujeres/integrantes/<int:pk>/editar/', views.editar_integrante_mujeres, name='editar_integrante_mujeres'),
    path('mujeres/integrantes/<int:pk>/estado/', views.cambiar_estado_mujeres, name='cambiar_estado_mujeres'),
    path('mujeres/buscar-dpi/', views.buscar_por_dpi_mujeres, name='buscar_por_dpi_mujeres'),
    path('mujeres/verificar-empadronamiento/', views.verificar_empadronamiento_mujeres, name='verificar_empadronamiento_mujeres'),
    path('mujeres/panorama/', views.panorama_municipal_mujeres, name='panorama_municipal_mujeres'),
    path('mujeres/estructura-territorial/', views.lista_estructura_territorial_mujeres, name='lista_estructura_territorial_mujeres'),
    path('mujeres/coordinadores/', views.lista_coordinadores_mujeres, name='lista_coordinadores_mujeres'),
    path('mujeres/coordinadores/nuevo/', views.crear_coordinador_mujeres, name='crear_coordinador_mujeres'),
    path('mujeres/coordinadores/<int:pk>/editar/', views.editar_coordinador_mujeres, name='editar_coordinador_mujeres'),
    path('mujeres/coordinadores/<int:pk>/', views.detalle_coordinador_mujeres, name='detalle_coordinador_mujeres'),
    path('mujeres/lideres/', views.lista_lideres_mujeres, name='lista_lideres_mujeres'),
    path('mujeres/lideres/nuevo/', views.crear_lider_mujeres, name='crear_lider_mujeres'),
    path('mujeres/lideres/<int:pk>/editar/', views.editar_lider_mujeres, name='editar_lider_mujeres'),
    path('mujeres/lideres/<int:pk>/', views.detalle_lider_mujeres, name='detalle_lider_mujeres'),
    path('mujeres/estructuras/', views.lista_estructuras_mujeres, name='lista_estructuras_mujeres'),
    path('mujeres/estructuras/nuevo/', views.crear_estructura_mujeres, name='crear_estructura_mujeres'),
    path('mujeres/estructuras/<int:pk>/editar/', views.editar_estructura_mujeres, name='editar_estructura_mujeres'),
    path('mujeres/estructuras/<int:pk>/', views.detalle_estructura_mujeres, name='detalle_estructura_mujeres'),
    path('mujeres/estructuras/<int:pk>/integrantes/<int:integrante_id>/eliminar/', views.eliminar_integrante_estructura_mujeres, name='eliminar_integrante_estructura_mujeres'),
    path('mujeres/responsables/', views.lista_responsables_mujeres, name='lista_responsables_mujeres'),
    path('mujeres/responsables/nuevo/', views.crear_responsable_mujeres, name='crear_responsable_mujeres'),
    path('mujeres/responsables/<int:pk>/editar/', views.editar_responsable_mujeres, name='editar_responsable_mujeres'),
    path('mujeres/responsables/<int:pk>/', views.detalle_responsable_mujeres, name='detalle_responsable_mujeres'),
    path('mujeres/reuniones/', views.lista_reuniones_mujeres, name='lista_reuniones_mujeres'),
    path('mujeres/reuniones/nuevo/', views.crear_reunion_mujeres, name='crear_reunion_mujeres'),
    path('mujeres/reuniones/<int:pk>/editar/', views.editar_reunion_mujeres, name='editar_reunion_mujeres'),
    path('mujeres/reuniones/<int:pk>/', views.detalle_reunion_mujeres, name='detalle_reunion_mujeres'),
    path('mujeres/incidencias/', views.lista_incidencias_mujeres, name='lista_incidencias_mujeres'),
    path('mujeres/incidencias/nuevo/', views.crear_incidencia_mujeres, name='crear_incidencia_mujeres'),
    path('mujeres/incidencias/<int:pk>/editar/', views.editar_incidencia_mujeres, name='editar_incidencia_mujeres'),
    path('mujeres/incidencias/<int:pk>/', views.detalle_incidencia_mujeres, name='detalle_incidencia_mujeres'),
    path('mujeres/reportes/cobertura-comunidades/', views.reporte_cobertura_mujeres, name='reporte_cobertura_mujeres'),
    path('mujeres/reportes/coordinadores/', views.reporte_coordinadores_mujeres, name='reporte_coordinadores_mujeres'),
    path('mujeres/reportes/reuniones/', views.reporte_reuniones_mujeres, name='reporte_reuniones_mujeres'),
    path('mujeres/reportes/crecimiento-mensual/', views.reporte_crecimiento_mensual_mujeres, name='reporte_crecimiento_mensual_mujeres'),
    path('mujeres/comunidad-lookup/', views.mujeres_comunidad_lookup, name='mujeres_comunidad_lookup'),

]