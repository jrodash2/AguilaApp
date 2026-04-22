from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse

from afiliados_app.form import (
    CoordinadorOrganizacionForm,
    EstructuraOrganizativaForm,
    IncidenciaTerritorialForm,
    LiderComunitarioOrganizacionForm,
    ReunionTerritorialForm,
    ResponsableTerritorialForm,
)
from afiliados_app.models import Comunidad, CoordinadorJuventud, CoordinadorOrganizacion, EstructuraJuventud, EstructuraOrganizativa, Sector


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class OrganizacionUIWiringTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Organizacion")
        self.jovenes_group = Group.objects.create(name="Jovenes")
        self.admin_group = Group.objects.create(name="Administrador")
        self.user = User.objects.create_user(username="org_user", password="12345")
        self.user.groups.add(self.group)
        self.admin_user = User.objects.create_user(username="admin_user", password="12345")
        self.admin_user.groups.add(self.admin_group)
        self.joven_user = User.objects.create_user(username="joven_user", password="12345")
        self.joven_user.groups.add(self.jovenes_group)

        self.creator = User.objects.create_user(username="creator", password="12345")

        self.sector = Sector.objects.create(nombre="Sector 1")
        self.comunidad = Comunidad.objects.create(nombre="Comunidad 1", sector=self.sector)

        self.coordinador = CoordinadorOrganizacion.objects.create(
            nombre_completo="COORD TEST",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        self.estructura = EstructuraOrganizativa.objects.create(
            tipo_estructura="Comité",
            nombre="Estructura Test",
            comunidad=self.comunidad,
            coordinador_responsable=self.coordinador,
            usuario_creador=self.creator,
        )

    def test_reuniones_template_real_contains_modal_and_hidden_targets(self):
        self.client.login(username="org_user", password="12345")
        response = self.client.get(reverse("afiliados:lista_reuniones"))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        self.assertIn('id="modalResponsables"', html)
        self.assertIn('id="id_responsables"', html)
        self.assertIn('id="id_responsable_tipo"', html)
        self.assertIn('id="id_responsable_referencia_id"', html)
        self.assertIn("#tablaResponsablesModal tbody", html)
        self.assertIn("modalResponsables.hide()", html)
        self.assertIn('data-bs-target="#modalResponsables">Agregar responsable</button>', html)
        self.assertIn("Agregar responsable", html)
        self.assertIn("<th>Fecha</th>", html)
        self.assertIn("<th>Comunidad</th>", html)
        self.assertIn("<th>Responsable</th>", html)
        self.assertIn("<th>Asistentes</th>", html)
        self.assertIn("<th>Estado</th>", html)
        self.assertIn("<th>Tipo</th>", html)
        self.assertIn("<th>Sector</th>", html)
        self.assertIn("<th>Centro</th>", html)

    def test_detalle_estructura_template_real_contains_modal_and_confirm_flow(self):
        self.client.login(username="org_user", password="12345")
        response = self.client.get(reverse("afiliados:detalle_estructura", args=[self.estructura.pk]))
        self.assertEqual(response.status_code, 200)

        html = response.content.decode()
        self.assertIn('id="modalAgregarIntegrante"', html)
        self.assertIn('id="id_dpi_integrante"', html)
        self.assertIn('id="id_verified_dpi"', html)
        self.assertIn('id="btnConfirmarAgregar"', html)
        self.assertIn("Debes verificar empadronamiento del DPI antes de confirmar.", html)

    def test_detalle_estructura_post_requires_verified_dpi(self):
        self.client.login(username="org_user", password="12345")
        response = self.client.post(
            reverse("afiliados:detalle_estructura", args=[self.estructura.pk]),
            {"dpi": "1234567890123", "verified_dpi": ""},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        msgs = "\n".join(str(m) for m in response.context["messages"])
        self.assertIn("Primero debe verificar empadronamiento", msgs)

    def test_organizacion_forms_do_not_expose_manual_sector_or_centro(self):
        forms = [
            CoordinadorOrganizacionForm(),
            LiderComunitarioOrganizacionForm(),
            ResponsableTerritorialForm(),
            ReunionTerritorialForm(),
            EstructuraOrganizativaForm(),
            IncidenciaTerritorialForm(),
        ]
        for form in forms:
            self.assertNotIn("sector", form.fields)
            self.assertNotIn("centro_votacion", form.fields)
        self.assertNotIn("cantidad_integrantes", EstructuraOrganizativaForm().fields)

    def test_admin_dashboard_renders_sidebar_without_template_syntax_errors(self):
        self.client.login(username="admin_user", password="12345")
        response = self.client.get(reverse("afiliados:dahsboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn("Afiliación", html)
        self.assertIn("Organización", html)
        self.assertIn("Juventud", html)

    def test_login_redirects_jovenes_to_dashboard_juventud(self):
        response = self.client.post(
            reverse("afiliados:signin"),
            {"username": "joven_user", "password": "12345"},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("afiliados:dashboard_juventud"))

    def test_dashboard_juventud_access_for_jovenes_group(self):
        self.client.login(username="joven_user", password="12345")
        response = self.client.get(reverse("afiliados:dashboard_juventud"))
        self.assertEqual(response.status_code, 200)

    def test_juventud_estructura_template_has_expected_modal_and_fields(self):
        self.client.login(username="joven_user", password="12345")
        response = self.client.get(reverse("afiliados:crear_estructura_juventud"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="modalCoordinadores"', html)
        self.assertIn('id="tablaCoordinadoresModal"', html)
        self.assertIn('id="coordinador_responsable_display"', html)
        self.assertIn('id="id_coordinador_responsable"', html)
        self.assertIn("btn-seleccionar-coordinador", html)
        self.assertIn("data-coordinador-id", html)
        self.assertIn("data-coordinador-nombre", html)

    def test_juventud_crear_estructura_guarda_coordinador_desde_hidden_field(self):
        self.client.login(username="joven_user", password="12345")
        coordinador = CoordinadorJuventud.objects.create(
            nombre_completo="COORD JUV TEST",
            comunidad=self.comunidad,
            usuario_creador=self.joven_user,
        )
        response = self.client.post(
            reverse("afiliados:crear_estructura_juventud"),
            {
                "tipo_estructura": "Comité juvenil",
                "nombre": "Estructura JUV 1",
                "comunidad": str(self.comunidad.pk),
                "estado": "ACTIVO",
                "coordinador_responsable": str(coordinador.pk),
                "observaciones": "test",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        estructura = EstructuraJuventud.objects.get(nombre="Estructura JUV 1")
        self.assertEqual(estructura.coordinador_responsable_id, coordinador.pk)

    def test_juventud_editar_estructura_permite_cambiar_coordinador(self):
        self.client.login(username="joven_user", password="12345")
        coordinador_a = CoordinadorJuventud.objects.create(
            nombre_completo="COORD JUV A",
            comunidad=self.comunidad,
            usuario_creador=self.joven_user,
        )
        coordinador_b = CoordinadorJuventud.objects.create(
            nombre_completo="COORD JUV B",
            comunidad=self.comunidad,
            usuario_creador=self.joven_user,
        )
        estructura = EstructuraJuventud.objects.create(
            tipo_estructura="Brigada",
            nombre="Estructura Edit JUV",
            comunidad=self.comunidad,
            coordinador_responsable=coordinador_a,
            usuario_creador=self.joven_user,
        )
        response_get = self.client.get(reverse("afiliados:editar_estructura_juventud", args=[estructura.pk]))
        self.assertEqual(response_get.status_code, 200)
        self.assertIn("COORD JUV A", response_get.content.decode())

        response_post = self.client.post(
            reverse("afiliados:editar_estructura_juventud", args=[estructura.pk]),
            {
                "tipo_estructura": "Brigada",
                "nombre": "Estructura Edit JUV",
                "comunidad": str(self.comunidad.pk),
                "estado": "ACTIVO",
                "coordinador_responsable": str(coordinador_b.pk),
                "observaciones": "update",
            },
            follow=True,
        )
        self.assertEqual(response_post.status_code, 200)
        estructura.refresh_from_db()
        self.assertEqual(estructura.coordinador_responsable_id, coordinador_b.pk)
