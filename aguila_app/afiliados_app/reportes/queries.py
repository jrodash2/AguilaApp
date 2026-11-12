"""Una sola consulta base para pantalla, estadísticas, agrupaciones y archivos."""
from datetime import date, datetime, time, timedelta

from django import forms
from django.conf import settings
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce, Concat, Replace, Substr, TruncDate
from django.utils import timezone

from .. import models
from ..utils import normalizar_dpi
from .forms import BASICAS, COLUMNAS, SECRETARIAS

INTEGRANTES = {
    'organizacion': models.OrganizacionIntegrante,
    'juventud': models.JuventudIntegrante,
    'mujeres': models.MujeresIntegrante,
    'logistica': models.LogisticaIntegrante,
    'comunicacion': models.ComunicacionIntegrante,
    'plan_hormiga': models.PlanHormigaIntegrante,
}
ORDENES = {
    'dpi': 'dpi', 'nombre': 'nombre_completo', 'edad': 'fecha_nacimiento',
    'nacimiento': 'fecha_nacimiento', 'telefono': 'telefono',
    'comunidad': 'comunidad__nombre', 'sector': 'comunidad__sector__nombre',
    'centro': 'reporte_centro_nombre', 'lider': 'lider_vinculado__nombre_completo',
    'empadronado': 'empadronado', 'creacion': 'fecha_creacion',
    'es_lider': 'es_lider_comunitario', 'cargo': 'cargo_en_comision',
    'departamento': 'reporte_departamento', 'municipio': 'reporte_municipio',
    'usuario_registro': 'usuario_registro__username',
}


def puede_reportar(user):
    # Mismo control efectivo usado por carnet y pendientes de afiliación.
    # Los decoradores legacy require_perms/require_group no restringen grupos.
    from ..views import _es_usuario_afiliacion
    return _es_usuario_afiliacion(user)


def fecha_local():
    return timezone.localdate() if settings.USE_TZ else date.today()


def edad(nacimiento, hoy):
    return hoy.year - nacimiento.year - ((hoy.month, hoy.day) < (nacimiento.month, nacimiento.day))


def hace_anios(hoy, anios):
    try:
        return hoy.replace(year=hoy.year - anios)
    except ValueError:  # 29 de febrero, año de destino no bisiesto.
        return hoy.replace(year=hoy.year - anios, day=28)


def limites_fechas(data, hoy):
    periodo = data.get('periodo')
    if periodo == 'hoy':
        return hoy, hoy
    if periodo in ('7', '30'):
        return hoy - timedelta(days=int(periodo) - 1), hoy
    if periodo == 'mes':
        siguiente = hoy.replace(day=28) + timedelta(days=4)
        return hoy.replace(day=1), siguiente.replace(day=1) - timedelta(days=1)
    if periodo == 'anterior':
        fin = hoy.replace(day=1) - timedelta(days=1)
        return fin.replace(day=1), fin
    if periodo == 'anio':
        return hoy.replace(month=1, day=1), hoy.replace(month=12, day=31)
    return data.get('desde'), data.get('hasta')


def instante(dia, fin=False):
    value = datetime.combine(dia, time.max if fin else time.min)
    return timezone.make_aware(value, timezone.get_current_timezone()) if settings.USE_TZ else value


