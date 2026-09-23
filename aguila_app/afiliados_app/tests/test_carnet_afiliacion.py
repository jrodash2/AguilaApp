import base64
import re
import tempfile
import uuid
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.templatetags.static import static
from django.urls import reverse

from afiliados_app.models import Afiliado, Comunidad, Institucion, PadronElectoral


PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher'],
)
class CarnetAfiliacionTests(TestCase):
    def setUp(self):
        self.grupo_afiliados = Group.objects.create(name='afiliados')
        self.usuario = User.objects.create_user(username='carnet', password='clave')
        self.usuario.groups.add(self.grupo_afiliados)
        self.afiliado = Afiliado.objects.create(
            nombre_completo='Nombre Corto',
            dpi='1234 56789 0101',
            fecha_nacimiento='1990-01-01',
            direccion='Dirección no mostrada',
        )
        self.client.login(username='carnet', password='clave')

    def image(self, name):
        return SimpleUploadedFile(name, PNG_1PX, content_type='image/png')

    def test_requires_login_and_affiliation_role(self):
        url = reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk])
        self.client.logout()
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

        unauthorized = User.objects.create_user(username='sin_permiso', password='clave')
        self.client.login(username=unauthorized.username, password='clave')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_renders_without_photo_logo_or_institution(self):
        response = self.client.get(reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Carnet de Afiliación')
        self.assertContains(response, 'data-nombre="Nombre Corto"')
        self.assertContains(
            response,
            'data-codigo="{}"'.format(str(self.afiliado.token_validacion)[:8].upper()),
        )
        self.assertNotContains(response, 'data-logo-url=')
        self.assertNotContains(response, 'data-foto-url=')
        self.assertRegex(
            response.content.decode(),
            r'data-qr-url="data:image/png;base64,[A-Za-z0-9+/=]+"',
        )
        validation_url = reverse(
            'afiliados:validar_afiliado',
            args=[self.afiliado.token_validacion],
        )
        self.assertContains(
            response,
            'href="{}"'.format(response.wsgi_request.build_absolute_uri(validation_url)),
        )
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'rel="noopener noreferrer"')

    def test_renders_photo_logo_long_name_and_optional_location(self):
        self.afiliado.nombre_completo = 'María Fernanda de los Ángeles Apellido Primero Apellido Segundo'
        self.afiliado.foto = self.image('foto.png')
        self.afiliado.comunidad = Comunidad.objects.create(nombre='Comunidad Central')
        self.afiliado.save()
        institucion = Institucion.objects.create(
            nombre='Institución de Prueba',
            direccion='Dirección',
            telefono='5555-5555',
            logo=self.image('logo.png'),
        )
        PadronElectoral.objects.create(
            nombre=self.afiliado.nombre_completo,
            identificacion='1234567890101',
            comunidad='Comunidad del padrón',
            municipio='Municipio de Prueba',
            departamento='Departamento de Prueba',
        )

        response = self.client.get(reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-foto-url="{}"'.format(self.afiliado.foto.url))
        self.assertContains(response, 'data-logo-url="{}"'.format(institucion.logo.url))
        self.assertContains(response, 'data-comunidad="Comunidad Central"')
        self.assertContains(response, 'data-municipio="Municipio de Prueba"')
        self.assertContains(response, 'data-departamento="Departamento de Prueba"')

    def test_uses_existing_credential_svg_as_background(self):
        svg_path = Path(__file__).resolve().parents[2] / 'static/assets/svg/credencial.svg'
        svg = svg_path.read_text(encoding='utf-8')
        self.assertIn('viewBox="0 0 708 483.749988"', svg)
        self.assertNotIn(self.afiliado.nombre_completo, svg)

        response = self.client.get(reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk]))
        self.assertContains(
            response,
            'data-fondo-url="{}"'.format(static('assets/svg/credencial.svg')),
        )

    def test_download_script_exports_real_jpeg_at_high_resolution(self):
        js_path = Path(__file__).resolve().parents[2] / 'static/assets/js/carnet_afiliacion.js'
        script = js_path.read_text(encoding='utf-8')
        css_path = Path(__file__).resolve().parents[2] / 'static/assets/css/carnet_afiliacion.css'
        stylesheet = css_path.read_text(encoding='utf-8')
        self.assertIn('drawCover(background, 0, 0, canvas.width, canvas.height)', script)
        self.assertIn(".getPropertyValue('--carnet-accent-color')", script)
        self.assertIn('context.lineWidth = px(2)', script)
        self.assertIn("context.fillText('CÓDIGO DE AFILIACIÓN', px(159), px(483))", script)
        self.assertIn("context.fillText(data.codigo, px(159), px(505))", script)
        self.assertIn('loadImage(data.qrUrl)', script)
        self.assertIn('renderCard(assets[0], assets[1], assets[2], assets[3])', script)
        self.assertIn('px(713), px(18), px(125), px(125)', script)
        self.assertIn("canvas.toBlob", script)
        self.assertIn("'image/jpeg', 0.95", script)
        self.assertIn("'carnet_afiliado_' + data.afiliadoId + '.jpg'", script)
        self.assertIn('.carnet-preview-shell {', stylesheet)
        self.assertIn('--carnet-accent-color: #0d47a1;', stylesheet)
        self.assertIn('border-radius: 0;', stylesheet)
        self.assertIn('.qr-validacion-link {', stylesheet)
        self.assertIn('left: 83.29%;', stylesheet)
        self.assertIn('top: 3.33%;', stylesheet)
        self.assertIn('width: 14.60%;', stylesheet)
        self.assertIn('width="1712"', self.client.get(
            reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk])
        ).content.decode())

    def test_sidebar_scroll_only_reads_offset_when_active_link_exists(self):
        js_path = Path(__file__).resolve().parents[2] / 'static/assets/js/sidebar-menu.js'
        script = js_path.read_text(encoding='utf-8')
        self.assertIn('a.active, .sidebar-list.active > a', script)
        self.assertIn('$activeSidebarLink.length', script)
        self.assertIn('activeSidebarOffset &&', script)

    def test_each_affiliate_has_a_stable_unique_validation_token(self):
        otro = Afiliado.objects.create(
            nombre_completo='Otro Afiliado',
            dpi='9876 54321 0101',
            fecha_nacimiento='1991-01-01',
            direccion='Dirección',
        )
        self.assertIsInstance(self.afiliado.token_validacion, uuid.UUID)
        self.assertNotEqual(self.afiliado.token_validacion, otro.token_validacion)

        token = self.afiliado.token_validacion
        self.afiliado.refresh_from_db()
        self.assertEqual(self.afiliado.token_validacion, token)

    def test_public_validation_page_displays_only_expected_affiliate_data(self):
        self.afiliado.telefono = '5555-1212'
        self.afiliado.save(update_fields=['telefono'])
        institucion = Institucion.objects.create(
            nombre='Institución de Prueba',
            direccion='Dirección institucional',
            telefono='5555-5555',
            logo=self.image('logo-validacion.png'),
        )
        PadronElectoral.objects.create(
            nombre=self.afiliado.nombre_completo,
            identificacion='1234567890101',
            municipio='Municipio de Prueba',
            departamento='Departamento de Prueba',
        )
        self.client.logout()
        response = self.client.get(reverse(
            'afiliados:validar_afiliado',
            args=[self.afiliado.token_validacion],
        ))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Afiliado Cabal')
        self.assertContains(response, 'Afiliación verificada')
        self.assertContains(response, institucion.logo.url)
        self.assertContains(response, self.afiliado.nombre_completo)
        self.assertContains(response, 'Municipio de Prueba')
        self.assertContains(response, 'Departamento de Prueba')
        self.assertNotContains(response, self.afiliado.direccion)
        self.assertNotContains(response, self.afiliado.telefono)

    def test_unknown_validation_token_has_a_clear_404_page(self):
        response = self.client.get(reverse(
            'afiliados:validar_afiliado',
            args=[uuid.uuid4()],
        ))
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'QR no válido', status_code=404)

        malformed_response = self.client.get(reverse(
            'afiliados:validar_afiliado',
            args=['codigo-invalido'],
        ))
        self.assertEqual(malformed_response.status_code, 404)
        self.assertContains(malformed_response, 'QR no válido', status_code=404)

    def test_different_affiliates_render_different_qr_images(self):
        otro = Afiliado.objects.create(
            nombre_completo='Otro Afiliado',
            dpi='9876 54321 0101',
            fecha_nacimiento='1991-01-01',
            direccion='Dirección',
        )
        responses = [
            self.client.get(reverse('afiliados:carnet_afiliado', args=[pk])).content.decode()
            for pk in (self.afiliado.pk, otro.pk)
        ]
        qr_images = [re.search(r'data-qr-url="([^"]+)"', html).group(1) for html in responses]
        self.assertNotEqual(qr_images[0], qr_images[1])
