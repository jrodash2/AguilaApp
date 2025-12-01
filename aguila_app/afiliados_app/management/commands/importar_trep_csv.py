from django.core.management.base import BaseCommand
import pandas as pd
from afiliados_app.models import TrepCentroResultado, EleccionTipo

class Command(BaseCommand):
    help = "Importa resultados TREP desde CSV"

    def add_arguments(self, parser):
        parser.add_argument("--file", type=str, required=True)

    def handle(self, *args, **options):
        file = options["file"]
        df = pd.read_csv(file)

        self.stdout.write(self.style.WARNING(f"Importando {len(df)} filas..."))

        count = 0

        for _, row in df.iterrows():
            try:
                TrepCentroResultado.objects.update_or_create(
                    tipo=row["tipo"].upper(),
                    centro_codigo=str(row["centro"]),
                    mesa=str(row["mesa"]),
                    defaults={
                        "departamento": row["departamento"],
                        "municipio": row["municipio"],
                        "acta_url": row["acta_url"] if not pd.isna(row["acta_url"]) else "",
                        "partidos": eval(row["partidos"]),  # convierte string a dict
                        "votos_blanco": int(row["votos_blanco"]),
                        "votos_nulos": int(row["votos_nulos"]),
                        "votos_total": int(row["votos_total"]),
                        "votos_invalidos": int(row["votos_invalidos"]),
                        "impugnaciones": row.get("impugnaciones", ""),
                        "observaciones": row.get("observaciones", ""),
                    }
                )
                count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error fila: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Importación completa: {count} filas cargadas."))
