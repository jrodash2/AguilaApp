from datetime import datetime, timezone
from venv import logger
from django.forms import IntegerField
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group, User
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.urls import reverse
import openpyxl
from django.views.decorators.csrf import csrf_exempt
import pandas as pd
import requests
from .form import  AfiliadoForm, CentroVotacionForm, ComisionForm, ComunidadForm, PerfilForm, UserCreateForm, UserEditForm, UserCreateForm,  InstitucionForm
from .models import   Afiliado, CentroVotacion, Comision, Comunidad, Eleccion2023, Perfil,  Institucion
from django.views.generic import CreateView
from django.views.generic import ListView
from django.urls import reverse_lazy
from django.http import Http404, HttpResponseNotAllowed, JsonResponse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.db import models
from django.db.models import Sum, F, Value, Count, Q, Case, When, OuterRef, Subquery, IntegerField
from django.contrib.auth.decorators import login_required, user_passes_test
from collections import defaultdict
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
import json
from django.contrib.auth.models import Group
from .utils import grupo_requerido
from django.views.decorators.http import require_GET
from django.db.models.functions import Coalesce
from django.db import transaction
from django.db.models import Sum
from django.shortcuts import render
from django.template.loader import render_to_string
from django.template.loader import get_template
from django.http import HttpResponse
from xhtml2pdf import pisa
from weasyprint import HTML
from django.db.models.functions import Cast, TruncWeek
from django.utils import timezone
from datetime import timedelta
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import datetime
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import strip_tags
from decimal import Decimal
from datetime import datetime  
from openpyxl import Workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Alignment, Font
import re
from django.views.generic.detail import DetailView
from django.core.mail import BadHeaderError
from smtplib import SMTPException

    
    
@login_required
@grupo_requerido('Administrador')
def editar_institucion(request):
    institucion = Institucion.objects.first()  # Solo debería haber una

    if request.method == 'POST':
        form = InstitucionForm(request.POST, request.FILES, instance=institucion)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos institucionales actualizados correctamente.")
            return redirect('afiliados:editar_institucion')  # Reemplaza con la URL real
    else:
        form = InstitucionForm(instance=institucion)

    return render(request, 'afiliados/editar_institucion.html', {'form': form})



@login_required
@grupo_requerido('Administrador', 'afiliados')
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get('new_password')
            user.set_password(password)
            user.save()

            group = form.cleaned_data.get('group')
            user.groups.add(group)

            # ✅ Espera a que la señal cree el perfil automáticamente
            foto = form.cleaned_data.get('foto')
            try:
                perfil = user.perfil  # accede al perfil creado por la señal
                if foto:
                    perfil.foto = foto
                    perfil.save()
            except Perfil.DoesNotExist:
                # Fallback solo si la señal falló (raro)
                Perfil.objects.create(user=user, foto=foto)

            messages.success(request, 'Usuario creado correctamente.')
            return redirect('afiliados:user_create')
    else:
        form = UserCreateForm()

    users = User.objects.all()
    return render(request, 'afiliados/user_form_create.html', {'form': form, 'users': users})

@login_required
@grupo_requerido('Administrador', 'afiliados')
def user_edit(request, user_id):
    user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = UserEditForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Usuario editado correctamente.')
            return redirect('afiliados:user_edit', user_id=user.id)
    else:
        form = UserEditForm(instance=user)

    context = {
        'form': form,
        'user': user,
        'users': User.objects.all(),
    }
    return render(request, 'afiliados/user_form_edit.html', context)




@login_required
@grupo_requerido('Administrador', 'afiliados')
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('afiliados:user_create')  # Redirige a la misma página para mostrar la lista actualizada
    return render(request, 'afiliados/user_confirm_delete.html', {'user': user})


def home(request):
    return render(request, 'afiliados/login.html')

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q, Sum
import json


