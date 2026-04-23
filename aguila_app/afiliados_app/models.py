from asyncio import open_connection
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.db.models import Sum
from django.db.models.signals import post_save
from django.utils import timezone



class EleccionTipo(models.TextChoices):
    PRESIDENTE = "PRESIDENTE", "Presidente y Vicepresidente"
    DIPUTADOS = "DIPUTADOS", "Diputados"
    PARLACEN = "PARLACEN", "Parlacen"
    ALCALDE = "ALCALDE", "Alcalde"
    
    
class Institucion(models.Model):
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    pagina_web = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    logo2 = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return self.nombre


def user_directory_path(instance, filename):
    # El archivo se subirá a MEDIA_ROOT/perfil_usuario/<username>/<filename>
    return f'perfil_usuario/{instance.user.username}/{filename}'

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    cargo = models.CharField(max_length=100, blank=True, null=True) 

    def __str__(self):
        return f'Perfil de {self.user.username}'

# Señal: Crear perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'perfil'):
        Perfil.objects.create(user=instance)

# Señal opcional: Guardar perfil cuando el usuario se guarda
@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    if hasattr(instance, 'perfil'):
        instance.perfil.save()
     
    
class FraseMotivacional(models.Model):
    frase = models.CharField(max_length=500)
    personaje = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.personaje}: {self.frase}'
    




# -------------------------------
# Centro de Votación
# -------------------------------
class CentroVotacion(models.Model):
    nombre = models.CharField(max_length=150)
    ubicacion = models.TextField()

    sectores = models.ManyToManyField(
        'Sector',
        blank=True,
        related_name='centros'
    )

    def __str__(self):
        return f"{self.nombre} - {self.ubicacion}"


# -------------------------------
# Comisión
# -------------------------------
class Comision(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Sector(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class Comunidad(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comunidades"
    )

    def __str__(self):
        return self.nombre


class Afiliado(models.Model):
    class CargoComision(models.TextChoices):
        COORDINADOR = "COORDINADOR", "Coordinador"
        SECRETARIO = "SECRETARIO", "Secretario"
        INTEGRANTE = "INTEGRANTE", "Integrante"

    nombre_completo = models.CharField(max_length=150)
    dpi = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField()
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="afiliados")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="afiliados")
    
    # 🌟 Campo para identificar si este afiliado es un líder
    es_lider_comunitario = models.BooleanField(default=False)

    # 🔗 Relación recursiva para vincularlo a su líder
    lider_vinculado = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referidos",
        limit_choices_to={'es_lider_comunitario': True}
    )

    empadronado = models.BooleanField(default=False)
    comisiones = models.ManyToManyField(Comision, blank=True, related_name="afiliados")
    cargo_en_comision = models.CharField(
        max_length=20,
        choices=CargoComision.choices,
        blank=True,
        null=True,
    )

    # 📅 Nueva columna: Fecha y hora de creación automática
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def sector(self):
        return self.comunidad.sector if self.comunidad else None

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"

    
class OrganizacionIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(
        Afiliado,
        on_delete=models.PROTECT,
        related_name="registros_organizacion",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_organizacion_registrados",
    )
    usuario_modificacion = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_organizacion_modificados",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Organización"
        verbose_name_plural = "Integrantes de Organización"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(fields=["afiliado"], name="uniq_organizacion_afiliado"),
        ]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"



class Eleccion2023(models.Model):
    mesa = models.IntegerField(null=True, blank=True)
    todos = models.IntegerField(null=True, blank=True)
    cambio = models.IntegerField(null=True, blank=True)
    morena = models.IntegerField(null=True, blank=True)
    vamos = models.IntegerField(null=True, blank=True)
    pin = models.IntegerField(null=True, blank=True)
    renovador = models.IntegerField(null=True, blank=True)
    valor = models.IntegerField(null=True, blank=True)
    azul = models.IntegerField(null=True, blank=True)
    une = models.IntegerField(null=True, blank=True)
    fcn_nacion = models.IntegerField(null=True, blank=True)
    podemos = models.IntegerField(null=True, blank=True)
    uc = models.IntegerField(null=True, blank=True)
    votos_blanco = models.IntegerField(null=True, blank=True)
    votos_nulos = models.IntegerField(null=True, blank=True)
    total = models.IntegerField(null=True, blank=True)
    votos_invalidos = models.IntegerField(null=True, blank=True)
    impugnaciones = models.TextField(null=True, blank=True)
    observaciones = models.TextField(null=True, blank=True)
    centro_votacion = models.TextField(null=True, blank=True)
    secnum = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elecciones_2023"

    def __str__(self):
        return f"Mesa {self.mesa} - {self.centro_votacion}"    
    
    
