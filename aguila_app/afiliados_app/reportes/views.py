from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from ..models import Afiliado, CentroVotacion, Comision, Comunidad, Sector
from .exports import descargar
from .forms import BASICAS, COLUMNAS, FiltrosReporteForm
from .queries import agrupados, columnas, consulta, detalle, estadisticas, fecha_local, fila, puede_reportar


def autorizar(user):
    if not puede_reportar(user):
        raise PermissionDenied('No tiene permisos para consultar reportes de afiliación.')


def validar(request):
    form = FiltrosReporteForm(request.GET)
    if not form.is_valid():
        return form, JsonResponse({'error': 'Revise los filtros indicados.', 'campos': form.errors.get_json_data()}, status=400)
    return form, None


@login_required
@never_cache
@require_GET
def pantalla(request):
    autorizar(request.user)
    form = FiltrosReporteForm()
    blocks = [
        ('Fechas', ['periodo', 'desde', 'hasta']),
        ('Ubicación', ['departamentos', 'municipios', 'sectores', 'comunidades', 'centros']),
        ('Organización', ['lideres', 'secretarias', 'comisiones', 'cargo', 'es_lider', 'participacion', 'estructura']),
        ('Datos personales', ['nombre', 'dpi', 'telefono', 'rango_edad', 'edad_min', 'edad_max', 'nacimiento']),
        ('Empadronamiento', ['empadronamiento']),
    ]
    return render(request, 'afiliados/reportes_avanzados.html', {
        'bloques': [(label, [form[name] for name in names]) for label, names in blocks],
        'form': form, 'columnas_reporte': COLUMNAS, 'columnas_basicas': list(BASICAS),
        'limite_excel': getattr(settings, 'REPORTES_MAX_EXCEL', 100000),
        'limite_pdf': getattr(settings, 'REPORTES_MAX_PDF', 2000),
    })


@login_required
@never_cache
@require_GET
def datos(request):
    autorizar(request.user)
    form, error = validar(request)
    if error:
        return error
    data = form.cleaned_data
    hoy = fecha_local()
    qs = consulta(data, hoy)
    stats = estadisticas(qs)
    cols = columnas(data)
    grupos = agrupados(qs, data, stats['total']) if data.get('tipo') not in ('', None, 'detalle') else None
    paginator = Paginator(grupos if grupos is not None else detalle(qs, data), data.get('cantidad') or 25)
    page = paginator.get_page(data.get('pagina') or 1)
    keys = [key for key, _ in cols]
    rows = [[obj[key] for key in keys] for obj in page] if grupos is not None else [fila(obj, keys, page.start_index() + i, hoy) for i, obj in enumerate(page)]
    chart = sorted(grupos, key=lambda row: row['total'], reverse=True)[:15] if grupos is not None else []
    if data.get('tipo') == 'fecha':
        chart = sorted(grupos, key=lambda row: row['grupo'])[-15:]
    return JsonResponse({
        'columnas': cols, 'filas': rows, 'estadisticas': stats,
        'pagina': page.number, 'paginas': paginator.num_pages, 'total_filas': paginator.count,
        'grafico': chart, 'tipo': data.get('tipo') or 'detalle',
        'nota': 'Las secretarías se superponen: una persona puede pertenecer a varias.' if data.get('tipo') == 'secretaria' else '',
    })


@login_required
@never_cache
@require_GET
def exportar(request, formato):
    autorizar(request.user)
    form, error = validar(request)
    if error:
        return error
    hoy = fecha_local()
    qs = consulta(form.cleaned_data, hoy)
    total = qs.count()
    limit = getattr(settings, 'REPORTES_MAX_EXCEL' if formato == 'xlsx' else 'REPORTES_MAX_PDF', 100000 if formato == 'xlsx' else 2000)
    if total > limit:
        return JsonResponse({'error': f'El límite de esta descarga es {limit:,} afiliados. Acote los filtros.'}, status=400)
    cols = columnas(form.cleaned_data)
    if formato == 'pdf' and len(cols) > 8:
        return JsonResponse({'error': 'El PDF admite hasta 8 columnas para mantener la legibilidad. Configure las columnas o descargue Excel.'}, status=400)
    grupos = agrupados(qs, form.cleaned_data, total) if form.cleaned_data.get('tipo') not in ('', None, 'detalle') else None
    return descargar(request.user, formato, form, qs, cols, grupos, total, hoy)


@login_required
@never_cache
@require_GET
def opciones(request):
    autorizar(request.user)
    catalogo = request.GET.get('catalogo')
    if catalogo not in ('comunidades', 'sectores', 'centros', 'lideres', 'comisiones'):
        return JsonResponse({'error': 'Catálogo inválido.'}, status=400)
    try:
        page = int(request.GET.get('pagina', 1))
        ids = [int(value) for value in request.GET.getlist('sectores')]
        if page < 1 or page > 100000 or len(ids) > 100:
            raise ValueError
    except ValueError:
        return JsonResponse({'error': 'Parámetros inválidos.'}, status=400)
    model, name = {'comunidades': (Comunidad, 'nombre'), 'sectores': (Sector, 'nombre'),
                   'centros': (CentroVotacion, 'nombre'), 'lideres': (Afiliado, 'nombre_completo'), 'comisiones': (Comision, 'nombre')}[catalogo]
    qs = model.objects.all()
    if catalogo == 'lideres':
        qs = qs.filter(es_lider_comunitario=True)
    if catalogo == 'comunidades' and ids:
        qs = qs.filter(sector_id__in=ids)
    if catalogo == 'centros' and ids:
        qs = qs.filter(sectores__in=ids).distinct()
    qs = qs.filter(**{name + '__icontains': request.GET.get('q', '')[:150]}).order_by(name, 'pk')
    start = (page - 1) * 30
    items = list(qs.values('pk', name)[start:start + 31])
    return JsonResponse({'results': [{'id': item['pk'], 'text': item[name]} for item in items[:30]], 'pagination': {'more': len(items) > 30}})
