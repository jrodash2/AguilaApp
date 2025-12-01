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

    # 📅 Nueva columna: Fecha y hora de creación automática
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    @property
    def sector(self):
        return self.comunidad.sector if self.comunidad else None

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"

    

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