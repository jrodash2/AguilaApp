import json
from datetime import date

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import Afiliado


class DashboardNullCommunityTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name="Administrador")
        self.user = User.objects.create_user(
            username="admin", password="password123"
        )
        self.user.groups.add(self.group)

    def test_dashboard_handles_null_comunidad(self):
        Afiliado.objects.create(
            nombre_completo="Persona Sin Comunidad",
            dpi="1234567890101",
            fecha_nacimiento=date(1990, 1, 1),
            direccion="Direccion",
            comunidad=None,
        )
        self.client.login(username="admin", password="password123")

        response = self.client.get(reverse("afiliados:dahsboard"))

        self.assertEqual(response.status_code, 200)
        afiliados_por_comunidad = json.loads(
            response.context["afiliados_por_comunidad"]
        )
        self.assertIn(
            "SIN COMUNIDAD",
            {item["comunidad_nombre"] for item in afiliados_por_comunidad},
        )