def consulta(data, hoy=None):
    hoy = hoy or fecha_local()
    # Se prioriza el primer centro del sector (nombre, id) como en el listado existente.
    centro = models.CentroVotacion.objects.filter(
        sectores=OuterRef('comunidad__sector_id')
    ).order_by('nombre', 'pk')
    qs = models.Afiliado.objects.annotate(
        reporte_centro_id=Coalesce(Subquery(centro.values('pk')[:1]), F('centro_votacion_id')),
        reporte_dpi=Replace(Replace(Replace(F('dpi'), Value(' '), Value('')), Value('-'), Value('')), Value('\t'), Value('')),
    ).annotate(
        reporte_centro_nombre=Subquery(models.CentroVotacion.objects.filter(pk=OuterRef('reporte_centro_id')).values('nombre')[:1]),
        reporte_dpi_formato=Concat(Substr('reporte_dpi', 1, 4), Value(' '), Substr('reporte_dpi', 5, 5), Value(' '), Substr('reporte_dpi', 10, 4)),
    )
    # Reutiliza las variantes de identificación admitidas por la consulta de padrón;
    # consulta correlacionada indexada por identificacion, sin una consulta por persona.
    padron = models.PadronElectoral.objects.filter(
        Q(identificacion=OuterRef('reporte_dpi')) | Q(identificacion=OuterRef('reporte_dpi_formato'))
    ).order_by('pk')
    qs = qs.annotate(
        reporte_departamento=Subquery(padron.values('departamento')[:1]),
        reporte_municipio=Subquery(padron.values('municipio')[:1]),
        **{'secretaria_' + key: Exists(model.objects.filter(afiliado_id=OuterRef('pk')))
           for key, model in INTEGRANTES.items()},
    )
    if data.get('estructura'):
        modelos_estructura = (
            models.EstructuraIntegrante, models.EstructuraIntegranteJuventud,
            models.EstructuraIntegranteMujeres, models.EstructuraIntegranteLogistica,
            models.EstructuraIntegranteComunicacion, models.EstructuraIntegrantePlanHormiga,
        )
        match = Q()
        for i, model in enumerate(modelos_estructura):
            alias = f'reporte_estructura_{i}'
            qs = qs.alias(**{alias: Exists(model.objects.filter(
                Q(dpi=OuterRef('dpi')) | Q(dpi=OuterRef('reporte_dpi')) | Q(dpi=OuterRef('reporte_dpi_formato'))
            ))})
            match |= Q(**{alias: True})
        qs = qs.filter(match if data['estructura'] == 'si' else ~match)
    desde, hasta = limites_fechas(data, hoy)
    if data.get('usuarios'):
        qs = qs.filter(usuario_registro__in=data['usuarios'])
    if data.get('autor_registrado'):
        qs = qs.filter(usuario_registro__isnull=data['autor_registrado'] == 'no')
    if desde:
        qs = qs.filter(fecha_creacion__gte=instante(desde))
    if hasta:
        qs = qs.filter(fecha_creacion__lte=instante(hasta, fin=True))
    for filtro, field in (('comunidades', 'comunidad_id'), ('sectores', 'comunidad__sector_id'),
                           ('centros', 'reporte_centro_id'), ('lideres', 'lider_vinculado_id')):
        if data.get(filtro):
            qs = qs.filter(**{field + '__in': data[filtro]})
    for filtro, field in (('departamentos', 'reporte_departamento'), ('municipios', 'reporte_municipio')):
        if data.get(filtro):
            qs = qs.filter(**{field: data[filtro]})
    if data.get('comisiones'):
        qs = qs.filter(Exists(models.Afiliado.comisiones.through.objects.filter(
            afiliado_id=OuterRef('pk'), comision_id__in=data['comisiones'])))
    if data.get('secretarias'):
        match = Q()
        for key in data['secretarias']:
            match |= Q(**{'secretaria_' + key: True})
        qs = qs.filter(match)
    if data.get('participacion'):
        match = Q()
        for key in INTEGRANTES:
            match |= Q(**{'secretaria_' + key: True})
        qs = qs.filter(match if data['participacion'] == 'si' else ~match)
    for filtro, field in (('empadronamiento', 'empadronado'), ('es_lider', 'es_lider_comunitario')):
        if data.get(filtro):
            qs = qs.filter(**{field: data[filtro] == 'si'})
    if data.get('cargo'):
        qs = qs.filter(cargo_en_comision=data['cargo'])
    for filtro, field in (('nombre', 'nombre_completo'), ('telefono', 'telefono')):
        if data.get(filtro):
            qs = qs.filter(**{field + '__icontains': data[filtro]})
    if data.get('dpi'):
        qs = qs.filter(reporte_dpi__contains=normalizar_dpi(data['dpi']))
    if data.get('nacimiento'):
        qs = qs.filter(fecha_nacimiento=data['nacimiento'])
    lo, hi = data.get('edad_min'), data.get('edad_max')
    if data.get('rango_edad'):
        lo, hi = map(int, data['rango_edad'].split('-'))
    if lo is not None:
        qs = qs.filter(fecha_nacimiento__lte=hace_anios(hoy, lo))
    if hi is not None:
        qs = qs.filter(fecha_nacimiento__gt=hace_anios(hoy, hi + 1))
    return qs


def estadisticas(qs):
    stats = qs.aggregate(total=Count('pk'), empadronados=Count('pk', filter=Q(empadronado=True)), comunidades=Count('comunidad_id', distinct=True))
    stats['no_empadronados'] = stats['total'] - stats['empadronados']
    stats['porcentaje_empadronados'] = round(100 * stats['empadronados'] / stats['total'], 2) if stats['total'] else 0
    return stats


def columnas(data):
    if (data.get('tipo') or 'detalle') != 'detalle':
        return [('grupo', 'Agrupación'), ('total', 'Cantidad'), ('porcentaje', 'Porcentaje')]
    selected = data.get('columnas') if data.get('configuradas') or data.get('columnas') else BASICAS
    return [(key, COLUMNAS[key]) for key in selected]


