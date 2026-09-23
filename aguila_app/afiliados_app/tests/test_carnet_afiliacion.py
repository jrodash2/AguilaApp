import base64
import tempfile
from pathlib import Path

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
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
        self.assertNotContains(response, 'data-logo-url=')
        self.assertNotContains(response, 'data-foto-url=')

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
        self.assertContains(response, 'data-fondo-url="/static/assets/svg/credencial.svg"')

    def test_download_script_exports_real_jpeg_at_high_resolution(self):
        js_path = Path(__file__).resolve().parents[2] / 'static/assets/js/carnet_afiliacion.js'
        script = js_path.read_text(encoding='utf-8')
        css_path = Path(__file__).resolve().parents[2] / 'static/assets/css/carnet_afiliacion.css'
        stylesheet = css_path.read_text(encoding='utf-8')
        self.assertIn('drawCover(background, 0, 0, canvas.width, canvas.height)', script)
        self.assertIn("canvas.toBlob", script)
        self.assertIn("'image/jpeg', 0.95", script)
        self.assertIn("'carnet_afiliado_' + data.afiliadoId + '.jpg'", script)
        self.assertIn('.carnet-preview-shell {', stylesheet)
        self.assertIn('border-radius: 0;', stylesheet)
        self.assertIn('width="1712"', self.client.get(
            reverse('afiliados:carnet_afiliado', args=[self.afiliado.pk])
        ).content.decode())
