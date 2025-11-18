import time
import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = "https://primeraeleccion.trep.gt/#!/tc4/SEC/e4/m3?secNum="


def configurar_driver():
    """Configura y devuelve una instancia de Chrome con Selenium."""
    options = webdriver.ChromeOptions()
    # Si quieres que NO se vea la ventana del navegador, descomenta la siguiente línea:
    # options.add_argument("--headless=new")
    options.add_argument("--start-maximized")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )
    return driver


def es_tabla_de_mesas(encabezados):
    """
    Decide si una tabla parece ser la tabla de resultados por mesa
    según los textos de los encabezados.
    """
    encabezados_lower = [h.lower() for h in encabezados]
    tiene_mesa = any("mesa" in h for h in encabezados_lower)
    tiene_partido = any("partido" in h or "organización" in h or "organizacion" in h for h in encabezados_lower)
    tiene_votos = any("voto" in h or "total" in h for h in encabezados_lower)

    # Ajusta las condiciones según lo que veas en la página
    return tiene_mesa and (tiene_partido or tiene_votos)


def extraer_tabla_mesa(driver, sec_num):
    """
    Abre la página de una sección (sec_num) y extrae la tabla de resultados POR MESA.
    Devuelve un DataFrame de pandas.
    """
    url = f"{BASE_URL}{sec_num}"
    print(f"\n↪ Cargando secNum {sec_num} -> {url}")
    driver.get(url)

    wait = WebDriverWait(driver, 30)

    # Esperar a que Angular cargue el contenido (al menos una tabla)
    wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "table")))

    tablas = driver.find_elements(By.TAG_NAME, "table")
    print(f"  - Encontradas {len(tablas)} tablas en la página")

    tabla_objetivo = None
    encabezados_objetivo = None

    for idx, t in enumerate(tablas):
        filas = t.find_elements(By.TAG_NAME, "tr")
        if not filas:
            continue

        # Encabezados: primera fila (th o td)
        encabezados = [
            th.text.strip()
            for th in filas[0].find_elements(By.XPATH, ".//th|.//td")
        ]

        if not any(encabezados):
            continue

        print(f"    Tabla #{idx}: encabezados = {encabezados}")

        if es_tabla_de_mesas(encabezados):
            print(f"    ✔ Tabla #{idx} parece ser la tabla de resultados por mesa.")
            tabla_objetivo = t
            encabezados_objetivo = encabezados
            break

    if tabla_objetivo is None:
        print(f"❌ No se identificó una tabla de resultados por mesa en secNum {sec_num}")
        return None

    filas = tabla_objetivo.find_elements(By.TAG_NAME, "tr")
    registros = []

    for fila in filas[1:]:
        celdas = fila.find_elements(By.TAG_NAME, "td")
        if not celdas:
            continue
        valores = [c.text.strip() for c in celdas]

        # Rellenar por si vinieran menos columnas
        while len(valores) < len(encabezados_objetivo):
            valores.append("")

        registros.append(valores)

    if not registros:
        print(f"❌ No se encontraron registros (filas de datos) en la tabla de secNum {sec_num}")
        return None

    df = pd.DataFrame(registros, columns=encabezados_objetivo)
    df["secNum"] = sec_num  # Identificador de la sección / centro
    return df


def main():
    driver = configurar_driver()
    dfs = []

    try:
        for sec in range(762, 763):  # 754 al 762 (incluye el 762)
            try:
                df_sec = extraer_tabla_mesa(driver, sec)
                if df_sec is not None:
                    dfs.append(df_sec)
            except Exception as e:
                print(f"⚠ Error procesando secNum {sec}: {e}")
            # Pausa para no saturar el servidor
            time.sleep(2)

    finally:
        driver.quit()

    if not dfs:
        print("❌ No se obtuvo información de ninguna sección.")
        return

    df_total = pd.concat(dfs, ignore_index=True)

    nombre_archivo = "resultados_san_agustin_acasaguastlan_754_762.xlsx"
    df_total.to_excel(nombre_archivo, index=False)
    print(f"\n✅ Archivo Excel generado: {nombre_archivo}")


if __name__ == "__main__":
    main()