@login_required
@grupo_requerido('Administrador', 'afiliados')
def dahsboard(request):

    # === Totales para las cards ===
    total_afiliados = Afiliado.objects.count()
    total_lideres = Afiliado.objects.filter(es_lider_comunitario=True).count()
    total_comunidades = Comunidad.objects.count()
    total_empadronados = Afiliado.objects.filter(empadronado=True).count()

    # === 1. Últimos afiliados registrados ===
    ultimos_afiliados = (
        Afiliado.objects.select_related('comunidad')
        .order_by('-id')[:10]
    )

    # === 2. Afiliados por comunidad ===
    afiliados_por_comunidad = (
        Afiliado.objects.values('comunidad__nombre')
        .annotate(total=Count('id'))
        .order_by('comunidad__nombre')
    )

    # === 3. Líderes por comunidad ===
    lideres_por_comunidad = (
        Afiliado.objects.filter(es_lider_comunitario=True)
        .values('comunidad__nombre')
        .annotate(total=Count('id'))
        .order_by('comunidad__nombre')
    )

    # === 4. Afiliados por rango de edad ===
    hoy = timezone.now().date()

    rangos = {
        "18-25": 0,
        "26-35": 0,
        "36-45": 0,
        "46-60": 0,
        "60+": 0,
    }

    afiliados = Afiliado.objects.exclude(fecha_nacimiento__isnull=True)

    for a in afiliados:
        fn = a.fecha_nacimiento
        edad = hoy.year - fn.year - ((hoy.month, hoy.day) < (fn.month, fn.day))

        if edad <= 25:
            rangos["18-25"] += 1
        elif edad <= 35:
            rangos["26-35"] += 1
        elif edad <= 45:
            rangos["36-45"] += 1
        elif edad <= 60:
            rangos["46-60"] += 1
        else:
            rangos["60+"] += 1

    rangos_edad = [
        {"rango": "18-25", "total": rangos["18-25"]},
        {"rango": "26-35", "total": rangos["26-35"]},
        {"rango": "36-45", "total": rangos["36-45"]},
        {"rango": "46-60", "total": rangos["46-60"]},
        {"rango": "60+",   "total": rangos["60+"]},
    ]

    # === 5. Empadronados ===
    total_no_empadronados = Afiliado.objects.filter(empadronado=False).count()

    # === CONTEXT ===
    context = {
        # Totales para las cards
        'total_afiliados': total_afiliados,
        'total_lideres': total_lideres,
        'total_comunidades': total_comunidades,
        'total_empadronados': total_empadronados,

        # Datos para dashboard
        'ultimos_afiliados': ultimos_afiliados,
        'afiliados_por_comunidad': list(afiliados_por_comunidad),
        'lideres_por_comunidad': list(lideres_por_comunidad),
        'rangos_edad': rangos_edad,
        'empadronados': {
            'empadronados': total_empadronados,
            'no_empadronados': total_no_empadronados,
        }
    }

    return render(request, 'afiliados/dahsboard.html', context)



def acceso_denegado(request, exception=None):
    return render(request, 'afiliados/403.html', status=403)



def signout(request):
    logout(request)
    return redirect('afiliados:signin')


def signin(request):  
    institucion = Institucion.objects.first()
    if request.method == 'GET':
        # Deberías instanciar el AuthenticationForm correctamente
        return render(request, 'afiliados/login.html', {
            'form': AuthenticationForm(),
            'institucion': institucion,
        })
    else:
        # Se instancia AuthenticationForm con los datos del POST para mantener el estado
        form = AuthenticationForm(request, data=request.POST)
        
        if form.is_valid():
            # El método authenticate devuelve el usuario si es válido
            user = form.get_user()
            
            # Si el usuario es encontrado, se inicia sesión
            auth_login(request, user)
            
            # Ahora verificamos los grupos
            for g in user.groups.all():
                print(g.name)
                if g.name == 'Administrador':
                    return redirect('afiliados:dahsboard')
                elif g.name == 'Departamento':
                    return redirect('afiliados:crear_requerimiento')
                elif g.name == 'afiliados':
                    return redirect('afiliados:dahsboard')
            # Si no se encuentra el grupo adecuado, se redirige a una página por defecto
            return redirect('afiliados:dahsboard')
        else:
            # Si el formulario no es válido, se retorna con el error
            return render(request, 'afiliados/login.html', {
                'form': form,  # Pasamos el formulario con los errores
                'error': 'Usuario o contraseña incorrectos',
                'institucion': institucion,
            })