class TrepCentroResultado(models.Model):
    tipo = models.CharField(max_length=20, choices=EleccionTipo.choices)

    departamento = models.CharField(max_length=100)
    municipio = models.CharField(max_length=100)

    centro_codigo = models.CharField(max_length=20, db_index=True)
    centro_nombre = models.CharField(max_length=200, null=True, blank=True)

    mesa = models.CharField(max_length=20, db_index=True)

    acta_url = models.TextField(null=True, blank=True)

    partidos = models.JSONField()

    votos_blanco = models.IntegerField(default=0)
    votos_nulos = models.IntegerField(default=0)
    votos_total = models.IntegerField(default=0)
    votos_invalidos = models.IntegerField(default=0)

    impugnaciones = models.CharField(max_length=50, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Resultado por Mesa"
        verbose_name_plural = "Resultados por Mesa"
        unique_together = ("tipo", "centro_codigo", "mesa")

    def __str__(self):
        return f"{self.tipo} | Centro {self.centro_codigo} | Mesa {self.mesa}"    
    


# afiliados_app/models.py

class PadronElectoral(models.Model):
    nombre = models.CharField(max_length=255)
    edad = models.PositiveIntegerField(null=True, blank=True)
    identificacion = models.CharField(max_length=20, unique=True)  # DPI
    comunidad = models.CharField(max_length=255, null=True, blank=True)
    departamento = models.CharField(max_length=100, null=True, blank=True)
    municipio = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} - {self.identificacion}"


class EstadoRegistro(models.TextChoices):
    ACTIVO = "ACTIVO", "Activo"
    INACTIVO = "INACTIVO", "Inactivo"


