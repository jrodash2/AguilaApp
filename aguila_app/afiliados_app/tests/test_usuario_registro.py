import io
import tempfile
from pathlib import Path

from django.contrib import admin
from django.contrib.auth.models import Group, User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from openpyxl import load_workbook
from pypdf import PdfReader

from afiliados_app.admin import AfiliadoAdmin
from afiliados_app.form import AfiliadoForm
from afiliados_app.models import Afiliado, CoordinadorOrganizacion


@override_settings(PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'])
class UsuarioRegistroTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user('usuario-alta')
        self.actor.groups.add(Group.objects.get_or_create(name='afiliados')[0])
        self.otro = User.objects.create_user('otro-usuario')
        self.client.force_login(self.actor)
        self.payload = {'nombre_completo': 'Afiliado de prueba', 'dpi': '1234567890123',
                        'fecha_nacimiento': '1990-01-01', 'direccion': 'Local',
                        'usuario_registro': self.otro.pk}

    def test_altas_lista_ajax_y_normal_no_permiten_suplantar_autor(self):
        urls = [('afiliado_lista', {}), ('afiliado_nuevo', {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}), ('afiliado_nuevo', {})]
        for i, (name, headers) in enumerate(urls):
            payload = dict(self.payload, dpi=f'123456789012{i}')
            response = self.client.post(reverse('afiliados:' + name), payload, **headers)
            self.assertIn(response.status_code, (200, 302))
            self.assertEqual(Afiliado.objects.get(dpi=payload['dpi']).usuario_registro, self.actor)

    def test_alta_desde_secretaria_registra_quien_confirma_afiliacion(self):
        fuente = CoordinadorOrganizacion.objects.create(nombre_completo='Fuente de prueba', dpi=self.payload['dpi'], usuario_creador=self.otro)
        response = self.client.post(reverse('afiliados:modal_afiliar_desde_secretaria_guardar'), dict(self.payload, fuente='coordinador_organizacion', fuente_id=fuente.pk))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Afiliado.objects.get(dpi=self.payload['dpi']).usuario_registro, self.actor)

    def test_edicion_preserva_autor_y_no_rellena_legacy(self):
        for i, autor in enumerate((self.otro, None)):
            obj = Afiliado.objects.create(nombre_completo='Anterior', dpi=f'223456789012{i}', fecha_nacimiento='1990-01-01', direccion='Local', usuario_registro=autor)
            response = self.client.post(reverse('afiliados:afiliado_editar', args=[obj.pk]), dict(self.payload, dpi=obj.dpi))
            self.assertEqual(response.status_code, 302)
            obj.refresh_from_db()
            self.assertEqual(obj.usuario_registro, autor)

    def test_formulario_commit_false_y_admin_guardan_autor_solo_en_alta(self):
        form = AfiliadoForm(self.payload, usuario_registro=self.actor)
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save(commit=False)
        self.assertEqual(obj.usuario_registro, self.actor)
        self.assertNotIn('usuario_registro', form.fields)
        request = RequestFactory().post('/admin/')
        request.user = self.otro
        model_admin = AfiliadoAdmin(Afiliado, admin.site)
        model_admin.save_model(request, obj, None, False)
        self.assertEqual(obj.usuario_registro, self.otro)
        request.user = self.actor
        model_admin.save_model(request, obj, None, True)
        obj.refresh_from_db()
        self.assertEqual(obj.usuario_registro, self.otro)

    def test_listado_y_legacy_sin_usuario_y_borrado_de_cuenta(self):
        obj = Afiliado.objects.create(nombre_completo='Con autor', dpi='1234567890123', fecha_nacimiento='1990-01-01', direccion='Local', usuario_registro=self.otro)
        Afiliado.objects.create(nombre_completo='Antiguo', dpi='1234567890124', fecha_nacimiento='1990-01-01', direccion='Local')
        response = self.client.get(reverse('afiliados:afiliado_lista'))
        self.assertContains(response, 'Agregado por')
        self.assertContains(response, 'otro-usuario')
        self.assertContains(response, 'Sin usuario registrado')
        self.otro.delete()
        obj.refresh_from_db()
        self.assertIsNone(obj.usuario_registro)

    def test_filtro_multiple_autores_combinado_y_catalogo(self):
        for i, autor in enumerate((self.actor, self.otro, None)):
            Afiliado.objects.create(nombre_completo=f'Persona {i}', dpi=f'323456789012{i}', fecha_nacimiento='1990-01-01', direccion='Local', usuario_registro=autor, empadronado=i == 0)
        url = reverse('afiliados:reportes_avanzados_datos')
        params = {'usuarios': [self.actor.pk, self.otro.pk], 'columnas': ['usuario_registro'], 'configuradas': 'on', 'orden': 'usuario_registro'}
        response = self.client.get(url, params)
        self.assertEqual(response.json()['estadisticas']['total'], 2)
        self.assertEqual(self.client.get(url, dict(params, empadronamiento='si')).json()['filas'], [['usuario-alta']])
        self.assertEqual(self.client.get(url, {'autor_registrado': 'no'}).json()['estadisticas']['total'], 1)
        self.assertEqual(self.client.get(url, {'usuarios': ['999999']}).status_code, 400)
        catalogo = self.client.get(reverse('afiliados:reportes_avanzados_opciones'), {'catalogo': 'usuarios'}).json()
        self.assertEqual({r['text'] for r in catalogo['results']}, {'usuario-alta', 'otro-usuario'})
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url, params).status_code, 403)

    def test_excel_pdf_respetan_autor_y_columna(self):
        for i, autor in enumerate((self.actor, self.otro)):
            Afiliado.objects.create(nombre_completo=f'Persona {i}', dpi=f'423456789012{i}', fecha_nacimiento='1990-01-01', direccion='Local', usuario_registro=autor)
        params = {'usuarios': [self.actor.pk], 'columnas': ['nombre', 'usuario_registro'], 'configuradas': 'on'}
        with tempfile.TemporaryDirectory() as folder, override_settings(REPORTES_AUDIT_LOG=Path(folder) / 'audit.jsonl'):
            for formato in ('excel', 'pdf'):
                response = self.client.get(reverse('afiliados:reportes_avanzados_' + formato), params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['X-Report-Total'], '1')
                content = b''.join(response.streaming_content)
                response.close()
                if formato == 'excel':
                    ws = load_workbook(io.BytesIO(content)).active
                    self.assertEqual(ws['B7'].value, 'Agregado por')
                    self.assertEqual(ws['B8'].value, 'usuario-alta')
                    self.assertEqual(ws.max_row, 8)
                else:
                    text = ''.join(p.extract_text() for p in PdfReader(io.BytesIO(content)).pages)
                    self.assertIn('usuario-alta', text)
                    self.assertNotIn('otro-usuario', text)
