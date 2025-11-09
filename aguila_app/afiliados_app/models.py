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
# Comunidad
# -------------------------------
class Comunidad(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    def __str__(self):
        return self.nombre


# -------------------------------
# Centro de Votación
# -------------------------------
class CentroVotacion(models.Model):
    nombre = models.CharField(max_length=150)
    ubicacion = models.TextField()

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



# -------------------------------
# Afiliado (Modelo modificado)
# -------------------------------
class Afiliado(models.Model):
    nombre_completo = models.CharField(max_length=150)
    dpi = models.CharField(max_length=20, unique=True)
    fecha_nacimiento = models.DateField()
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.TextField()
    comunidad = models.ForeignKey(Comunidad, on_delete=models.SET_NULL, null=True, blank=True, related_name="afiliados")
    centro_votacion = models.ForeignKey(CentroVotacion, on_delete=models.SET_NULL, null=True, blank=True, related_name="afiliados")
    
    # 🌟 Campo para identificar si ESTE afiliado es un líder
    es_lider_comunitario = models.BooleanField(default=False)
    
    # 🔗 Clave foránea recursiva para vincular este afiliado a SU líder
    # Solo se puede vincular a otro Afiliado que es un líder.
    lider_vinculado = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name="referidos",
        limit_choices_to={'es_lider_comunitario': True} # Opcional: limita la elección solo a los que son líderes
    )
    
    empadronado = models.BooleanField(default=False)
    comisiones = models.ManyToManyField(Comision, blank=True, related_name="afiliados")

    def __str__(self):
        return f"{self.nombre_completo} ({self.dpi})"