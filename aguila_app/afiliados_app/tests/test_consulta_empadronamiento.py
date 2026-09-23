from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.conf import settings
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

from afiliados_app.models import PadronElectoral
from afiliados_app.views import GRUPOS_CONSULTA_PADRON


class ConsultaEmpadronamientoTests(TestCase):
    dpi_existente = '1234567890101'

    @classmethod
    def setUpTestData(cls):
        cls.groups = {
            name: Group.objects.create(name=name)
            for name in GRUPOS_CONSULTA_PADRON
        }
        cls.user = User.objects.create_user(username='secretaria', password='test-pass')
        cls.user.groups.add(cls.groups['Organizacion'])
        cls.unauthorized_user = User.objects.create_user(
            username='sin-secretaria', password='test-pass'
        )
        cls.person = PadronElectoral.objects.create(
            identificacion=cls.dpi_existente,
            nombre='Persona de Prueba',
            edad=32,
            comunidad='Comunidad Central',
            departamento='El Progreso',
            municipio='San Agustín Acasaguastlán',
        )

    def setUp(self):
        self.page_url = reverse('afiliados:consulta_empadronamiento')
        self.api_url = reverse('afiliados:consulta_empadronamiento_api')

    def test_anonymous_user_is_redirected_from_page_and_api(self):
        self.assertEqual(self.client.get(self.page_url).status_code, 302)
        self.assertEqual(self.client.get(self.api_url, {'dpi': self.dpi_existente}).status_code, 302)

    def test_user_without_authorized_group_is_forbidden(self):
        self.client.force_login(self.unauthorized_user)
        self.assertEqual(self.client.get(self.page_url).status_code, 403)
        response = self.client.get(self.api_url, {'dpi': self.dpi_existente})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json()['ok'])

    def test_every_authorized_group_can_open_page_and_query(self):
        for group_name, group in self.groups.items():
            with self.subTest(group=group_name):
                user = User.objects.create_user(username='user-' + group_name)
                user.groups.add(group)
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.page_url).status_code, 200)
                self.assertEqual(
                    self.client.get(self.api_url, {'dpi': self.dpi_existente}).status_code,
                    200,
                )
                self.client.logout()

    def test_page_links_to_configured_tse_site_in_new_tab(self):
        self.client.force_login(self.user)
        response = self.client.get(self.page_url)
        self.assertContains(response, 'href="{}"'.format(settings.TSE_CONSULTA_URL))
        self.assertContains(response, 'target="_blank"')
        self.assertContains(response, 'rel="noopener noreferrer"')

    def test_existing_dpi_returns_only_local_person_data(self):
        self.client.force_login(self.user)
        response = self.client.get(self.api_url, {'dpi': self.dpi_existente})
        payload = response.json()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(payload['found'])
        self.assertEqual(payload['data']['nombre_completo'], self.person.nombre)
        self.assertEqual(payload['data']['municipio'], self.person.municipio)

    def test_missing_dpi_returns_informative_not_found(self):
        self.client.force_login(self.user)
        response = self.client.get(self.api_url, {'dpi': '9999999999999'})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['found'])
        self.assertEqual(response.json()['message'], 'No encontrado en el padrón local.')

    def test_spaces_and_hyphens_are_normalized(self):
        self.client.force_login(self.user)
        for formatted_dpi in ('1234 56789 0101', '1234-56789-0101'):
            with self.subTest(dpi=formatted_dpi):
                response = self.client.get(self.api_url, {'dpi': formatted_dpi})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['found'])

    def test_incomplete_or_alphabetic_dpi_is_rejected(self):
        self.client.force_login(self.user)
        for invalid_dpi in ('123456789012', 'A1234567890101', '1234567890101A'):
            with self.subTest(dpi=invalid_dpi):
                response = self.client.get(self.api_url, {'dpi': invalid_dpi})
                self.assertEqual(response.status_code, 400)
                self.assertFalse(response.json()['ok'])

    def test_database_failure_returns_controlled_error(self):
        self.client.force_login(self.user)
        with patch(
            'afiliados_app.views.PadronElectoral.objects.filter',
            side_effect=DatabaseError('sensitive database detail'),
        ):
            response = self.client.get(self.api_url, {'dpi': self.dpi_existente})
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'sensitive database detail', status_code=503)

    def test_queries_do_not_create_or_modify_records(self):
        self.client.force_login(self.user)
        before = list(PadronElectoral.objects.values())
        self.client.get(self.api_url, {'dpi': self.dpi_existente})
        self.client.get(self.api_url, {'dpi': '9999999999999'})
        self.client.get(self.api_url, {'dpi': '123'})
        self.assertEqual(list(PadronElectoral.objects.values()), before)