class CoordinadorOrganizacion(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_organizacion")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_org_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_org_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class LiderComunitarioOrganizacion(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_organizacion")
    coordinador = models.ForeignKey(CoordinadorOrganizacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_org_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_org_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class EstructuraOrganizativa(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_organizacion")
    coordinador_responsable = models.ForeignKey(CoordinadorOrganizacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_org_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_org_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


class ResponsableTerritorial(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_organizacion")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_org_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_org_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class ReunionTerritorial(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_organizacion")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_org_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_org_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class IncidenciaTerritorial(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_organizacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_organizacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_organizacion")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableTerritorial, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_org_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_org_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.tipo_incidencia


class JuventudIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(
        Afiliado,
        on_delete=models.PROTECT,
        related_name="registros_juventud",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_juventud_registrados",
    )
    usuario_modificacion = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_juventud_modificados",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Juventud"
        verbose_name_plural = "Integrantes de Juventud"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(fields=["afiliado"], name="uniq_juventud_afiliado"),
        ]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"


class CoordinadorJuventud(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_juventud")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_juv_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_juv_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class LiderJuvenil(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_juventud")
    coordinador = models.ForeignKey(CoordinadorJuventud, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_juv_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_juv_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class EstructuraJuventud(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_juventud")
    coordinador_responsable = models.ForeignKey(CoordinadorJuventud, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_juv_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_juv_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


class ResponsableJuventud(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_juventud")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_juv_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_juv_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class ReunionJuventud(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_juventud")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_juv_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_juv_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class IncidenciaJuventud(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_juventud")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_juventud")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_juventud")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableJuventud, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_juv_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_juv_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.tipo_incidencia


class EstructuraIntegranteJuventud(models.Model):
    estructura = models.ForeignKey(EstructuraJuventud, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura_juventud")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_juventud_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_juventud_integrante_dpi"),
        ]
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"




class MujeresIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(
        Afiliado,
        on_delete=models.PROTECT,
        related_name="registros_mujeres",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_mujeres_registrados",
    )
    usuario_modificacion = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_mujeres_modificados",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Mujeres"
        verbose_name_plural = "Integrantes de Mujeres"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(fields=["afiliado"], name="uniq_mujeres_afiliado"),
        ]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"


class CoordinadoraMujeres(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_mujeres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_muj_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_muj_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class LiderMujeres(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_mujeres")
    coordinador = models.ForeignKey(CoordinadoraMujeres, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_muj_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_muj_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class EstructuraMujeres(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_mujeres")
    coordinador_responsable = models.ForeignKey(CoordinadoraMujeres, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_muj_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_muj_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


class ResponsableMujeres(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_mujeres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_muj_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_muj_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class ReunionMujeres(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_mujeres")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_muj_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_muj_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class IncidenciaMujeres(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_mujeres")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_mujeres")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_mujeres")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableMujeres, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_muj_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_muj_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.tipo_incidencia


class EstructuraIntegranteMujeres(models.Model):
    estructura = models.ForeignKey(EstructuraMujeres, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura_mujeres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_mujeres_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_mujeres_integrante_dpi"),
        ]
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"


class LogisticaIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(
        Afiliado,
        on_delete=models.PROTECT,
        related_name="registros_logistica",
    )
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_logistica_registrados",
    )
    usuario_modificacion = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="integrantes_logistica_modificados",
        null=True,
        blank=True,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Logística"
        verbose_name_plural = "Integrantes de Logística"
        ordering = ["-fecha_creacion"]
        constraints = [
            models.UniqueConstraint(fields=["afiliado"], name="uniq_logistica_afiliado"),
        ]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"


class CoordinadorLogistica(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_logistica")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_log_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_log_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class LiderLogistica(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_logistica")
    coordinador = models.ForeignKey(CoordinadorLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_log_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_log_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class EstructuraLogistica(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_logistica")
    coordinador_responsable = models.ForeignKey(CoordinadorLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


class ResponsableLogistica(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_logistica")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_log_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_log_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class ReunionLogistica(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_logistica")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class IncidenciaLogistica(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_logistica")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_logistica")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_logistica")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.tipo_incidencia


class EstructuraIntegranteLogistica(models.Model):
    estructura = models.ForeignKey(EstructuraLogistica, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura_logistica")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_logistica_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_logistica_integrante_dpi"),
        ]
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"


class RecursoLogistico(models.Model):
    class EstadoRecurso(models.TextChoices):
        DISPONIBLE = "DISPONIBLE", "Disponible"
        ASIGNADO = "ASIGNADO", "Asignado"
        MANTENIMIENTO = "MANTENIMIENTO", "Mantenimiento"
        BAJA = "BAJA", "Baja"

    nombre = models.CharField(max_length=150)
    tipo_recurso = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=20, choices=EstadoRecurso.choices, default=EstadoRecurso.DISPONIBLE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recursos_log_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="recursos_log_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return f"{self.nombre} ({self.tipo_recurso})"


class AsignacionLogistica(models.Model):
    class EstadoAsignacion(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        CANCELADA = "CANCELADA", "Cancelada"

    recurso = models.ForeignKey(RecursoLogistico, on_delete=models.PROTECT, related_name="asignaciones")
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones_logistica")
    actividad = models.CharField(max_length=180, blank=True, null=True)
    responsable = models.ForeignKey(ResponsableLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="asignaciones")
    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=EstadoAsignacion.choices, default=EstadoAsignacion.PLANIFICADA)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="asignaciones_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="asignaciones_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.recurso.nombre} - {self.fecha}"


class SolicitudLogistica(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class EstadoSolicitud(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        RESUELTA = "RESUELTA", "Resuelta"
        CANCELADA = "CANCELADA", "Cancelada"

    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitudes_logistica")
    responsable = models.ForeignKey(ResponsableLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="solicitudes")
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=20, choices=EstadoSolicitud.choices, default=EstadoSolicitud.ABIERTA)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="solicitudes_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="solicitudes_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.titulo


class EntregaLogistica(models.Model):
    class EstadoEntrega(models.TextChoices):
        PROGRAMADA = "PROGRAMADA", "Programada"
        ENTREGADA = "ENTREGADA", "Entregada"
        PARCIAL = "PARCIAL", "Parcial"
        CANCELADA = "CANCELADA", "Cancelada"

    solicitud = models.ForeignKey(SolicitudLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas")
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas_logistica")
    responsable = models.ForeignKey(ResponsableLogistica, on_delete=models.SET_NULL, null=True, blank=True, related_name="entregas")
    fecha = models.DateField()
    detalle = models.TextField()
    estado = models.CharField(max_length=20, choices=EstadoEntrega.choices, default=EstadoEntrega.PROGRAMADA)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="entregas_log_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="entregas_log_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"Entrega {self.fecha} - {self.estado}"


class AgendaLogistica(models.Model):
    class EstadoActividad(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        EN_CURSO = "EN_CURSO", "En curso"
        COMPLETADA = "COMPLETADA", "Completada"
        REPROGRAMADA = "REPROGRAMADA", "Reprogramada"

    actividad = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="agenda_logistica")
    responsables = models.TextField(blank=True, null=True)
    fecha_programada = models.DateField()
    estado = models.CharField(max_length=20, choices=EstadoActividad.choices, default=EstadoActividad.PLANIFICADA)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agenda_log_creada")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agenda_log_modificada", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_programada", "-id"]

    def __str__(self):
        return self.actividad


class ComunicacionIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(Afiliado, on_delete=models.PROTECT, related_name="registros_comunicacion")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_comunicacion_registrados")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_comunicacion_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Comunicación y Redes"
        verbose_name_plural = "Integrantes de Comunicación y Redes"
        ordering = ["-fecha_creacion"]
        constraints = [models.UniqueConstraint(fields=["afiliado"], name="uniq_comunicacion_afiliado")]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"


class CoordinadorComunicacion(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_comunicacion")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_com_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_com_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class LiderComunicacion(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres_comunicacion")
    coordinador = models.ForeignKey(CoordinadorComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="lideres")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_com_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="lideres_com_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class EstructuraComunicacion(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_comunicacion")
    coordinador_responsable = models.ForeignKey(CoordinadorComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_com_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_com_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre


class ResponsableComunicacion(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_comunicacion")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_com_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_com_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.nombre_completo


class ReunionComunicacion(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_comunicacion")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_com_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_com_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return self.titulo


class IncidenciaComunicacion(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_comunicacion")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_comunicacion")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_comunicacion")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_com_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_com_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self):
        return self.tipo_incidencia


class EstructuraIntegranteComunicacion(models.Model):
    estructura = models.ForeignKey(EstructuraComunicacion, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura_comunicacion")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_comunicacion_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_comunicacion_integrante_dpi")]
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"


class AgendaPublicacion(models.Model):
    class EstadoPublicacion(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        EN_DISENO = "EN_DISENO", "En diseño"
        PUBLICADA = "PUBLICADA", "Publicada"
        CANCELADA = "CANCELADA", "Cancelada"

    fecha = models.DateField()
    plataforma = models.CharField(max_length=80)
    tipo_contenido = models.CharField(max_length=100)
    estado = models.CharField(max_length=20, choices=EstadoPublicacion.choices, default=EstadoPublicacion.PLANIFICADA)
    responsable = models.ForeignKey(ResponsableComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="agendas_publicaciones")
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agenda_pub_creada")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="agenda_pub_modificada", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class SolicitudContenido(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"
        URGENTE = "URGENTE", "Urgente"

    class Estado(models.TextChoices):
        ABIERTA = "ABIERTA", "Abierta"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        ENTREGADA = "ENTREGADA", "Entregada"
        CANCELADA = "CANCELADA", "Cancelada"

    titulo = models.CharField(max_length=180)
    solicitante = models.CharField(max_length=160)
    area_solicitante = models.CharField(max_length=120)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ABIERTA)
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="solicitudes_contenido_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="solicitudes_contenido_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class CoberturaActividad(models.Model):
    class EstadoCobertura(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "En curso"
        CUBIERTA = "CUBIERTA", "Cubierta"
        CANCELADA = "CANCELADA", "Cancelada"

    actividad = models.CharField(max_length=180)
    fecha = models.DateField()
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coberturas_comunicacion")
    responsable = models.ForeignKey(ResponsableComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coberturas")
    estado_cobertura = models.CharField(max_length=20, choices=EstadoCobertura.choices, default=EstadoCobertura.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coberturas_com_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coberturas_com_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class BancoMedios(models.Model):
    class TipoMedio(models.TextChoices):
        IMAGEN = "IMAGEN", "Imagen"
        VIDEO = "VIDEO", "Video"
        ARTE = "ARTE", "Arte"
        COPY = "COPY", "Copy"
        OTRO = "OTRO", "Otro"

    class Estado(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        ARCHIVADO = "ARCHIVADO", "Archivado"
        DESCARTADO = "DESCARTADO", "Descartado"

    titulo = models.CharField(max_length=180)
    tipo = models.CharField(max_length=20, choices=TipoMedio.choices, default=TipoMedio.IMAGEN)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.ACTIVO)
    referencia = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="medios_com_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="medios_com_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class CampanaComunicacion(models.Model):
    class Estado(models.TextChoices):
        PLANIFICADA = "PLANIFICADA", "Planificada"
        ACTIVA = "ACTIVA", "Activa"
        FINALIZADA = "FINALIZADA", "Finalizada"
        CANCELADA = "CANCELADA", "Cancelada"

    nombre = models.CharField(max_length=180)
    objetivo = models.TextField()
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PLANIFICADA)
    responsable = models.ForeignKey(ResponsableComunicacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="campanas")
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="campanas_com_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="campanas_com_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_inicio", "-id"]


class MonitoreoRed(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        COMPLETADO = "COMPLETADO", "Completado"

    red_social = models.CharField(max_length=80)
    actividad = models.CharField(max_length=180)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="monitoreos_com_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="monitoreos_com_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]



class PlanHormigaIntegrante(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADO = "REVISADO", "Revisado"
        APROBADO = "APROBADO", "Aprobado"

    afiliado = models.ForeignKey(Afiliado, on_delete=models.PROTECT, related_name="registros_plan_hormiga")
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_plan_hormiga_registrados")
    usuario_modificacion = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_plan_hormiga_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Integrante de Plan Hormiga"
        verbose_name_plural = "Integrantes de Plan Hormiga"
        ordering = ["-fecha_creacion"]
        constraints = [models.UniqueConstraint(fields=["afiliado"], name="uniq_plan_hormiga_afiliado")]

    def __str__(self):
        return f"{self.afiliado.nombre_completo} - {self.get_estado_display()}"


class CoordinadorPlanHormiga(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_coordinacion = models.CharField(max_length=100, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="coordinadores_plan_hormiga")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_plan_hormiga_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="coordinadores_plan_hormiga_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class EnlaceTerritorialPlanHormiga(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="enlaces_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="enlaces_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="enlaces_plan_hormiga")
    coordinador = models.ForeignKey(CoordinadorPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name="enlaces")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="enlaces_plan_hormiga_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="enlaces_plan_hormiga_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class EstructuraPlanHormiga(models.Model):
    tipo_estructura = models.CharField(max_length=80)
    nombre = models.CharField(max_length=160)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_plan_hormiga")
    coordinador_responsable = models.ForeignKey(CoordinadorPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name="estructuras_responsables")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    cantidad_integrantes = models.PositiveIntegerField(default=0)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_plan_hormiga_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="estructuras_plan_hormiga_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class ResponsableZonaPlanHormiga(models.Model):
    nombre_completo = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="responsables_plan_hormiga")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_plan_hormiga_creados")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="responsables_plan_hormiga_modificados", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class ReunionPlanHormiga(models.Model):
    class Seguimiento(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    fecha = models.DateField()
    tipo_reunion = models.CharField(max_length=80, blank=True, null=True)
    titulo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="reuniones_plan_hormiga")
    responsables = models.TextField(blank=True, null=True)
    responsable_tipo = models.CharField(max_length=20, blank=True, null=True)
    responsable_referencia_id = models.PositiveIntegerField(blank=True, null=True)
    asistentes = models.PositiveIntegerField(default=0)
    acuerdos = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=Seguimiento.choices, default=Seguimiento.PENDIENTE)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_plan_hormiga_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reuniones_plan_hormiga_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class IncidenciaPlanHormiga(models.Model):
    class Prioridad(models.TextChoices):
        BAJA = "BAJA", "Baja"
        MEDIA = "MEDIA", "Media"
        ALTA = "ALTA", "Alta"

    tipo_incidencia = models.CharField(max_length=120)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_plan_hormiga")
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_plan_hormiga")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_plan_hormiga")
    descripcion = models.TextField()
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    responsable_asignado = models.ForeignKey(ResponsableZonaPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name="incidencias_asignadas")
    seguimiento = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_plan_hormiga_creadas")
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name="incidencias_plan_hormiga_modificadas", null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_creacion"]


class EstructuraIntegrantePlanHormiga(models.Model):
    estructura = models.ForeignKey(EstructuraPlanHormiga, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura_plan_hormiga")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_plan_hormiga_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_plan_hormiga_integrante_dpi")]
        ordering = ["-fecha_registro"]


class VisitaPlanHormiga(models.Model):
    class TipoVisita(models.TextChoices):
        CASA_CASA = "CASA_CASA", "Casa a casa"
        RECORRIDO = "RECORRIDO", "Recorrido"
        REUNION = "REUNION", "Reunión"

    fecha = models.DateField()
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitas_plan_hormiga')
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitas_plan_hormiga')
    responsable = models.ForeignKey(ResponsableZonaPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name='visitas')
    tipo_visita = models.CharField(max_length=20, choices=TipoVisita.choices, default=TipoVisita.RECORRIDO)
    observaciones = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='visitas_plan_hormiga_creadas')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='visitas_plan_hormiga_modificadas', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class SeguimientoContactoPlanHormiga(models.Model):
    class EstadoSeguimiento(models.TextChoices):
        NUEVO = "NUEVO", "Nuevo"
        EN_PROCESO = "EN_PROCESO", "En proceso"
        CERRADO = "CERRADO", "Cerrado"

    persona_contactada = models.CharField(max_length=160)
    dpi = models.CharField(max_length=20, blank=True, null=True)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='seguimientos_plan_hormiga')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    estado_seguimiento = models.CharField(max_length=20, choices=EstadoSeguimiento.choices, default=EstadoSeguimiento.NUEVO)
    observaciones = models.TextField(blank=True, null=True)
    fecha_ultimo_contacto = models.DateField(null=True, blank=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='seguimientos_plan_hormiga_creados')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='seguimientos_plan_hormiga_modificados', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_actualizacion"]


class CompromisoTerritorialPlanHormiga(models.Model):
    class EstadoCompromiso(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_CURSO = "EN_CURSO", "En curso"
        CUMPLIDO = "CUMPLIDO", "Cumplido"

    actividad = models.CharField(max_length=180)
    responsable = models.ForeignKey(ResponsableZonaPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name='compromisos')
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='compromisos_plan_hormiga')
    fecha_compromiso = models.DateField()
    estado = models.CharField(max_length=20, choices=EstadoCompromiso.choices, default=EstadoCompromiso.PENDIENTE)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='compromisos_plan_hormiga_creados')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='compromisos_plan_hormiga_modificados', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_compromiso", "-id"]


class PuntoVisitadoPlanHormiga(models.Model):
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='puntos_visitados_plan_hormiga')
    sector = models.ForeignKey(Sector, on_delete=models.SET_NULL, null=True, blank=True, related_name='puntos_visitados_plan_hormiga')
    responsable = models.ForeignKey(ResponsableZonaPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name='puntos_visitados')
    cantidad_visitada = models.PositiveIntegerField(default=0)
    fecha = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='puntos_visitados_plan_hormiga_creados')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='puntos_visitados_plan_hormiga_modificados', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class ActivacionTerritorialPlanHormiga(models.Model):
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name='activaciones_plan_hormiga')
    responsable = models.ForeignKey(ResponsableZonaPlanHormiga, on_delete=models.SET_NULL, null=True, blank=True, related_name='activaciones')
    tipo_accion = models.CharField(max_length=150)
    fecha = models.DateField()
    resultado = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='activaciones_plan_hormiga_creadas')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='activaciones_plan_hormiga_modificadas', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha", "-id"]


class CoberturaVisitaPlanHormiga(models.Model):
    comunidades_atendidas = models.PositiveIntegerField(default=0)
    comunidades_pendientes = models.PositiveIntegerField(default=0)
    sectores_visitados = models.PositiveIntegerField(default=0)
    sectores_pendientes = models.PositiveIntegerField(default=0)
    fecha_corte = models.DateField()
    observaciones = models.TextField(blank=True, null=True)
    usuario_creador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='coberturas_plan_hormiga_creadas')
    usuario_modificador = models.ForeignKey(User, on_delete=models.PROTECT, related_name='coberturas_plan_hormiga_modificadas', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_corte", "-id"]


class EstructuraIntegrante(models.Model):
    estructura = models.ForeignKey(EstructuraOrganizativa, on_delete=models.CASCADE, related_name="integrantes")
    dpi = models.CharField(max_length=20)
    nombre_completo = models.CharField(max_length=180)
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="integrantes_estructura")
    estado = models.CharField(max_length=15, choices=EstadoRegistro.choices, default=EstadoRegistro.ACTIVO)
    usuario_registro = models.ForeignKey(User, on_delete=models.PROTECT, related_name="integrantes_estructura_registrados")
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["estructura", "dpi"], name="uniq_estructura_integrante_dpi"),
        ]
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"
