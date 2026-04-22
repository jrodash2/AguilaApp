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
from afiliados_app.models import Comunidad, CoordinadorOrganizacion, EstructuraOrganizativa, Sector


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class OrganizacionUIWiringTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Organizacion")
        self.user = User.objects.create_user(username="org_user", password="12345")
        self.user.groups.add(self.group)

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
