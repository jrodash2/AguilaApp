import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from django.conf import settings
from django.http import FileResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from ..models import Institucion
from .queries import detalle, fila, resumen_filtros


def filas(qs, data, cols, grupos, hoy):
    keys = [key for key, _ in cols]
    if grupos is not None:
        for group in grupos:
            yield [group[key] for key in keys]
    else:
        for index, obj in enumerate(detalle(qs, data).iterator(chunk_size=500), 1):
            yield fila(obj, keys, index, hoy)


def texto_seguro(value):
    if not isinstance(value, str):
        return value
    # Fuerza texto en Excel, y elimina controles que XML no admite.
    return ''.join(c for c in value if ord(c) >= 32 or c in '\t\n\r')[:32767]


def metadata(user, form, total):
    institucion = Institucion.objects.only('nombre').first()
    now = timezone.localtime() if settings.USE_TZ else timezone.now()
    return [
        institucion.nombre if institucion else 'AguilaApp', 'Reporte de Afiliados',
        f'Generado: {now:%d/%m/%Y %H:%M:%S} · Usuario: {user.get_username()}',
        resumen_filtros(form), f'Total de afiliados filtrados: {total}',
    ]


def registrar_exportacion(user, formato, form, total):
    # Archivo privado, fuera de media/static. No registrar nombres, DPI, teléfonos,
    # fechas de nacimiento ni parámetros GET sin depurar.
    path = Path(getattr(settings, 'REPORTES_AUDIT_LOG', Path(tempfile.gettempdir()) / 'aguila-reportes' / 'audit.jsonl'))
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    active = {}
    for key, value in form.cleaned_data.items():
        if key in ('pagina', 'cantidad', 'orden', 'direccion', 'configuradas', 'columnas') or value in (None, '', [], False):
            continue
        if key in ('nombre', 'dpi', 'telefono', 'nacimiento', 'lideres'):
            active[key] = 'aplicado; valor omitido'
        elif hasattr(value, 'model'):
            active[key] = list(value.values_list('pk', flat=True))
        else:
            active[key] = value
    record = {'fecha': timezone.now().isoformat(), 'usuario_id': user.pk, 'formato': formato,
              'filtros': active, 'columnas': form.cleaned_data.get('columnas') or [], 'cantidad': total}
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(fd, 'a', encoding='utf-8') as log:
        log.write(json.dumps(record, ensure_ascii=False, default=str) + '\n')


def excel(user, form, qs, cols, grupos, total, hoy):
    output = tempfile.TemporaryFile()
    wb = Workbook(write_only=True)
    ws = wb.create_sheet('Afiliados')
    info = metadata(user, form, total)
    header_row = len(info) + 2
    ws.freeze_panes = f'A{header_row + 1}'
    for i, (key, label) in enumerate(cols, 1):
        ws.column_dimensions[get_column_letter(i)].width = min(45, max(16, len(label) + 5))
    def cell(value, heading=False):
        c = WriteOnlyCell(ws, value=texto_seguro(value))
        if isinstance(value, str):
            c.data_type = 's'  # Incluye textos que comienzan con =, +, -, @ o tabulador.
            c.number_format = '@'
        if isinstance(value, datetime):
            c.number_format = 'dd/mm/yyyy hh:mm'
        elif isinstance(value, date):
            c.number_format = 'dd/mm/yyyy'
        c.alignment = Alignment(vertical='top', wrap_text=True)
        c.border = Border(bottom=Side(style='hair', color='DDE3EA'))
        if heading:
            c.font = Font(color='FFFFFF', bold=True)
            c.fill = PatternFill('solid', fgColor='006A67')
        return c
    for value in info:
        ws.append([cell(value)])
    ws.append([])
    ws.append([cell(label, heading=True) for _, label in cols])
    count = 0
    for row in filas(qs, form.cleaned_data, cols, grupos, hoy):
        ws.append([cell(v) for v in row])
        count += 1
    ws.auto_filter.ref = f'A{header_row}:{get_column_letter(len(cols))}{header_row + count}'
    wb.save(output)
    output.seek(0)
    return output


def pdf(user, form, qs, cols, grupos, total, hoy):
    output = tempfile.TemporaryFile()
    pagesize = landscape(A4) if len(cols) > 4 else A4
    doc = SimpleDocTemplate(output, pagesize=pagesize, rightMargin=24, leftMargin=24,
                            topMargin=30, bottomMargin=32, title='Reporte de Afiliados')
    styles = getSampleStyleSheet()
    tiny = ParagraphStyle('ReporteCelda', fontName='Helvetica', fontSize=7, leading=9, wordWrap='CJK')
    info = metadata(user, form, total)
    story = [Paragraph(escape(v), styles['Title'] if i == 1 else styles['Normal']) for i, v in enumerate(info)]
    if form.cleaned_data.get('tipo') == 'secretaria':
        story.append(Paragraph('Un afiliado puede pertenecer a varias secretarías. Las agrupaciones se superponen.', styles['Normal']))
    story.append(Spacer(1, 10))
    def paragraph(value):
        if isinstance(value, datetime):
            value = value.strftime('%d/%m/%Y %H:%M')
        elif isinstance(value, date):
            value = value.strftime('%d/%m/%Y')
        return Paragraph(escape(str(value)), tiny)
    # Límite de filas previo a generar PDF; tablas por lotes para no crear una
    # tabla monolítica. Paragraph ajusta y escapa todos los textos de las celdas.
    header = [paragraph(label) for _, label in cols]
    batch = [header]
    def table(rows):
        item = LongTable(rows, colWidths=[doc.width / len(cols)] * len(cols), repeatRows=1, hAlign='LEFT', splitInRow=1)
        item.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#D9EFED')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CED4DA')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F7FA')]),
        ]))
        return item
    for row in filas(qs, form.cleaned_data, cols, grupos, hoy):
        batch.append([paragraph(value) for value in row])
        if len(batch) == 101:
            story.append(table(batch))
            batch = [header]
    if len(batch) > 1 or not any(isinstance(item, LongTable) for item in story):
        story.append(table(batch))
    def footer(canvas, document):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.drawString(24, 16, f'AguilaApp · Total: {total}')
        canvas.drawRightString(pagesize[0] - 24, 16, f'Página {document.page}')
        canvas.restoreState()
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return output


def descargar(user, formato, form, qs, cols, grupos, total, hoy):
    output = (excel if formato == 'xlsx' else pdf)(user, form, qs, cols, grupos, total, hoy)
    try:
        registrar_exportacion(user, formato, form, total)
    except Exception:
        output.close()
        raise
    stamp = (timezone.localtime() if settings.USE_TZ else timezone.now()).strftime('%Y%m%d_%H%M%S')
    response = FileResponse(output, as_attachment=True, filename=f'reporte_afiliados_{stamp}.{formato}')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Report-Total'] = str(total)
    return response
