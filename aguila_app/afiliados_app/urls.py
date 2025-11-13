from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


app_name = 'afiliados'

# Manejador global de errores (esto debe estar fuera de urlpatterns)
handler403 = 'afiliados_app.views.acceso_denegado'  # Asegúrate que el nombre de tu app sea correcto

urlpatterns = [
    path('', views.home, name='home'), 
    path('dahsboard/', views.dahsboard, name='dahsboard'),
    path('signin/', views.signin, name='signin'),
    path('logout/', views.signout, name='logout'),

    # Acceso denegado
    path('no-autorizado/', views.acceso_denegado, name='acceso_denegado'),
   
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
    path('verificar_empadronamiento/', views.verificar_empadronamiento_ajax, name='verificar_empadronamiento'),
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

  


]
