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
from .form import  AfiliadoForm, PerfilForm, UserCreateForm, UserEditForm, UserCreateForm,  InstitucionForm
from .models import   Afiliado, Perfil,  Institucion
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



    return render(request, 'afiliados/dashboard.html')


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


@login_required
@grupo_requerido('Administrador')
def afiliado_lista(request):
    afiliados = Afiliado.objects.all().select_related('comunidad', 'centro_votacion', 'lider')
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


# -------------------------------
# CREAR AFILIADO
# -------------------------------
@login_required
@grupo_requerido('Administrador')
def afiliado_nuevo(request):
    if request.method == 'POST':
        form = AfiliadoForm(request.POST)
        if form.is_valid():
            afiliado = form.save()

            # Si la solicitud es AJAX, devolvemos JSON en lugar de redirigir
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                data = {
                    'exito': True,
                    'mensaje': "Afiliado agregado correctamente.",
                    'afiliado': {
                        'id': afiliado.id,
                        'nombre_completo': afiliado.nombre_completo,
                        'dpi': afiliado.dpi,
                        'comunidad': str(afiliado.comunidad) if afiliado.comunidad else "",
                        'lider': str(afiliado.lider) if afiliado.lider else "",
                        'centro_votacion': str(afiliado.centro_votacion) if afiliado.centro_votacion else "",
                        'empadronado': "Sí" if afiliado.empadronado else "No",
                    }
                }
                return JsonResponse(data)
            else:
                messages.success(request, "Afiliado agregado correctamente.")
                return redirect('afiliados:afiliado_lista')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'exito': False,
                    'mensaje': "Datos inválidos. Verifique el formulario."
                })

    else:
        form = AfiliadoForm()

    return render(request, 'afiliados/form.html', {'form': form})

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




# -------------------------------
# ACCESO DENEGADO
# -------------------------------
@login_required
def acceso_denegado(request):
    return render(request, 'afiliados/acceso_denegado.html')

from django.http import JsonResponse
from .selenium_utils import verificar_empadronamiento

def verificar_empadronamiento_ajax(request):
    if request.method == "POST":
        dpi = request.POST.get("dpi")
        fecha_nacimiento = request.POST.get("fecha_nacimiento")
        if not dpi or not fecha_nacimiento:
            return JsonResponse({"exito": False, "mensaje": "Datos incompletos"}, status=400)

        try:
            resultado = verificar_empadronamiento(dpi, fecha_nacimiento)
            return JsonResponse({"exito": True, "mensaje": resultado})
        except Exception as e:
            return JsonResponse({"exito": False, "mensaje": f"Error interno: {str(e)}"}, status=500)

    return JsonResponse({"exito": False, "mensaje": "Método no permitido"}, status=405)


