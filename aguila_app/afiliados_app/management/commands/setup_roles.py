from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Crea/actualiza roles RBAC y sincroniza permisos por grupo (idempotente)."

    BASE_GROUPS = ["Administrador", "Gestor", "Coordinador", "Digitador", "Consulta"]

    GESTOR_REQUIRED = [
        ("afiliados_app", "view_afiliado"),
        ("afiliados_app", "add_afiliado"),
        ("afiliados_app", "change_afiliado"),
        ("afiliados_app", "view_lidercomunitario"),
        ("afiliados_app", "add_lidercomunitario"),
        ("afiliados_app", "change_lidercomunitario"),
        ("afiliados_app", "view_comision"),
        ("afiliados_app", "add_comision"),
        ("afiliados_app", "change_comision"),
        ("afiliados_app", "view_comunidad"),
        ("afiliados_app", "add_comunidad"),
        ("afiliados_app", "change_comunidad"),
        ("afiliados_app", "view_sector"),
        ("afiliados_app", "add_sector"),
        ("afiliados_app", "change_sector"),
        ("afiliados_app", "view_centrovotacion"),
        ("afiliados_app", "add_centrovotacion"),
        ("afiliados_app", "change_centrovotacion"),
        ("afiliados_app", "view_institucion"),
        ("afiliados_app", "view_perfil"),
    ]

    GESTOR_PROHIBITED_PREFIXES = [
        "delete_",
    ]

    GESTOR_PROHIBITED_MODELS = {
        ("afiliados_app", "eleccion2023"),
        ("afiliados_app", "trepcentroresultado"),
        ("afiliados_app", "padronelectoral"),
        ("auth", "user"),
        ("auth", "group"),
        ("auth", "permission"),
        ("admin", "logentry"),
        ("contenttypes", "contenttype"),
        ("sessions", "session"),
    }

    def _collect_permissions(self, tuples_list):
        permisos = []
        missing = []
        for app_label, codename in tuples_list:
            perm = Permission.objects.filter(content_type__app_label=app_label, codename=codename).first()
            if perm:
                permisos.append(perm)
            else:
                missing.append(f"{app_label}.{codename}")
        return permisos, missing

    def _sync_gestor(self, group):
        required_perms, missing = self._collect_permissions(self.GESTOR_REQUIRED)
        if missing:
            self.stdout.write(self.style.WARNING("Permisos no encontrados para Gestor: " + ", ".join(missing)))

        group.permissions.set(required_perms)

        # Limpieza defensiva de permisos prohibidos que hayan quedado por asignaciones manuales
        for perm in list(group.permissions.select_related("content_type")):
            ct = perm.content_type
            if (ct.app_label, ct.model) in self.GESTOR_PROHIBITED_MODELS:
                group.permissions.remove(perm)
                continue

            if any(perm.codename.startswith(prefix) for prefix in self.GESTOR_PROHIBITED_PREFIXES):
                group.permissions.remove(perm)
                continue

            # Bloquear elecciones/padrón por codename aunque cambie el modelo de origen
            codigo = perm.codename.lower()
            if "eleccion" in codigo or "padron" in codigo:
                group.permissions.remove(perm)

        self.stdout.write(self.style.SUCCESS("Gestor sincronizado sin permisos prohibidos."))

    def handle(self, *args, **options):
        groups = {}
        for name in self.BASE_GROUPS:
            group, _ = Group.objects.get_or_create(name=name)
            groups[name] = group

        # Administrador: todos los permisos disponibles
        groups["Administrador"].permissions.set(Permission.objects.all())
        self.stdout.write(self.style.SUCCESS("Administrador sincronizado con todos los permisos."))

        # Gestor: permisos operativos concretos
        self._sync_gestor(groups["Gestor"])

        # Coordinador / Consulta: sólo lectura operativa
        read_tuples = [
            ("afiliados_app", "view_afiliado"),
            ("afiliados_app", "view_comision"),
            ("afiliados_app", "view_comunidad"),
            ("afiliados_app", "view_sector"),
            ("afiliados_app", "view_centrovotacion"),
            ("afiliados_app", "view_perfil"),
            ("afiliados_app", "view_institucion"),
        ]
        read_perms, _ = self._collect_permissions(read_tuples)
        groups["Coordinador"].permissions.set(read_perms)
        groups["Consulta"].permissions.set(read_perms)

        # Digitador: lectura + alta/cambio de afiliado
        digitador_tuples = read_tuples + [
            ("afiliados_app", "add_afiliado"),
            ("afiliados_app", "change_afiliado"),
        ]
        digitador_perms, _ = self._collect_permissions(digitador_tuples)
        groups["Digitador"].permissions.set(digitador_perms)

        self.stdout.write(self.style.SUCCESS("Roles y permisos configurados correctamente. Ejecutado en modo idempotente."))
