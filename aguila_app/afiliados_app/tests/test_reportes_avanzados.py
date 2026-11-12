import datetime
import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.db import connection
from django.http import QueryDict
from django.test import TestCase, override_settings
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook
from pypdf import PdfReader

from afiliados_app.models import (
    Afiliado, CentroVotacion, Comision, Comunidad, EstructuraIntegrante,
    EstructuraOrganizativa, JuventudIntegrante,
    OrganizacionIntegrante, PadronElectoral, Sector,
)
from afiliados_app.reportes.forms import FiltrosReporteForm
from afiliados_app.reportes.queries import consulta, edad


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class ReportesAvanzadosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('reportes', password='clave')
        cls.user.groups.add(Group.objects.create(name='afiliados'))
        cls.otro = User.objects.create_user('sin-reportes')
        cls.sector = Sector.objects.create(nombre='Sector central')
        cls.c1 = Comunidad.objects.create(nombre='Comunidad Uno', sector=cls.sector)
        cls.c2 = Comunidad.objects.create(nombre='Comunidad Dos')
        cls.c3 = Comunidad.objects.create(nombre='Comunidad Tres')
        cls.centro = CentroVotacion.objects.create(nombre='Centro derivado', ubicacion='Local')
        cls.centro.sectores.add(cls.sector)
        cls.directo = CentroVotacion.objects.create(nombre='Centro directo', ubicacion='Otro')
        cls.lider = Afiliado.objects.create(nombre_completo='Líder central', dpi='0000000000001', fecha_nacimiento='1980-01-01', direccion='Local', es_lider_comunitario=True)
        cls.a = Afiliado.objects.create(nombre_completo='Ana Apellido', dpi='0123 45678 9012', fecha_nacimiento='2000-11-12', telefono='00123456', direccion='Local', comunidad=cls.c1, centro_votacion=cls.directo, lider_vinculado=cls.lider, empadronado=True)
        cls.b = Afiliado.objects.create(nombre_completo='Beatriz Apellido', dpi='0000000000003', fecha_nacimiento='1990-11-13', direccion='Local', comunidad=cls.c2)
        cls.c = Afiliado.objects.create(nombre_completo='Carlos Apellido', dpi='0000000000004', fecha_nacimiento='2010-01-01', direccion='Local', comunidad=cls.c3)
        cls.com1 = Comision.objects.create(nombre='Comisión A')
        cls.com2 = Comision.objects.create(nombre='Comisión B')
        cls.a.comisiones.add(cls.com1, cls.com2)
        OrganizacionIntegrante.objects.create(afiliado=cls.a, usuario_registro=cls.user)
        JuventudIntegrante.objects.create(afiliado=cls.a, usuario_registro=cls.user)
        PadronElectoral.objects.create(identificacion='0123 45678 9012', nombre='Ana Apellido', departamento='El Progreso', municipio='San Agustín')
        # Día final en Guatemala: corresponde a las primeras horas del día siguiente en UTC.
        Afiliado.objects.filter(pk=cls.a.pk).update(fecha_creacion=datetime.datetime(2026, 10, 1, 5, 59, 59, tzinfo=datetime.timezone.utc))
        Afiliado.objects.filter(pk=cls.b.pk).update(fecha_creacion=datetime.datetime(2026, 10, 1, 6, 0, tzinfo=datetime.timezone.utc))

    def setUp(self):
        self.client.force_login(self.user)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.audit = Path(self.tmp.name) / 'audit.jsonl'
        self.override = override_settings(REPORTES_AUDIT_LOG=self.audit)
        self.override.enable()
        self.addCleanup(self.override.disable)

    def url(self, endpoint='datos'):
        return reverse('afiliados:reportes_avanzados' + ('_' + endpoint if endpoint else ''))

    def data(self, **kwargs):
        response = self.client.get(self.url(), kwargs)
        self.assertEqual(response.status_code, 200, response.content[:800])
        return response.json()

    def archivo(self, fmt, **kwargs):
        response = self.client.get(self.url(fmt), kwargs)
        self.assertEqual(response.status_code, 200)
        output = b''.join(response.streaming_content)
        response.close()
        return response, output

    def test_sin_filtros_y_pantalla_riho(self):
        self.assertEqual(self.data()['estadisticas']['total'], 4)
        response = self.client.get(self.url(''))
        self.assertContains(response, 'Reportes Avanzados de Afiliados')
        self.assertContains(response, 'reportes_avanzados.js')
        self.assertContains(response, 'select2.full.min.js')

    def test_fechas_incluyen_fin_local_y_excluyen_siguiente_dia(self):
        data = self.data(periodo='personalizado', desde='2026-09-01', hasta='2026-09-30')
        self.assertEqual(data['estadisticas']['total'], 1)
        self.assertEqual(data['filas'][0][1], 'Ana Apellido')

    def test_periodos_predefinidos_y_fechas_invalidas(self):
        from afiliados_app.reportes.queries import limites_fechas
        hoy = datetime.date(2026, 11, 12)
        self.assertEqual(limites_fechas({'periodo': '7'}, hoy), (datetime.date(2026, 11, 6), hoy))
        self.assertEqual(limites_fechas({'periodo': 'anterior'}, hoy), (datetime.date(2026, 10, 1), datetime.date(2026, 10, 31)))
        for params in ({'desde': 'xxx'}, {'desde': '2026-11-12', 'hasta': '2026-01-01'}, {'periodo': 'hoy', 'desde': '2026-01-01'}, {'edad_min': 'a'}, {'edad_min': 50, 'edad_max': 18}, {'rango_edad': '18-35', 'edad_min': 18}, {'tipo': 'inventado'}, {'pagina': '-1'}, {'orden': 'dpi;DROP TABLE'}, {'sexo': 'femenino'}):
            with self.subTest(params=params):
                self.assertEqual(self.client.get(self.url(), params).status_code, 400)

    def test_comunidades_multiples_or_y_sector(self):
        self.assertEqual(self.data(comunidades=[self.c1.pk])['estadisticas']['total'], 1)
        self.assertEqual(self.data(comunidades=[self.c1.pk, self.c2.pk, self.c3.pk])['estadisticas']['total'], 3)
        self.assertEqual(self.data(comunidades=[self.c1.pk, self.c2.pk], sectores=[self.sector.pk])['estadisticas']['total'], 1)

    def test_lider_y_empadronamiento(self):
        self.assertEqual(self.data(lideres=[self.lider.pk])['estadisticas']['total'], 1)
        self.assertEqual(self.data(empadronamiento='si')['estadisticas']['total'], 1)
        self.assertEqual(self.data(empadronamiento='no')['estadisticas']['total'], 3)
        self.assertEqual(self.client.get(self.url(), {'lideres': [self.b.pk]}).status_code, 400)

    def test_edades_nacimiento_y_29_febrero(self):
        with patch('afiliados_app.reportes.views.fecha_local', return_value=datetime.date(2026, 11, 12)):
            self.assertEqual(self.data(edad_min=26, edad_max=26)['estadisticas']['total'], 1)
            self.assertEqual(self.data(rango_edad='18-35')['estadisticas']['total'], 2)
            self.assertEqual(self.data(nacimiento='2000-11-12')['estadisticas']['total'], 1)
        self.assertEqual(edad(datetime.date(2000, 2, 29), datetime.date(2025, 2, 28)), 24)
        self.assertEqual(edad(datetime.date(2000, 2, 29), datetime.date(2025, 3, 1)), 25)

    def test_siete_filtros_combinados_y_dpi_normalizado(self):
        data = self.data(desde='2026-09-01', hasta='2026-09-30', comunidades=[self.c1.pk], lideres=[self.lider.pk], empadronamiento='si', comisiones=[self.com1.pk, self.com2.pk], dpi='0123456789012', telefono='0012', departamentos='El Progreso', municipios='San Agustín')
        self.assertEqual(data['estadisticas']['total'], 1)
        self.assertEqual(len(data['filas']), 1)

    def test_centro_resuelto_prioriza_sector_en_filtro_columna_y_grupo(self):
        self.assertEqual(self.data(centros=[self.centro.pk])['estadisticas']['total'], 1)
        self.assertEqual(self.data(centros=[self.directo.pk])['estadisticas']['total'], 0)
        data = self.data(centros=[self.centro.pk], columnas=['centro'], configuradas='on')
        self.assertEqual(data['filas'], [['Centro derivado']])
        self.assertEqual(self.data(tipo='centro', centros=[self.centro.pk])['filas'][0][0], 'Centro derivado')

    def test_secretarias_comisiones_sin_duplicados_y_porcentajes(self):
        data = self.data(secretarias=['organizacion', 'juventud'], comisiones=[self.com1.pk, self.com2.pk])
        self.assertEqual(data['estadisticas']['total'], 1)
        groups = self.data(tipo='secretaria', comunidades=[self.c1.pk])
        self.assertEqual(groups['estadisticas']['total'], 1)
        self.assertEqual(len(groups['filas']), 2)
        self.assertTrue(all(row[1:] == [1, 100.0] for row in groups['filas']))
        self.assertIn('superponen', groups['nota'])
        self.assertEqual(self.data(participacion='no')['estadisticas']['total'], 3)

    def test_participacion_estructura_por_dpi_no_duplica(self):
        for nombre in ('Estructura A', 'Estructura B'):
            estructura = EstructuraOrganizativa.objects.create(nombre=nombre, tipo_estructura='Comité', usuario_creador=self.user)
            EstructuraIntegrante.objects.create(estructura=estructura, dpi='0123456789012', nombre_completo='Ana Apellido', usuario_registro=self.user)
        self.assertEqual(self.data(estructura='si')['estadisticas']['total'], 1)
        self.assertEqual(self.data(estructura='no')['estadisticas']['total'], 3)

    def test_padron_normalizado_y_agrupacion_con_centro_compartido(self):
        PadronElectoral.objects.filter(nombre='Ana Apellido').update(identificacion='0123456789012')
        self.assertEqual(self.data(departamentos='El Progreso')['estadisticas']['total'], 1)
        Afiliado.objects.filter(pk=self.b.pk).update(comunidad=self.c1, centro_votacion=None)
        result = self.data(tipo='centro', comunidades=[self.c1.pk])
        self.assertEqual(result['filas'], [['Centro derivado', 2, 100.0]])

    def test_reportes_agrupados_coinciden_con_total_y_tienen_grafico(self):
        for tipo in ('comunidad', 'lider', 'centro', 'fecha', 'empadronamiento'):
            with self.subTest(tipo=tipo):
                data = self.data(tipo=tipo)
                self.assertEqual(sum(row[1] for row in data['filas']), 4)
                self.assertAlmostEqual(sum(row[2] for row in data['filas']), 100)
                self.assertTrue(data['grafico'])
                self.assertEqual(len(data['columnas']), 3)

    def test_vacio_y_paginacion_y_orden(self):
        self.assertEqual(self.data(nombre='inexistente')['filas'], [])
        _, content = self.archivo('excel', nombre='inexistente')
        self.assertEqual(load_workbook(io.BytesIO(content)).active.max_row, 7)
        _, content = self.archivo('pdf', nombre='inexistente', tipo='secretaria')
        text = '\n'.join(page.extract_text() for page in PdfReader(io.BytesIO(content)).pages)
        self.assertIn('Agrupación', text)
        data = self.data(cantidad=10, orden='edad', direccion='asc', columnas=['nombre', 'edad'], configuradas='on')
        self.assertEqual(data['filas'][0][0], 'Carlos Apellido')
        for key in ('dpi', 'nombre', 'nacimiento', 'centro', 'departamento', 'municipio'):
            self.data(orden=key, direccion='desc')

    def test_validacion_ids_y_columnas(self):
        for params in ({'comunidades': ['999999']}, {'comunidades': ['x']}, {'secretarias': ['x']}, {'columnas': ['password']}, {'configuradas': 'on'}, {'cantidad': 100000}):
            self.assertEqual(self.client.get(self.url(), params).status_code, 400)

    def test_excel_completo_texto_fechas_y_seleccion(self):
        response, content = self.archivo('excel', comunidades=[self.c1.pk], configuradas='on', columnas=['dpi', 'nombre', 'telefono', 'creacion', 'nacimiento'])
        self.assertEqual(response['X-Report-Total'], '1')
        wb = load_workbook(io.BytesIO(content))
        ws = wb.active
        self.assertEqual([c.value for c in ws[7]], ['DPI', 'Nombre completo', 'Teléfono', 'Fecha de registro', 'Fecha de nacimiento'])
        self.assertEqual(ws['A8'].value, '0123 45678 9012')
        self.assertEqual(ws['A8'].data_type, 's')
        self.assertEqual(ws['C8'].value, '00123456')
        self.assertIsInstance(ws['D8'].value, datetime.datetime)
        self.assertEqual(ws.freeze_panes, 'A8')
        self.assertEqual(ws.auto_filter.ref, 'A7:E8')
        self.assertEqual(ws.max_row, 8)
        self.assertIn('private', response['Cache-Control'])

    def test_inyeccion_excel_y_auditoria_sin_datos_personales(self):
        Afiliado.objects.filter(pk=self.a.pk).update(nombre_completo='=HYPERLINK("evil")', telefono='+00123456')
        _, content = self.archivo('excel', nombre='HYPERLINK', dpi='0123', telefono='+001', columnas=['nombre', 'telefono'], configuradas='on')
        ws = load_workbook(io.BytesIO(content)).active
        self.assertEqual(ws['A8'].data_type, 's')
        self.assertEqual(ws['B8'].data_type, 's')
        audit = self.audit.read_text()
        self.assertNotIn('HYPERLINK', audit)
        self.assertNotIn('0123', audit)
        self.assertNotIn('+001', audit)
        record = json.loads(audit)
        self.assertEqual(record['usuario_id'], self.user.pk)
        self.assertEqual(record['cantidad'], 1)

    def test_pdf_valido_todas_las_filas_y_grupos_exportables(self):
        response, content = self.archivo('pdf', columnas=['nombre', 'dpi', 'comunidad'], configuradas='on')
        self.assertEqual(response['Content-Type'], 'application/pdf')
        reader = PdfReader(io.BytesIO(content))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn('Ana Apellido', text)
        self.assertIn('Carlos Apellido', text)
        self.assertIn('Página 1', text)
        self.assertIn('Total de afiliados filtrados: 4', text)
        for tipo in ('comunidad', 'secretaria', 'fecha', 'empadronamiento'):
            for formato in ('excel', 'pdf'):
                self.archivo(formato, tipo=tipo)

    def test_limites_exportacion_y_columnas_pdf(self):
        with override_settings(REPORTES_MAX_PDF=1, REPORTES_MAX_EXCEL=1):
            self.assertEqual(self.client.get(self.url('pdf')).status_code, 400)
            self.assertEqual(self.client.get(self.url('excel')).status_code, 400)
        self.assertEqual(self.client.get(self.url('pdf'), {'configuradas': 'on', 'columnas': ['dpi', 'nombre', 'edad', 'nacimiento', 'telefono', 'comunidad', 'sector', 'centro', 'lider']}).status_code, 400)

    def test_permisos_en_todos_los_endpoints_y_manipulacion_get(self):
        self.client.force_login(self.otro)
        for endpoint in ('', 'datos', 'excel', 'pdf', 'opciones'):
            self.assertEqual(self.client.get(self.url(endpoint), {'comunidades': self.c1.pk, 'catalogo': 'lideres'}).status_code, 403)
        self.client.logout()
        for endpoint in ('', 'datos', 'excel', 'pdf', 'opciones'):
            self.assertEqual(self.client.get(self.url(endpoint)).status_code, 302)
        for group_name in ('Administrador', 'Gestor'):
            self.otro.groups.set([Group.objects.get_or_create(name=group_name)[0]])
            self.client.force_login(self.otro)
            self.assertEqual(self.client.get(self.url()).status_code, 200)

    def test_catalogos_dependientes_sin_dpi_y_limite_de_opciones(self):
        result = self.client.get(self.url('opciones'), {'catalogo': 'comunidades', 'sectores': self.sector.pk}).json()
        self.assertEqual(result['results'], [{'id': self.c1.pk, 'text': self.c1.nombre}])
        result = self.client.get(self.url('opciones'), {'catalogo': 'lideres'}).json()
        self.assertEqual(result['results'], [{'id': self.lider.pk, 'text': self.lider.nombre_completo}])
        self.assertNotIn('0000000000001', str(result))
        self.assertEqual(self.client.get(self.url('opciones'), {'catalogo': 'x'}).status_code, 400)

    def test_miles_exportados_y_consultas_acotadas(self):
        Afiliado.objects.bulk_create([
            Afiliado(nombre_completo=f'Afiliado masivo {i}', dpi=f'{1000 + i:013d}', fecha_nacimiento='1990-01-01', direccion='Local', comunidad=self.c1)
            for i in range(2100)
        ], batch_size=500)
        with CaptureQueriesContext(connection) as captured:
            data = self.data(comunidades=[self.c1.pk], cantidad=10)
        self.assertLess(len(captured), 20)
        self.assertEqual(len(data['filas']), 10)
        self.assertEqual(data['estadisticas']['total'], 2101)
        response, content = self.archivo('excel', comunidades=[self.c1.pk], cantidad=10)
        ws = load_workbook(io.BytesIO(content), read_only=True).active
        self.assertEqual(sum(1 for _ in ws.rows), 2108)
        self.assertEqual(response['X-Report-Total'], '2101')
        # PDF sobre miles dentro de su límite y encabezados repetidos.
        with override_settings(REPORTES_MAX_PDF=2200):
            _, content = self.archivo('pdf', comunidades=[self.c1.pk], columnas=['nombre'], configuradas='on')
        reader = PdfReader(io.BytesIO(content))
        self.assertGreater(len(reader.pages), 1)
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn('Afiliado masivo 2099', text)
        self.assertIn('Afiliado masivo 0', text)