def dashboard_elecciones(request):

    centros = Eleccion2023.objects.values_list(
        "centro_votacion", flat=True
    ).distinct().order_by("centro_votacion")

    partidos = [
        "todos","cambio","morena","vamos","pin","renovador",
        "valor","azul","une","fcn_nacion","podemos","uc"
    ]

    # 🔥 GENERAR TOTALES GLOBALES
    totales_globales = {
        p: Eleccion2023.objects.aggregate(total=Sum(p))["total"] or 0
        for p in partidos
    }

    # 🔥 ORDENAR DE MAYOR A MENOR Y AGREGAR RANKING
    ranking_global = sorted(
        totales_globales.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return render(request, "afiliados/elecciones2023.html", {
        "centros": centros,
        "ranking_global": ranking_global,  # ⬅ nueva variable
    })



from django.http import JsonResponse
from django.db.models import Sum

def datos_centro(request):
    centro = request.GET.get("centro", "").strip()
    mesa = request.GET.get("mesa", "").strip()

    if not centro:
        return JsonResponse({"error": "Centro no enviado"})

    queryset = Eleccion2023.objects.filter(centro_votacion=centro)

    if not queryset.exists():
        return JsonResponse({"error": "Centro no encontrado"})

    # 🔥 SOLO filtrar mesa si no es "0"
    if mesa and mesa != "0":
        queryset = queryset.filter(mesa=mesa)

    partidos = [
        "todos","cambio","morena","vamos","pin","renovador",
        "valor","azul","une","fcn_nacion","podemos","uc"
    ]

    data_partidos = {
        p: queryset.aggregate(total=Sum(p))["total"] or 0
        for p in partidos
    }

    resumen = {
        "votos_blanco": queryset.aggregate(Sum("votos_blanco"))["votos_blanco__sum"] or 0,
        "votos_nulos": queryset.aggregate(Sum("votos_nulos"))["votos_nulos__sum"] or 0,
        "votos_invalidos": queryset.aggregate(Sum("votos_invalidos"))["votos_invalidos__sum"] or 0,
        "total": queryset.aggregate(Sum("total"))["total__sum"] or 0,
    }

    mesas = list(
        Eleccion2023.objects.filter(centro_votacion=centro)
        .exclude(mesa__isnull=True)
        .values_list("mesa", flat=True)
        .order_by("mesa")
    )

    return JsonResponse({
        "partidos": data_partidos,
        "resumen": resumen,
        "mesas": mesas,
    })





@login_required
@grupo_requerido('Administrador')
def afiliado_lista(request):
    afiliados = Afiliado.objects.all().select_related('comunidad', 'centro_votacion')
    form = AfiliadoForm()  # Instancia vacía para el modal

    if request.method == 'POST':
        form = AfiliadoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('afiliados:afiliado_lista')

    return render(request, 'afiliados/lista.html', {
        'afiliados': afiliados,
        'form': form  # Pasamos el formulario al template
    })


@login_required
@csrf_exempt # Solo si estás usando AJAX sin manejar CSRF token en el header correctamente
def afiliado_nuevo(request):
    institucion = Institucion.objects.first()
    
    if request.method == 'POST':
        # 1. Usar el AfiliadoForm actualizado
        form = AfiliadoForm(request.POST) 
        
        # Si la solicitud es AJAX (desde el modal)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            
            if form.is_valid():
                afiliado = form.save()
                
                # 🛠️ Verificación Adicional (Opcional pero Recomendada)
                # Si el afiliado es guardado con lider_vinculado, nos aseguramos que ese 'lider_vinculado'
                # realmente exista y sea un líder (aunque el form ya lo limite, esto es una capa de seguridad).
                if afiliado.lider_vinculado and not afiliado.lider_vinculado.es_lider_comunitario:
                    # Esto no debería pasar si limit_choices_to funciona, pero es buena práctica.
                    # Podrías registrar un error o limpiar el campo si es necesario.
                    pass 
                
                # Preparamos la respuesta para AJAX
                response_data = {
                    'exito': True,
                    'mensaje': f"Afiliado '{afiliado.nombre_completo}' guardado con éxito.",
                    'afiliado': {
                        'id': afiliado.id,
                        'nombre_completo': afiliado.nombre_completo,
                        # ... puedes añadir más campos para actualizar la tabla si es necesario
                    }
                }
                return JsonResponse(response_data, status=200)
            
            else:
                # Manejar errores de validación para AJAX
                error_html = render_to_string('afiliados/partials/form_errors.html', {'form': form})
                return JsonResponse({
                    'exito': False,
                    'mensaje': "Error de validación. Revise los campos.",
                    'errores': form.errors.as_json()
                }, status=400)
                
        # Si la solicitud es POST normal (no AJAX)
        else:
            if form.is_valid():
                form.save()
                messages.success(request, 'Afiliado guardado con éxito.')
                return redirect('afiliados:afiliados_lista') # Asegúrate que el nombre de la URL sea correcto
            else:
                messages.error(request, 'Hubo un error al guardar el afiliado.')
                # Si no es AJAX, podrías renderizar la página completa con el formulario con errores
                
    else:
        # Petición GET: Creamos el formulario vacío
        form = AfiliadoForm()

    # Renderizamos la lista principal o el contexto para el modal (si no es AJAX)
    # Asumiendo que esta vista es la que renderiza la lista principal y el modal
    context = {
        'afiliados': Afiliado.objects.all(),
        'form': form, # El formulario vacío o con errores
        'institucion': institucion
    }
    return render(request, 'afiliados/afiliados_lista.html', context)

# -------------------------------
# EDITAR AFILIADO
# -------------------------------
@login_required
@grupo_requerido('Administrador')
def afiliado_editar(request, pk):
    afiliado = get_object_or_404(Afiliado, pk=pk)
    if request.method == 'POST':
        form = AfiliadoForm(request.POST, instance=afiliado)
        if form.is_valid():
            form.save()
            messages.success(request, "Afiliado actualizado correctamente.")
            return redirect('afiliados:afiliado_lista')
    else:
        form = AfiliadoForm(instance=afiliado)
    return render(request, 'afiliados/form.html', {'form': form, 'afiliado': afiliado})

@login_required
# @grupo_requerido('Administrador') # Descomentar si usas este decorador
def lider_editar(request, pk):
    afiliado = get_object_or_404(Afiliado, pk=pk)
    
    # OPCIONAL: Si el objeto no es un líder, redirigir a la edición general
    # if not afiliado.es_lider_comunitario:
    #     return redirect('afiliados:afiliado_editar', pk=pk)

    if request.method == 'POST':
        form = AfiliadoForm(request.POST, instance=afiliado)
        if form.is_valid():
            form.save()
            messages.success(request, f"Líder {afiliado.nombre_completo} actualizado correctamente.")
            return redirect('afiliados:lideres_lista') # 🚀 Redirección CLAVE
    else:
        form = AfiliadoForm(instance=afiliado)
    
    # Cambiamos el contexto para indicar que es una edición de líder (opcional)
    context = {
        'form': form, 
        'afiliado': afiliado,
        'es_lider_edicion': True # Usar esta variable en el template para cambiar el título
    }
    return render(request, 'afiliados/form.html', context)

@login_required
def lideres_lista(request):
    """Muestra solo a los afiliados que son Líderes Comunitarios."""
    
    # Filtramos la lista de Afiliados donde es_lider_comunitario es True
    lideres = Afiliado.objects.filter(es_lider_comunitario=True).select_related('comunidad', 'centro_votacion').order_by('nombre_completo')
    
    # Necesitas el formulario para el modal 'Nuevo Afiliado'
    form = AfiliadoForm()
    institucion = Institucion.objects.first()

    context = {
        'lideres': lideres, # Renombramos la variable a 'lideres' para evitar confusiones
        'form': form,
        'institucion': institucion,
    }
    
    return render(request, 'afiliados/lideres_lista.html', context)

# -------------------------------
# ELIMINAR AFILIADO
# -------------------------------
@login_required
@grupo_requerido('Administrador')
def afiliado_eliminar(request, pk):
    afiliado = get_object_or_404(Afiliado, pk=pk)

    if request.method == 'POST':
        afiliado.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'exito': True, 'mensaje': 'Afiliado eliminado exitosamente.'})
        return redirect('afiliados:afiliado_lista')

    return JsonResponse({'exito': False, 'mensaje': 'Método no permitido.'}, status=400)

