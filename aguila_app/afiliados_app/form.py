from django import forms
from django.contrib.auth.models import User, Group
from django.forms import CheckboxInput, DateInput, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError


from .models import  Perfil,  Institucion, Afiliado, LiderComunitario, Comunidad, CentroVotacion, Comision

from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce



from django import forms
from .models import Institucion

from django.core.exceptions import ValidationError

class InstitucionForm(forms.ModelForm):
    pagina_web = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Ingrese URL que comience con www., sin http/https.'
    )

    class Meta:
        model = Institucion
        fields = ['nombre', 'direccion', 'telefono', 'pagina_web', 'logo', 'logo2']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            # 'pagina_web': forms.URLInput(attrs={'class': 'form-control'}),  # quitamos este
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'logo2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_pagina_web(self):
        url = self.cleaned_data.get('pagina_web')
        if url:
            if not url.startswith('www.'):
                raise ValidationError('La URL debe comenzar con "www."')
            # Añadimos http:// para que sea una URL válida
            url = 'http://' + url
        return url



from django import forms
from django.contrib.auth.models import User, Group
from .models import Perfil

class UserCreateForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Confirmar Contraseña"
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    cargo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')

        if password != confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password')
        user.set_password(password)

        if commit:
            user.save()
            # Asignar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])

            # Crear perfil
            cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')
            Perfil.objects.update_or_create(
                user=user,
                defaults={'cargo': cargo, 'foto': foto}
            )

        return user

class UserEditForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Grupo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cargo = forms.CharField(
        max_length=100,
        required=False,
        label="Cargo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        label="Foto de perfil",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].required = False

        # Cargar valores iniciales del perfil (cargo y foto)
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['cargo'].initial = perfil.cargo
                self.fields['foto'].initial = perfil.foto

            groups = self.instance.groups.all()
            if groups.exists():
                self.fields['group'].initial = groups.first()

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Actualizar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])
            else:
                user.groups.clear()

            # Actualizar perfil
            perfil, created = Perfil.objects.get_or_create(user=user)
            perfil.cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')

            if foto:
                perfil.foto = foto

            perfil.save()

        return user


        
class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto']
        widgets = {
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
  # -------------------------------
# Formulario Afiliado
# -------------------------------
class AfiliadoForm(forms.ModelForm):
    class Meta:
        model = Afiliado
        fields = '__all__'
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'dpi': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'  # 🔹 formato ISO compatible con <input type="date">
            ),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'rows': 3}),
            'comunidad': forms.Select(attrs={'class': 'form-control'}),
            'lider': forms.Select(attrs={'class': 'form-control'}),
            'centro_votacion': forms.Select(attrs={'class': 'form-control'}),
            'empadronado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'comisiones': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Forzar formato correcto de fecha al cargar el formulario (modo edición)
        if self.instance and self.instance.fecha_nacimiento:
            self.initial['fecha_nacimiento'] = self.instance.fecha_nacimiento.strftime('%Y-%m-%d')

# -------------------------------
# Formulario Líder Comunitario
# -------------------------------
class LiderForm(forms.ModelForm):
    class Meta:
        model = LiderComunitario
        fields = '__all__'
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'comunidad': forms.Select(attrs={'class': 'form-control'}),
            'comisiones': forms.SelectMultiple(attrs={'class': 'form-control'}),
        }

# -------------------------------
# Formulario Comunidad
# -------------------------------
class ComunidadForm(forms.ModelForm):
    class Meta:
        model = Comunidad
        fields = ['nombre']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
        }

# -------------------------------
# Formulario Centro de Votación
# -------------------------------
class CentroVotacionForm(forms.ModelForm):
    class Meta:
        model = CentroVotacion
        fields = ['nombre', 'ubicacion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

# -------------------------------
# Formulario Comisión
# -------------------------------
class ComisionForm(forms.ModelForm):
    class Meta:
        model = Comision
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }