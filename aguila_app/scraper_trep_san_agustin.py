import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import pandas as pd

URL = "https://primeraeleccion.trep.gt/"

DEPARTAMENTO = "string:e4"  # El Progreso
MUNICIPIO = "string:m3"     # San Agustín Acasaguastlán

SALIDA = Path("trep_resultados")
SALIDA.mkdir(exist_ok=True)


async def wait():
    return 1500


async def seleccionar(page, selector, value):
    await page.select_option(selector, value)
    await page.wait_for_timeout(await wait())


# ============================================================
#   🔵  EXTRAE TABLA COMPLETA DE UN CENTRO CON TODAS SUS MESAS
# ============================================================
async def extraer_tabla_centro(page):

    # Convierte valores a int sin romper
    def to_int(value):
        if not value:
            return 0
        v = value.replace(",", "").replace("%", "").strip()
        return int(v) if v.isdigit() else 0

    # Buscar tablas
    tablas = page.locator("table")

    if await tablas.count() == 0:
        return []

    tabla_correcta = None

    # Buscar tabla que tenga columna "Votos en Blanco"
    for i in range(await tablas.count()):
        t = tablas.nth(i)
        headers = await t.locator("thead tr th").all_text_contents()
        headers = [h.strip() for h in headers]
        if "Votos en Blanco" in headers:
            tabla_correcta = t
            break

    if not tabla_correcta:
        print("⚠ No se encontró tabla correcta, saltando…")
        return []

    filas = tabla_correcta.locator("tbody tr")

    headers = await tabla_correcta.locator("thead tr th").all_text_contents()
    headers = [h.strip() for h in headers]

    # Buscar partidos reales
    try:
        idx_blanco = headers.index("Votos en Blanco")
    except:
        return []

    partidos = headers[2:idx_blanco]

    data = []

    for fila in await filas.all():

        celdas = await fila.locator("td, th").all_text_contents()
        celdas = [c.strip() for c in celdas]

        if len(celdas) < 5:
            continue

        mesa = celdas[0]

        # Acta URL
        acta = ""
        links = fila.locator("a")
        if await links.count() > 0:
            acta = await links.first.get_attribute("href")

        idx = 2
        votos_partido = {}
        for p in partidos:
            votos_partido[p] = to_int(celdas[idx])
            idx += 1

        votos_blanco = to_int(celdas[idx]); idx += 1
        votos_nulos = to_int(celdas[idx]); idx += 1
        votos_total = to_int(celdas[idx]); idx += 1

        votos_inv = 0
        impugn = ""
        if idx < len(celdas) - 1:
            votos_inv = to_int(celdas[idx]); idx += 1
        if idx < len(celdas) - 1:
            impugn = celdas[idx]; idx += 1

        observaciones = celdas[-1]

        data.append({
            "mesa": mesa,
            "acta_url": acta,
            "partidos": votos_partido,
            "votos_blanco": votos_blanco,
            "votos_nulos": votos_nulos,
            "votos_total": votos_total,
            "votos_invalidos": votos_inv,
            "impugnaciones": impugn,
            "observaciones": observaciones,
        })

    return data



# ============================================================
#   🔵 SCRAPEA TODO TIPO (presidente, diputados, parlacen…)
# ============================================================
async def scrap_elec(page, tipo_codigo, nombre_archivo):
    print(f"\n🔵 Procesando: {nombre_archivo}")

    # cargar página del tipo
    await page.goto(f"{URL}#!/tc{tipo_codigo}/DIV/e04/m03")
    await page.wait_for_timeout(2000)

    # seleccionar depto/muni
    await seleccionar(page, "select[ng-model='formside.selectedDiv']", DEPARTAMENTO)
    await seleccionar(page, "select[ng-model='formside.selectedDiv2']", MUNICIPIO)

    centros = await page.locator("select[ng-model='formside.selectedSec'] option").all()
    resultados = []

    for centro in centros:
        centro_value = await centro.get_attribute("value")
        centro_text = (await centro.text_content() or "").strip()

        if not centro_value or centro_value == "all":
            continue

        print(f" 🏫 Centro: {centro_text}")

        await seleccionar(page, "select[ng-model='formside.selectedSec']", centro_value)

        # EXTRAER TODAS LAS MESAS DE ESTE CENTRO
        filas = await extraer_tabla_centro(page)

        for fila in filas:
            fila["centro"] = centro_text
            fila["departamento"] = "El Progreso"
            fila["municipio"] = "San Agustín Acasaguastlán"
            fila["tipo"] = nombre_archivo

        resultados.extend(filas)

    df = pd.DataFrame(resultados)
    ruta = SALIDA / f"{nombre_archivo}.csv"
    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    print(f"📁 Guardado: {ruta}")


# ============================================================
#   🔵 MAIN
# ============================================================
async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto(URL)
        await page.wait_for_timeout(2000)

        await scrap_elec(page, "1", "presidente")
        await scrap_elec(page, "2", "diputados")
        await scrap_elec(page, "3", "parlacen")
        await scrap_elec(page, "4", "alcalde")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())


# python -m pip install playwright