def detalle(qs, data):
    key = data.get('orden') or 'nombre'
    field = ORDENES.get(key, 'nombre_completo')
    descendente = data.get('direccion') == 'desc'
    if key == 'edad':
        descendente = not descendente
    return qs.select_related('comunidad__sector', 'lider_vinculado', 'usuario_registro').prefetch_related('comisiones').order_by(('-' if descendente else '') + field, 'pk')


def fila(afiliado, keys, numero, hoy):
    values = {
        'numero': numero, 'dpi': afiliado.dpi, 'nombre': afiliado.nombre_completo,
        'usuario_registro': afiliado.usuario_registro.username if afiliado.usuario_registro else 'Sin usuario registrado',
        'edad': edad(afiliado.fecha_nacimiento, hoy), 'nacimiento': afiliado.fecha_nacimiento,
        'telefono': afiliado.telefono or '', 'comunidad': afiliado.comunidad.nombre if afiliado.comunidad else '',
        'sector': afiliado.comunidad.sector.nombre if afiliado.comunidad and afiliado.comunidad.sector else '',
        'centro': afiliado.reporte_centro_nombre or '',
        'lider': afiliado.lider_vinculado.nombre_completo if afiliado.lider_vinculado else '',
        'secretarias': ', '.join(label for key, label in SECRETARIAS if getattr(afiliado, 'secretaria_' + key)),
        'empadronado': 'Empadronado' if afiliado.empadronado else 'No empadronado',
        'creacion': timezone.localtime(afiliado.fecha_creacion).replace(tzinfo=None) if settings.USE_TZ else afiliado.fecha_creacion,
        'es_lider': 'Sí' if afiliado.es_lider_comunitario else 'No',
        'comisiones': ', '.join(c.nombre for c in afiliado.comisiones.all()),
        'cargo': afiliado.get_cargo_en_comision_display() or '',
        'departamento': afiliado.reporte_departamento or '', 'municipio': afiliado.reporte_municipio or '',
    }
    return [values[key] for key in keys]


def agrupados(qs, data, total):
    tipo = data['tipo']
    if tipo == 'secretaria':
        counts = qs.aggregate(**{key: Count('pk', filter=Q(**{'secretaria_' + key: True})) for key, _ in SECRETARIAS})
        sin = qs.filter(**{'secretaria_' + key: False for key, _ in SECRETARIAS}).count()
        rows = [{'grupo': label, 'total': counts[key]} for key, label in SECRETARIAS if counts[key]]
        if sin:
            rows.append({'grupo': 'Sin secretaría', 'total': sin})
    else:
        fields = {
            'comunidad': ('comunidad_id', 'comunidad__nombre'),
            'lider': ('lider_vinculado_id', 'lider_vinculado__nombre_completo'),
            'centro': ('reporte_centro_id', 'reporte_centro_nombre'),
            'empadronamiento': ('empadronado',), 'fecha': ('reporte_dia',),
        }[tipo]
        if tipo == 'fecha':
            qs = qs.annotate(reporte_dia=TruncDate('fecha_creacion'))
        rows = []
        for group in qs.order_by().values(*fields).annotate(total=Count('pk')).iterator(chunk_size=1000):
            label = group[fields[-1]]
            if tipo == 'empadronamiento':
                label = 'Empadronado' if label else 'No empadronado'
            rows.append({'grupo': str(label) if label is not None else 'Sin asignar', 'total': group['total']})
    for row in rows:
        row['porcentaje'] = round(100 * row['total'] / total, 2) if total else 0
    order = data.get('orden') or ('grupo' if tipo == 'fecha' else 'total')
    key = order if order in ('grupo', 'total', 'porcentaje') else 'grupo'
    reverse = data.get('direccion') == 'desc' if data.get('direccion') else key != 'grupo'
    return sorted(rows, key=lambda r: (r[key], r['grupo']), reverse=reverse)


def resumen_filtros(form):
    """Descripción para el archivo privado; nunca se envía al logger de auditoría."""
    parts = []
    for name, field in form.fields.items():
        value = form.cleaned_data.get(name)
        if name in ('pagina', 'cantidad', 'columnas', 'configuradas', 'orden', 'direccion') or value in (None, '', [], False):
            continue
        if hasattr(value, 'model'):
            value = ', '.join(getattr(obj, 'nombre_completo', None) or getattr(obj, 'nombre', None) or getattr(obj, 'username', str(obj.pk)) for obj in value)
        elif isinstance(field, forms.ChoiceField):
            choices = dict(field.choices)
            value = ', '.join(str(choices.get(v, v)) for v in value) if isinstance(value, list) else choices.get(value, value)
        parts.append(f'{field.label}: {value}')
    return '; '.join(parts) or 'Sin filtros'
