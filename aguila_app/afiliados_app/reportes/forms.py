from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from ..models import Afiliado, CentroVotacion, Comision, Comunidad, Sector

SECRETARIAS = (
    ('organizacion', 'Organización'), ('juventud', 'Juventud'),
    ('mujeres', 'Mujeres'), ('logistica', 'Logística'),
    ('comunicacion', 'Comunicación'), ('plan_hormiga', 'Plan Hormiga'),
)
TIPOS = (
    ('detalle', 'Detallado de afiliados'), ('comunidad', 'Resumen por comunidad'),
    ('lider', 'Resumen por líder'), ('secretaria', 'Resumen por secretaría'),
    ('centro', 'Resumen por centro de votación'), ('fecha', 'Resumen por fecha de registro'),
    ('empadronamiento', 'Resumen por empadronamiento'),
)
COLUMNAS = {
    'numero': 'N.º', 'dpi': 'DPI', 'nombre': 'Nombre completo', 'edad': 'Edad',
    'nacimiento': 'Fecha de nacimiento', 'telefono': 'Teléfono',
    'comunidad': 'Comunidad', 'sector': 'Sector', 'centro': 'Centro de votación',
    'lider': 'Líder responsable', 'secretarias': 'Secretarías (integrantes)',
    'empadronado': 'Empadronamiento', 'creacion': 'Fecha de registro',
    'es_lider': 'Es líder comunitario', 'comisiones': 'Comisiones',
    'cargo': 'Cargo en comisión', 'departamento': 'Departamento (padrón)',
    'municipio': 'Municipio (padrón)',
    'usuario_registro': 'Agregado por',
}
BASICAS = ('dpi', 'nombre', 'comunidad', 'telefono', 'lider', 'creacion')


class SeleccionRemota(forms.SelectMultiple):
    """Renderiza solo opciones seleccionadas; Select2 pagina el catálogo por AJAX."""
    def optgroups(self, name, value, attrs=None):
        if hasattr(self.choices, 'queryset'):
            self.choices = forms.models.ModelChoiceIterator(self.choices.field)
            originales = self.choices
            # No evaluar todo el catálogo para construir el HTML.
            self.choices = [(str(obj.pk), self.choices.field.label_from_instance(obj))
                            for obj in self.choices.queryset.filter(pk__in=[v for v in value if str(v).isdigit()])]
            try:
                return super().optgroups(name, value, attrs)
            finally:
                self.choices = originales
        return super().optgroups(name, value, attrs)


def multiple(model, label, **filters):
    return forms.ModelMultipleChoiceField(
        queryset=model.objects.filter(**filters), required=False, label=label,
        widget=SeleccionRemota(attrs={'class': 'form-select reporte-remoto'}),
    )


class FiltrosReporteForm(forms.Form):
    periodo = forms.ChoiceField(required=False, label='Período', choices=(
        ('', 'Todas las fechas'), ('hoy', 'Registrados hoy'), ('7', 'Últimos 7 días'),
        ('30', 'Últimos 30 días'), ('mes', 'Mes actual'), ('anterior', 'Mes anterior'),
        ('anio', 'Año actual'), ('personalizado', 'Rango personalizado'),
    ))
    desde = forms.DateField(required=False, label='Fecha inicial', widget=forms.DateInput(attrs={'type': 'date'}))
    hasta = forms.DateField(required=False, label='Fecha final', widget=forms.DateInput(attrs={'type': 'date'}))
    departamentos = forms.CharField(required=False, max_length=100, label='Departamento (padrón)')
    municipios = forms.CharField(required=False, max_length=100, label='Municipio (padrón)')
    comunidades = multiple(Comunidad, 'Comunidades')
    sectores = multiple(Sector, 'Sectores')
    centros = multiple(CentroVotacion, 'Centros de votación')
    lideres = multiple(Afiliado, 'Líderes responsables', es_lider_comunitario=True)
    usuarios = multiple(User, 'Usuarios que agregaron afiliados')
    autor_registrado = forms.ChoiceField(required=False, label='Usuario de registro identificado', choices=(('', 'Todos'), ('si', 'Con usuario registrado'), ('no', 'Sin usuario registrado')))
    secretarias = forms.MultipleChoiceField(required=False, choices=SECRETARIAS, label='Secretarías (pertenencia como integrante)')
    comisiones = multiple(Comision, 'Comisiones')
    es_lider = forms.ChoiceField(required=False, label='Es líder comunitario', choices=(('', 'Todos'), ('si', 'Sí'), ('no', 'No')))
    participacion = forms.ChoiceField(required=False, label='Participa como integrante de secretaría', choices=(('', 'Todos'), ('si', 'Sí'), ('no', 'No')))
    estructura = forms.ChoiceField(required=False, label='Participa en estructura (coincidencia de DPI)', choices=(('', 'Todos'), ('si', 'Sí'), ('no', 'No')))
    cargo = forms.ChoiceField(required=False, label='Cargo en comisión', choices=(('', 'Todos'), *Afiliado.CargoComision.choices))
    nombre = forms.CharField(required=False, max_length=150, label='Nombre completo (incluye apellidos)')
    dpi = forms.RegexField(r'^[0-9\s-]*$', required=False, max_length=20, label='DPI', error_messages={'invalid': 'Utilice dígitos, espacios o guiones.'})
    telefono = forms.CharField(required=False, max_length=20, label='Teléfono')
    edad_min = forms.IntegerField(required=False, min_value=0, max_value=130, label='Edad mínima')
    edad_max = forms.IntegerField(required=False, min_value=0, max_value=130, label='Edad máxima')
    rango_edad = forms.ChoiceField(required=False, label='Rango de edad', choices=(('', 'Todas las edades'), ('0-17', 'Menores de 18'), ('18-35', '18 a 35 años'), ('36-59', '36 a 59 años'), ('60-130', '60 años o más')))
    nacimiento = forms.DateField(required=False, label='Fecha de nacimiento', widget=forms.DateInput(attrs={'type': 'date'}))
    empadronamiento = forms.ChoiceField(required=False, label='Empadronamiento registrado', choices=(('', 'Todos'), ('si', 'Empadronados'), ('no', 'No empadronados')))
    tipo = forms.ChoiceField(required=False, label='Tipo de reporte', choices=TIPOS)
    columnas = forms.MultipleChoiceField(required=False, choices=tuple(COLUMNAS.items()))
    configuradas = forms.BooleanField(required=False)
    pagina = forms.IntegerField(required=False, min_value=1)
    cantidad = forms.TypedChoiceField(required=False, coerce=int, choices=((10, '10'), (25, '25'), (50, '50'), (100, '100')))
    orden = forms.ChoiceField(required=False, choices=tuple((k, v) for k, v in COLUMNAS.items() if k not in ('numero', 'secretarias', 'comisiones')) + (('grupo', 'Agrupación'), ('total', 'Cantidad'), ('porcentaje', 'Porcentaje')))
    direccion = forms.ChoiceField(required=False, choices=(('asc', 'Ascendente'), ('desc', 'Descendente')))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-select' if isinstance(field.widget, forms.Select) else 'form-control')
            if name in ('comunidades', 'sectores', 'centros', 'lideres', 'comisiones', 'usuarios'):
                field.widget.attrs['data-catalogo'] = name

    def clean(self):
        data = super().clean()
        unknown = set(self.data) - set(self.fields)
        if unknown:
            raise ValidationError('Se recibieron filtros no admitidos.')
        if len(self.data.urlencode()) > 12000:
            raise ValidationError('La selección de filtros es demasiado extensa.')
        for field in ('comunidades', 'sectores', 'centros', 'lideres', 'comisiones', 'secretarias', 'usuarios'):
            if len(self.data.getlist(field)) > 100:
                self.add_error(field, 'Seleccione como máximo 100 valores por filtro.')
        if data.get('desde') and data.get('hasta') and data['desde'] > data['hasta']:
            self.add_error('hasta', 'La fecha final debe ser igual o posterior a la inicial.')
        if data.get('periodo') not in ('', None, 'personalizado') and (data.get('desde') or data.get('hasta')):
            self.add_error('periodo', 'Use rango personalizado para indicar fechas inicial y final.')
        if data.get('periodo') == 'personalizado' and not (data.get('desde') or data.get('hasta')):
            self.add_error('desde', 'Indique al menos una fecha para el rango personalizado.')
        lo, hi = data.get('edad_min'), data.get('edad_max')
        if lo is not None and hi is not None and lo > hi:
            self.add_error('edad_max', 'La edad máxima debe ser igual o mayor que la mínima.')
        if data.get('rango_edad') and (lo is not None or hi is not None):
            self.add_error('rango_edad', 'Use un rango predefinido o edades mínima y máxima.')
        if data.get('configuradas') and not data.get('columnas') and data.get('tipo', 'detalle') in ('', 'detalle'):
            self.add_error('columnas', 'Seleccione al menos una columna.')
        return data
