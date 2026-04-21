from django import forms
from django.contrib.auth.models import User, Group
from django.forms import CheckboxInput, DateInput, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError


from .models import  Perfil,  Institucion, Afiliado, Comunidad, CentroVotacion, Comision, Sector, OrganizacionIntegrante

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


from django import forms
# Asegúrate de importar tu modelo Afiliado
# from .models import Afiliado # o la ruta correcta
# -------------------------------
# Formulario Afiliado
# -------------------------------
class AfiliadoForm(forms.ModelForm):
    comision = forms.ModelChoiceField(
        queryset=Comision.objects.all().order_by('nombre'),
        required=False,
        label='Comisión',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cargo_en_comision = forms.ChoiceField(
        choices=[('', '---------')] + list(Afiliado.CargoComision.choices),
        required=False,
        label='Cargo en Comisión',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    class Meta:
        model = Afiliado
        # ⚠️ IMPORTANTE: Ajustar la lista de campos
        fields = [
            'nombre_completo', 'dpi', 'fecha_nacimiento', 'telefono', 
            'direccion', 'comunidad', 
            'es_lider_comunitario',  # 🌟 NUEVO: El check para ser líder
            'lider_vinculado',       # 🔗 RENOMBRADO: Apunta a otro Afiliado (Líder)
            'empadronado',
        ]
        
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control'}),
            'dpi': forms.TextInput(attrs={'class': 'form-control'}),
            'fecha_nacimiento': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d'
            ),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control', 'rows': 3}),
            'comunidad': forms.Select(attrs={'class': 'form-control'}),
            'lider_vinculado': forms.Select(attrs={'class': 'form-control'}), # 🔗 RENOMBRADO

            'empadronado': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_lider_comunitario': forms.CheckboxInput(attrs={'class': 'form-check-input'}), # 🌟 NUEVO

        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ✅ Forzar formato correcto de fecha al cargar el formulario (modo edición)
        if self.instance and self.instance.fecha_nacimiento:
            self.initial['fecha_nacimiento'] = self.instance.fecha_nacimiento.strftime('%Y-%m-%d')

        if self.instance and self.instance.pk:
            self.fields['comision'].initial = self.instance.comisiones.first()
            self.fields['cargo_en_comision'].initial = self.instance.cargo_en_comision
        
        # 🎨 Opcional: Renombrar la etiqueta del campo 'lider_vinculado'
        self.fields['lider_vinculado'].label = 'Líder (Afiliado Referente)'

    def clean(self):
        cleaned_data = super().clean()
        comision = cleaned_data.get('comision')
        cargo = cleaned_data.get('cargo_en_comision')

        if cargo and not comision:
            cleaned_data['cargo_en_comision'] = ''

        return cleaned_data

    def clean_comunidad(self):
        comunidad = self.cleaned_data.get('comunidad')
        return comunidad or None

    def save(self, commit=True):
        afiliado = super().save(commit=commit)

        if commit:
            comision = self.cleaned_data.get('comision')
            cargo = self.cleaned_data.get('cargo_en_comision')

            if comision:
                afiliado.comisiones.set([comision])
                afiliado.cargo_en_comision = cargo or None
            else:
                afiliado.comisiones.clear()
                afiliado.cargo_en_comision = None

            afiliado.save(update_fields=['cargo_en_comision'])

        return afiliado

class ComunidadForm(forms.ModelForm):
    class Meta:
        model = Comunidad
        fields = ['nombre', 'sector']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'sector': forms.Select(attrs={'class': 'form-control'}),
        }



class CentroVotacionForm(forms.ModelForm):
    class Meta:
        model = CentroVotacion
        fields = ['nombre', 'ubicacion', 'sectores']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'ubicacion': forms.TextInput(attrs={'class': 'form-control'}),
            'sectores': forms.SelectMultiple(attrs={
                'class': 'form-control',
                'size': 6,
            }),
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


class OrganizacionIntegranteForm(forms.ModelForm):
    dpi = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        label='DPI',
    )

    class Meta:
        model = OrganizacionIntegrante
        fields = ['estado', 'observaciones']
        widgets = {
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ComisionForm(forms.ModelForm):
    class Meta:
        model = Comision
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class SectorForm(forms.ModelForm):
    class Meta:
        model = Sector
        fields = ['nombre', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