# En tu archivo afiliados_app/views.py

from .form import AfiliadoForm # Asegúrate de importar el formulario

@login_required
def afiliado_detalle(request, pk):
    afiliado = get_object_or_404(Afiliado, pk=pk)
    institucion = Institucion.objects.first()
    
    referidos = afiliado.referidos.all() # Ya no necesitamos el if, si no es líder estará vacío
    
    # 🆕 IMPORTANTE: Creamos el formulario para el modal
    form = AfiliadoForm() 
    
    context = {
        'afiliado': afiliado,
        'institucion': institucion,
        'referidos': referidos,
        'form': form, # <-- Pasamos el formulario al template
    }
    
    return render(request, 'afiliados/afiliado_detalle.html', context)


# -------------------------------
# ACCESO DENEGADO
# -------------------------------
@login_required
def acceso_denegado(request):
    return render(request, 'afiliados/acceso_denegado.html')
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from .selenium_utils import verificar_empadronamiento 

from .selenium_utils import verificar_empadronamiento
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def verificar_empadronamiento_ajax(request):
    if request.method == 'POST':
        dpi = request.POST.get('dpi')
        fecha_nacimiento = request.POST.get('fecha_nacimiento')

        if not dpi or not fecha_nacimiento:
            return JsonResponse({'exito': False, 'mensaje': 'Faltan datos.'})

        # 🎯 CAMBIO CLAVE: Capturamos la tupla (mensaje, nombre, municipio)
        mensaje_resultado, nombre_ciudadano, municipio_residencia = verificar_empadronamiento(dpi, fecha_nacimiento)

        if "ACTIVO" in mensaje_resultado:
            return JsonResponse({
                'exito': True,
                'mensaje': mensaje_resultado,
                'nombre': nombre_ciudadano,
                # 🎯 Enviamos el municipio REAL obtenido por Selenium
                'municipio': municipio_residencia 
            })
        else:
            return JsonResponse({
                'exito': False, 
                'mensaje': mensaje_resultado
            })

    return JsonResponse({'exito': False, 'mensaje': 'Método no permitido.'}, status=400)

