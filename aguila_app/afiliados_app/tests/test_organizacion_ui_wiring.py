from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import parse_qs, urlparse

from afiliados_app.form import (
    AfiliadoForm,
    CoordinadorOrganizacionForm,
    EstructuraOrganizativaForm,
    IncidenciaTerritorialForm,
    LiderComunitarioOrganizacionForm,
    ReunionTerritorialForm,
    ResponsableTerritorialForm,
)
from afiliados_app.models import Comunidad, CoordinadorJuventud, CoordinadorOrganizacion, EstructuraJuventud, EstructuraOrganizativa, Sector
from afiliados_app.models import Afiliado, CoordinadoraMujeres
from afiliados_app.models import CoordinadorLogistica, RecursoLogistico


@override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
)
class OrganizacionUIWiringTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Organizacion")
        self.jovenes_group = Group.objects.create(name="Jovenes")
        self.admin_group = Group.objects.create(name="Administrador")
        self.logistica_group = Group.objects.create(name="Logistica")
        self.user = User.objects.create_user(username="org_user", password="12345")
        self.user.groups.add(self.group)
        self.admin_user = User.objects.create_user(username="admin_user", password="12345")
        self.admin_user.groups.add(self.admin_group)
        self.joven_user = User.objects.create_user(username="joven_user", password="12345")
        self.joven_user.groups.add(self.jovenes_group)
        self.logistica_user = User.objects.create_user(username="logistica_user", password="12345")
        self.logistica_user.groups.add(self.logistica_group)

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

    def test_organizacion_estructura_template_has_expected_modal_and_fields(self):
        self.client.login(username="org_user", password="12345")
        response = self.client.get(reverse("afiliados:crear_estructura"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="modalCoordinadores"', html)
        self.assertIn('id="tablaCoordinadoresModal"', html)
        self.assertIn('id="coordinador_responsable_display"', html)
        self.assertIn('id="id_coordinador_responsable"', html)
        self.assertIn("js-select-coordinador", html)
        self.assertIn("data-coord-id", html)
        self.assertIn("data-coord-nombre", html)

    def test_organizacion_crear_estructura_guarda_coordinador(self):
        self.client.login(username="org_user", password="12345")
        coordinador = CoordinadorOrganizacion.objects.create(
            nombre_completo="COORD ORG TEST",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )
        response = self.client.post(
            reverse("afiliados:crear_estructura"),
            {
                "tipo_estructura": "Comité",
                "nombre": "Estructura ORG 1",
                "comunidad": str(self.comunidad.pk),
                "estado": "ACTIVO",
                "coordinador_responsable": str(coordinador.pk),
                "observaciones": "test",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        estructura = EstructuraOrganizativa.objects.get(nombre="Estructura ORG 1")
        self.assertEqual(estructura.coordinador_responsable_id, coordinador.pk)

    def test_organizacion_editar_estructura_permite_cambiar_coordinador(self):
        self.client.login(username="org_user", password="12345")
        coordinador_a = CoordinadorOrganizacion.objects.create(
            nombre_completo="COORD ORG A",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )
        coordinador_b = CoordinadorOrganizacion.objects.create(
            nombre_completo="COORD ORG B",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )
        estructura = EstructuraOrganizativa.objects.create(
            tipo_estructura="Comité",
            nombre="Estructura Edit ORG",
            comunidad=self.comunidad,
            coordinador_responsable=coordinador_a,
            usuario_creador=self.creator,
        )
        response_get = self.client.get(reverse("afiliados:editar_estructura", args=[estructura.pk]))
        self.assertEqual(response_get.status_code, 200)
        self.assertIn("COORD ORG A", response_get.content.decode())

        response_post = self.client.post(
            reverse("afiliados:editar_estructura", args=[estructura.pk]),
            {
                "tipo_estructura": "Comité",
                "nombre": "Estructura Edit ORG",
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

    def test_login_redirects_logistica_to_dashboard_logistica(self):
        response = self.client.post(
            reverse("afiliados:signin"),
            {"username": "logistica_user", "password": "12345"},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("afiliados:dashboard_logistica"))

    def test_dashboard_logistica_access_and_sidebar(self):
        self.client.login(username="logistica_user", password="12345")
        response = self.client.get(reverse("afiliados:dashboard_logistica"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Logística", response.content.decode())

    def test_logistica_estructura_template_has_expected_modal_and_fields(self):
        self.client.login(username="logistica_user", password="12345")
        response = self.client.get(reverse("afiliados:crear_estructura_logistica"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="modalCoordinadores"', html)
        self.assertIn('id="tablaCoordinadoresModal"', html)
        self.assertIn('id="coordinador_responsable_display"', html)
        self.assertIn('id="id_coordinador_responsable"', html)

    def test_logistica_crear_estructura_guarda_coordinador(self):
        self.client.login(username="logistica_user", password="12345")
        coordinador = CoordinadorLogistica.objects.create(
            nombre_completo="COORD LOG TEST",
            comunidad=self.comunidad,
            usuario_creador=self.logistica_user,
        )
        response = self.client.post(
            reverse("afiliados:crear_estructura_logistica"),
            {
                "tipo_estructura": "Brigada logística",
                "nombre": "Estructura LOG 1",
                "comunidad": str(self.comunidad.pk),
                "estado": "ACTIVO",
                "coordinador_responsable": str(coordinador.pk),
                "observaciones": "test",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Registro guardado correctamente")

    def test_logistica_recursos_view_allows_create(self):
        self.client.login(username="logistica_user", password="12345")
        response = self.client.post(
            reverse("afiliados:lista_recursos_logisticos"),
            {
                "nombre": "Carpa móvil",
                "tipo_recurso": "Infraestructura",
                "descripcion": "Carpa para jornadas",
                "estado": "DISPONIBLE",
                "observaciones": "Sin novedades",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(RecursoLogistico.objects.filter(nombre="Carpa móvil").exists())

    def test_juventud_estructura_template_has_expected_modal_and_fields(self):
        self.client.login(username="joven_user", password="12345")
        response = self.client.get(reverse("afiliados:crear_estructura_juventud"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="modalCoordinadores"', html)
        self.assertIn('id="tablaCoordinadoresModal"', html)
        self.assertIn('id="coordinador_responsable_display"', html)
        self.assertIn('id="id_coordinador_responsable"', html)
        self.assertIn("js-select-coordinador", html)
        self.assertIn("data-coord-id", html)
        self.assertIn("data-coord-nombre", html)

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

    def test_pendientes_afiliacion_construye_boton_con_fuente_y_prefill(self):
        self.client.login(username="admin_user", password="12345")
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Secretaria",
            dpi="1234 56789 0123",
            telefono="55551234",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(reverse("afiliados:pendientes_afiliacion_secretarias"))
        self.assertEqual(response.status_code, 200)

        pendientes = response.context["pendientes"]
        self.assertEqual(len(pendientes), 1)
        afiliar_url = pendientes[0]["afiliar_url"]
        parsed = parse_qs(urlparse(afiliar_url).query)
        self.assertEqual(parsed.get("dpi", [None])[0], "1234567890123")
        self.assertEqual(parsed.get("fuente", [None])[0], "coordinadora_mujeres")
        self.assertEqual(parsed.get("fuente_id", [None])[0], str(registro_fuente.pk))
        self.assertEqual(parsed.get("telefono", [None])[0], "55551234")
        self.assertEqual(parsed.get("comunidad_id", [None])[0], str(self.comunidad.pk))

        html = response.content.decode()
        self.assertIn("Exportar a Excel", html)
        self.assertIn(">Afiliar<", html)
        self.assertIn('id="afiliarPendienteModal"', html)
        self.assertIn("modal_afiliar_desde_secretaria_form", html)

    def test_afiliar_desde_secretaria_redirige_con_prefill_reutilizando_datos(self):
        self.client.login(username="admin_user", password="12345")
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Source",
            dpi="1234567890123",
            telefono="45678901",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:afiliar_desde_secretaria"),
            {"dpi": "1234567890123", "fuente": "coordinadora_mujeres", "fuente_id": registro_fuente.pk},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(urlparse(response.url).path, reverse("afiliados:afiliado_lista"))
        parsed = parse_qs(urlparse(response.url).query)
        self.assertIn("prefill_token", parsed)

        token = parsed["prefill_token"][0]
        session_key = f"afiliacion_prefill:{token}"
        payload = self.client.session.get(session_key)
        self.assertIsNotNone(payload)
        self.assertEqual(payload.get("dpi"), "1234567890123")
        self.assertEqual(payload.get("nombre"), "Persona Source")
        self.assertEqual(payload.get("telefono"), "45678901")
        self.assertEqual(payload.get("comunidad_id"), str(self.comunidad.pk))

    def test_prefill_afiliacion_desde_secretaria_retorna_datos_para_modal(self):
        self.client.login(username="admin_user", password="12345")
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Modal",
            dpi="1234567890123",
            telefono="10101010",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:prefill_afiliacion_desde_secretaria"),
            {"dpi": "1234567890123", "fuente": "coordinadora_mujeres", "fuente_id": registro_fuente.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["prefill"]["dpi"], "1234567890123")
        self.assertEqual(payload["prefill"]["nombre"], "Persona Modal")
        self.assertEqual(payload["prefill"]["telefono"], "10101010")
        self.assertEqual(payload["prefill"]["comunidad_id"], str(self.comunidad.pk))

    def test_modal_afiliar_desde_secretaria_form_retorna_html_precargado(self):
        self.client.login(username="admin_user", password="12345")
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Modal HTML",
            dpi="1234567890123",
            telefono="30303030",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:modal_afiliar_desde_secretaria_form"),
            {"dpi": "1234567890123", "fuente": "coordinadora_mujeres", "fuente_id": registro_fuente.pk},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("formAfiliarPendienteModal", payload["form_html"])
        self.assertIn("Persona Modal HTML", payload["form_html"])

    def test_exportar_pendientes_afiliacion_secretarias_excel_descarga_archivo(self):
        self.client.login(username="admin_user", password="12345")
        CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Export",
            dpi="1234567890123",
            telefono="40404040",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(reverse("afiliados:exportar_pendientes_afiliacion_secretarias_excel"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertIn("pendientes_afiliacion_secretarias.xlsx", response["Content-Disposition"])
        self.assertGreater(len(response.content), 0)

    def test_prefill_afiliacion_desde_secretaria_bloquea_si_ya_esta_afiliado(self):
        self.client.login(username="admin_user", password="12345")
        afiliado = Afiliado.objects.create(
            nombre_completo="Ya Afiliado",
            dpi="1234 56789 0123",
            fecha_nacimiento="1990-01-01",
            direccion="Zona 3",
        )
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Ya Afiliado",
            dpi="1234567890123",
            telefono="20202020",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:prefill_afiliacion_desde_secretaria"),
            {"dpi": "1234567890123", "fuente": "coordinadora_mujeres", "fuente_id": registro_fuente.pk},
        )
        self.assertEqual(response.status_code, 409)
        payload = response.json()
        self.assertTrue(payload["exists"])
        self.assertEqual(payload["detalle_url"], reverse("afiliados:afiliado_detalle", args=[afiliado.pk]))

    def test_afiliar_desde_secretaria_no_duplica_afiliado_existente(self):
        self.client.login(username="admin_user", password="12345")
        afiliado = Afiliado.objects.create(
            nombre_completo="Ya Afiliado",
            dpi="1234567890123",
            fecha_nacimiento="1990-01-01",
        )
        CoordinadoraMujeres.objects.create(
            nombre_completo="Ya Afiliado",
            dpi="1234567890123",
            telefono="11111111",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:afiliar_desde_secretaria"),
            {"dpi": "1234567890123", "fuente": "coordinadora_mujeres", "fuente_id": 999999},
            follow=False,
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("afiliados:afiliado_detalle", args=[afiliado.pk]))

    def test_afiliar_desde_secretaria_muestra_error_si_fuente_no_corresponde(self):
        self.client.login(username="admin_user", password="12345")
        registro_fuente = CoordinadoraMujeres.objects.create(
            nombre_completo="Persona Real",
            dpi="1234567890123",
            telefono="22223333",
            comunidad=self.comunidad,
            usuario_creador=self.creator,
        )

        response = self.client.get(
            reverse("afiliados:afiliar_desde_secretaria"),
            {"dpi": "9999999999999", "fuente": "coordinadora_mujeres", "fuente_id": registro_fuente.pk},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.request["PATH_INFO"], reverse("afiliados:pendientes_afiliacion_secretarias"))
        mensajes = "\n".join(str(m) for m in response.context["messages"])
        self.assertIn("No se encontró un registro fuente válido", mensajes)

    def test_afiliado_form_normaliza_dpi_y_evita_duplicado_por_formato(self):
        afiliado = Afiliado.objects.create(
            nombre_completo="Registro existente",
            dpi="1234 56789 0123",
            fecha_nacimiento="1990-01-01",
            direccion="Zona 1",
        )
        form = AfiliadoForm(
            data={
                "nombre_completo": "Intento duplicado",
                "dpi": "1234567890123",
                "fecha_nacimiento": "1999-01-01",
                "telefono": "55550000",
                "direccion": "Zona 2",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("dpi", form.errors)
        self.assertIn("Ya existe un afiliado registrado con este DPI.", form.errors["dpi"])

        afiliado.delete()

    def test_afiliado_lista_aplica_prefill_desde_session_token(self):
        self.client.login(username="admin_user", password="12345")
        session = self.client.session
        session["afiliacion_prefill:token123"] = {
            "dpi": "1234567890123",
            "nombre": "Precargada",
            "telefono": "33334444",
            "direccion": "Zona 9",
            "comunidad_id": str(self.comunidad.pk),
        }
        session.save()

        response = self.client.get(reverse("afiliados:afiliado_lista"), {"prefill_token": "token123"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["abrir_modal_prefill"])
        self.assertEqual(response.context["prefill_dpi"], "1234567890123")
        self.assertEqual(response.context["form"].initial.get("nombre_completo"), "Precargada")
        self.assertEqual(response.context["form"].initial.get("telefono"), "33334444")
