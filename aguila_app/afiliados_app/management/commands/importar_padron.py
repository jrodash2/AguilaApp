import pandas as pd
from django.core.management.base import BaseCommand
from afiliados_app.models import PadronElectoral
from afiliados_app.utils import normalizar_dpi

class Command(BaseCommand):
    help = "Importa el padrón electoral desde un archivo Excel"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help="Ruta al archivo .xlsx")

    def handle(self, *args, **options):
        archivo = options['file']
        # Evita que pandas convierta el DPI a float ("123...0.0") o elimine
        # ceros iniciales; el modelo lo almacena como texto.
        df = pd.read_excel(archivo, dtype=str)

        total = len(df)
        self.stdout.write(self.style.WARNING(f"Importando {total} registros..."))

        for _, row in df.iterrows():
            identificacion = normalizar_dpi(row["IDENTIFICACION"])
            if len(identificacion) != 13:
                self.stderr.write(
                    self.style.WARNING("Se omitió una fila con identificación inválida.")
                )
                continue
            PadronElectoral.objects.update_or_create(
                identificacion=identificacion,
                defaults={
                    "nombre": row["NOMBRE"],
                    "edad": row.get("EDAD", None),
                    "comunidad": row.get("COMUNIDAD", ""),
                    "departamento": row.get("DEPARTAMENTO", ""),
                    "municipio": row.get("MUNICIPIO", ""),
                }
            )

        self.stdout.write(self.style.SUCCESS("Padrón cargado correctamente"))