# -----------------------------------------
# CRUD - COMUNIDAD
# -----------------------------------------

@login_required
@grupo_requerido('Administrador', 'afiliados')
def comunidad_lista(request):
    comunidades = Comunidad.objects.all().order_by('nombre')
    form = ComunidadForm()  # Nuevo formulario vacío 

    return render(request, 'afiliados/comunidad_lista.html', {
        'form': form,
        'comunidades': comunidades
    })


@login_required
@grupo_requerido('Administrador')
def comunidad_nueva(request):
    if request.method == 'POST':
        form = ComunidadForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Comunidad creada correctamente.")
            return redirect('afiliados:comunidad_lista')
    else:
        form = ComunidadForm()

    comunidades = Comunidad.objects.all().order_by('nombre')

    return render(request, 'afiliados/comunidad_lista.html', {
        'form': form,
        'comunidades': comunidades
    })


@login_required
@grupo_requerido('Administrador')
def comunidad_editar(request, pk):
    comunidad = get_object_or_404(Comunidad, pk=pk)

    if request.method == "POST":
        form = ComunidadForm(request.POST, instance=comunidad)
        if form.is_valid():
            form.save()
            messages.success(request, "Comunidad actualizada correctamente.")
            return redirect('afiliados:comunidad_lista')
    else:
        form = ComunidadForm(instance=comunidad)

    comunidades = Comunidad.objects.all().order_by('nombre')

    return render(request, 'afiliados/comunidad_lista.html', {
        'form': form,
        'comunidad': comunidad,
        'comunidades': comunidades,
    })


