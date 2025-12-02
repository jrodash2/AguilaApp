import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
import pandas as pd

URL = "https://primeraeleccion.trep.gt/"

SALIDA = Path("trep_resultados_full")
SALIDA.mkdir(exist_ok=True)

async def wait():
    return 1200


async def seleccionar(page, selector, value):
    await page.select_option(selector, value)
    await page.wait_for_timeout(await wait())


# ============================================================
#   🔵  EXTRAE TABLA COMPLETA DE UN CENTRO CON TODAS SUS MESAS
# ============================================================
async def extraer_tabla_centro(page):

    def to_int(value):
        if not value:
            return 0
        v = value.replace(",", "").replace("%", "").strip()
        return int(v) if v.isdigit() else 0

    tablas = page.locator("table")

    if await tablas.count() == 0:
        return []

    tabla_correcta = None

    for i in range(await tablas.count()):
        t = tablas.nth(i)
        headers = await t.locator("thead tr th").all_text_contents()
        headers = [h.strip() for h in headers]
        if "Votos en Blanco" in headers:
            tabla_correcta = t
            break

    if not tabla_correcta:
        return []

    filas = tabla_correcta.locator("tbody tr")

    headers = await tabla_correcta.locator("thead tr th").all_text_contents()
    headers = [h.strip() for h in headers]

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

        votos_inv = to_int(celdas[idx]) if idx < len(celdas) else 0
        observaciones = celdas[-1]

        data.append({
            "mesa": mesa,
            "acta_url": acta,
            "partidos": votos_partido,
            "votos_blanco": votos_blanco,
            "votos_nulos": votos_nulos,
            "votos_total": votos_total,
            "votos_invalidos": votos_inv,
            "observaciones": observaciones,
        })

    return data



# ============================================================
#   🔵 DESCARGA RESULTADOS DE UN TIPO PARA TODO EL PAÍS
# ============================================================
async def scrap_elec(page, tipo_codigo, tipo_nombre):

    print(f"\n==============================")
    print(f"🔵 TIPO: {tipo_nombre}")
    print(f"==============================")

    # cargar tipo
    await page.goto(f"{URL}#!/tc{tipo_codigo}/DIV/")
    await page.wait_for_timeout(2000)

    # listamos todos los departamentos
    dept_options = await page.locator("select[ng-model='formside.selectedDiv'] option").all()

    for d in dept_options:
        dep_value = await d.get_attribute("value")
        dep_text = (await d.text_content() or "").strip()

        if not dep_value or dep_value == "all":
            continue

        print(f"\n🏛 Departamento: {dep_text}")

        await seleccionar(page, "select[ng-model='formside.selectedDiv']", dep_value)

        # listar municipios
        muni_options = await page.locator("select[ng-model='formside.selectedDiv2'] option").all()

        for m in muni_options:
            muni_value = await m.get_attribute("value")
            muni_text = (await m.text_content() or "").strip()

            if not muni_value or muni_value == "all":
                continue

            print(f"   📍 Municipio: {muni_text}")

            await seleccionar(page, "select[ng-model='formside.selectedDiv2']", muni_value)

            # listar centros
            centro_options = await page.locator("select[ng-model='formside.selectedSec'] option").all()

            resultados = []

            for c in centro_options:
                cen_value = await c.get_attribute("value")
                cen_text = (await c.text_content() or "").strip()

                if not cen_value or cen_value == "all":
                    continue

                print(f"      🏫 Centro: {cen_text}")

                await seleccionar(page, "select[ng-model='formside.selectedSec']", cen_value)

                filas = await extraer_tabla_centro(page)

                for fila in filas:
                    fila["departamento"] = dep_text
                    fila["municipio"] = muni_text
                    fila["centro"] = cen_text
                    fila["tipo"] = tipo_nombre

                resultados.extend(filas)

            # guardar municipio
            df = pd.DataFrame(resultados)
            ruta = SALIDA / f"{tipo_nombre}_{dep_text}_{muni_text}.csv"
            df.to_csv(ruta, index=False, encoding="utf-8-sig")
            print(f"      📁 Guardado: {ruta}")


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
