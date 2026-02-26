from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/actualiza roles RBAC y asigna permisos por módulo para afiliados_app"

    PERMISSIONS = {
        "view_dashboard",
        "view_filtros",
        "view_elecciones_2023",
        "view_cargar_padron",
        "view_configuracion",
        "view_usuarios",
    }

    ROLE_MATRIX = {
        "Administrador": {
            "view_dashboard",
            "view_filtros",
            "view_elecciones_2023",
            "view_cargar_padron",
            "view_configuracion",
            "view_usuarios",
        },
        "Gestor": {"view_dashboard", "view_filtros"},
        "Coordinador": {"view_dashboard", "view_filtros"},
        "Digitador": {"view_dashboard"},
        "Consulta": {"view_dashboard", "view_filtros"},
    }

    def handle(self, *args, **options):
        perms = Permission.objects.filter(
            content_type__app_label="afiliados_app",
            codename__in=self.PERMISSIONS,
        )
        perms_by_codename = {p.codename: p for p in perms}

        faltantes = sorted(self.PERMISSIONS - set(perms_by_codename.keys()))
        if faltantes:
            self.stdout.write(self.style.WARNING(
                "Permisos faltantes (ejecute migraciones primero): " + ", ".join(faltantes)
            ))

        for role, codenames in self.ROLE_MATRIX.items():
            group, created = Group.objects.get_or_create(name=role)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Grupo creado: {role}"))
            else:
                self.stdout.write(f"Grupo existente: {role}")

            permisos_asignar = [
                perms_by_codename[codename]
                for codename in sorted(codenames)
                if codename in perms_by_codename
            ]
            group.permissions.set(permisos_asignar)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Permisos sincronizados para {role}: {', '.join([p.codename for p in permisos_asignar])}"
                )
            )

        self.stdout.write(self.style.SUCCESS("Roles y permisos configurados correctamente."))
