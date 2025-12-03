import pandas as pd
from django.core.management.base import BaseCommand
from afiliados_app.models import PadronElectoral

class Command(BaseCommand):
    help = "Importa el padrón electoral desde un archivo Excel"

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help="Ruta al archivo .xlsx")

    def handle(self, *args, **options):
        archivo = options['file']
        df = pd.read_excel(archivo)

        total = len(df)
        self.stdout.write(self.style.WARNING(f"Importando {total} registros..."))

        for _, row in df.iterrows():
            PadronElectoral.objects.update_or_create(
                identificacion=row["IDENTIFICACION"],
                defaults={
                    "nombre": row["NOMBRE"],
                    "edad": row.get("EDAD", None),
                    "comunidad": row.get("COMUNIDAD", ""),
                    "departamento": row.get("DEPARTAMENTO", ""),
                    "municipio": row.get("MUNICIPIO", ""),
                }
            )

        self.stdout.write(self.style.SUCCESS("Padrón cargado correctamente"))
