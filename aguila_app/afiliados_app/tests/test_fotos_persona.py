import base64
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from afiliados_app.fotos import asignar_fotos_personas, guardar_foto_persona
from afiliados_app.models import Afiliado, FotoPersona


PNG_1PX = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class FotoPersonaTests(TestCase):
    def foto(self):
        return SimpleUploadedFile('captura.png', PNG_1PX, content_type='image/png')

    def test_afiliado_uses_opaque_filename(self):
        afiliado = Afiliado.objects.create(
            nombre_completo='Persona Privada', dpi='1234567890101',
            fecha_nacimiento='1990-01-01', direccion='Dirección',
        )
        guardar_foto_persona(afiliado, self.foto())
        afiliado.refresh_from_db()
        self.assertTrue(afiliado.foto.name.startswith('afiliados/fotos/'))
        self.assertNotIn(afiliado.dpi, afiliado.foto.name)
        self.assertNotIn('Persona', afiliado.foto.name)

    def test_standalone_person_reuses_affiliate_photo_by_dpi(self):
        afiliado = Afiliado.objects.create(
            nombre_completo='Persona', dpi='1234567890102',
            fecha_nacimiento='1990-01-01', direccion='Dirección',
        )

        class Registro:
            dpi = afiliado.dpi

        guardar_foto_persona(Registro(), self.foto())
        afiliado.refresh_from_db()
        self.assertTrue(afiliado.foto)
        self.assertFalse(FotoPersona.objects.filter(dpi=afiliado.dpi).exists())

    def test_bulk_resolution_does_not_create_records(self):
        FotoPersona.objects.create(dpi='1234567890103', foto=self.foto())

        class Registro:
            dpi = '1234567890103'

        before = FotoPersona.objects.count()
        result = asignar_fotos_personas([Registro()])
        self.assertTrue(result[0].foto_resuelta)
        self.assertEqual(FotoPersona.objects.count(), before)