@login_required
@grupo_requerido('Administrador')
def comunidad_eliminar(request, pk):
    comunidad = get_object_or_404(Comunidad, pk=pk)

    if request.method == 'POST':
        comunidad.delete()
        messages.success(request, "Comunidad eliminada.")
        return redirect('afiliados:comunidad_lista')

    # ❌ Ya NO renderizamos nada
    return redirect('afiliados:comunidad_lista')

# -----------------------------------------
# CRUD - CENTRO DE VOTACION
# -----------------------------------------
# -----------------------------------------
# CRUD - CENTRO DE VOTACIÓN (MisMO estilo)
# -----------------------------------------

@login_required
@grupo_requerido('Administrador', 'afiliados')
def centro_lista(request):
    centros = CentroVotacion.objects.all().order_by('nombre')
    form = CentroVotacionForm()  # formulario vacío para creación

    return render(request, 'afiliados/centro_lista.html', {
        'form': form,
        'centros': centros
    })


@login_required
@grupo_requerido('Administrador')
def centro_nuevo(request):
    if request.method == 'POST':
        form = CentroVotacionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Centro de Votación creado correctamente.")
            return redirect('afiliados:centro_lista')
    else:
        form = CentroVotacionForm()

    centros = CentroVotacion.objects.all().order_by('nombre')

    return render(request, 'afiliados/centro_lista.html', {
        'form': form,
        'centros': centros
    })


@login_required
@grupo_requerido('Administrador')
def centro_editar(request, pk):
    centro = get_object_or_404(CentroVotacion, pk=pk)

    if request.method == "POST":
        form = CentroVotacionForm(request.POST, instance=centro)
        if form.is_valid():
            form.save()
            messages.success(request, "Centro de Votación actualizado correctamente.")
            return redirect('afiliados:centro_lista')
    else:
        form = CentroVotacionForm(instance=centro)

    centros = CentroVotacion.objects.all().order_by('nombre')

    return render(request, 'afiliados/centro_lista.html', {
        'form': form,
        'centro': centro,
        'centros': centros,
    })


@login_required
@grupo_requerido('Administrador')
def centro_eliminar(request, pk):
    centro = get_object_or_404(CentroVotacion, pk=pk)

    if request.method == 'POST':
        centro.delete()
        messages.success(request, "Centro de votación eliminado.")
        return redirect('afiliados:centro_lista')

    return redirect('afiliados:centro_lista')

# -----------------------------------------
# CRUD - COMISION
# -----------------------------------------
# -----------------------------------------
# CRUD - COMISIÓN (Mismo estilo)
# -----------------------------------------

@login_required
@grupo_requerido('Administrador', 'afiliados')
def comision_lista(request):
    comisiones = Comision.objects.all().order_by('nombre')
    form = ComisionForm()

    return render(request, 'afiliados/comision_lista.html', {
        'form': form,
        'comisiones': comisiones,
    })


@login_required
@grupo_requerido('Administrador')
def comision_nueva(request):
    if request.method == 'POST':
        form = ComisionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Comisión creada correctamente.")
            return redirect('afiliados:comision_lista')

    comisiones = Comision.objects.all().order_by('nombre')
    form = ComisionForm()

    return render(request, 'afiliados/comision_lista.html', {
        'form': form,
        'comisiones': comisiones,
    })


@login_required
@grupo_requerido('Administrador')
def comision_editar(request, pk):
    comision = get_object_or_404(Comision, pk=pk)

    if request.method == 'POST':
        form = ComisionForm(request.POST, instance=comision)
        if form.is_valid():
            form.save()
            messages.success(request, "Comisión actualizada correctamente.")
            return redirect('afiliados:comision_lista')
    else:
        form = ComisionForm(instance=comision)

    comisiones = Comision.objects.all().order_by('nombre')

    return render(request, 'afiliados/comision_lista.html', {
        'form': form,
        'comision': comision,
        'comisiones': comisiones,
    })


@login_required
@grupo_requerido('Administrador')
def comision_eliminar(request, pk):
    comision = get_object_or_404(Comision, pk=pk)

    if request.method == 'POST':
        comision.delete()
        messages.success(request, "Comisión eliminada correctamente.")
        return redirect('afiliados:comision_lista')

    return redirect('afiliados:comision_lista')
