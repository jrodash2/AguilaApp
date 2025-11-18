from django.core.management.base import BaseCommand
import pandas as pd
from afiliados_app.models import Eleccion2023
import numpy as np


class Command(BaseCommand):
    help = "Carga datos de las elecciones 2023 desde un Excel"

    def handle(self, *args, **kwargs):
        archivo_excel = "resultado_san_agustin_754_762.xlsx"

        df = pd.read_excel(archivo_excel)

        # Asignar nombres correctos a las columnas
        df.columns = [
            "mesa", "todos", "cambio", "morena", "vamos", "pin", "renovador",
            "valor", "azul", "une", "fcn_nacion", "podemos", "uc",
            "votos_blanco", "votos_nulos", "total", "votos_invalidos",
            "impugnaciones", "observaciones", "centro_votacion"
        ]

        # Reemplazar valores problemáticos
        df = df.replace({
            "--": None,
            "": None,
            "Acta en Blanco": None,
            np.nan: None
        })

        # Convertir columnas numéricas
        columnas_numericas = [
            "mesa", "todos", "cambio", "morena", "vamos", "pin", "renovador",
            "valor", "azul", "une", "fcn_nacion", "podemos", "uc",
            "votos_blanco", "votos_nulos", "total", "votos_invalidos"
        ]

        for col in columnas_numericas:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("float")

        # Convertir todas las columnas con NaN → None
        df = df.where(pd.notnull(df), None)

        # Construir objetos Django
        objetos = [
            Eleccion2023(**row)
            for row in df.to_dict(orient="records")
        ]

        # Insertar en la base
        Eleccion2023.objects.bulk_create(objetos, batch_size=300)

        self.stdout.write(self.style.SUCCESS("✔ Datos cargados correctamente."))
