import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# Se instala solo una vez (rápido)
DRIVER_PATH = ChromeDriverManager().install()

def verificar_empadronamiento(num_boleta, fecha_nacimiento, tipo_doc='3'):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # NO ACTIVAR HEADLESS (rompe el iframe del TSE)
    # options.add_argument("--headless")

    driver = webdriver.Chrome(service=Service(DRIVER_PATH), options=options)

    try:
        driver.get("https://tse.org.gt/reg-ciudadanos/sistema-de-estadisticas/consulta-de-afiliacion")

        wait = WebDriverWait(driver, 10)

        # 1️⃣ Esperar iframe
        iframe = wait.until(
            EC.presence_of_element_located((By.ID, "blockrandom"))
        )
        driver.switch_to.frame(iframe)

        # 2️⃣ Seleccionar tipo de documento
        radio_dpi = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'input[name="tipo_doc"][value=\"{tipo_doc}\"]'))
        )
        radio_dpi.click()

        # 3️⃣ Formatear fecha
        if "-" in fecha_nacimiento:
            y, m, d = fecha_nacimiento.split("-")
            fecha_nacimiento = f"{d}/{m}/{y}"

        # 4️⃣ Llenar datos
        driver.find_element(By.ID, "num_doc").send_keys(num_boleta)

        fecha_input = driver.find_element(By.ID, "fecha")
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
            fecha_input, fecha_nacimiento
        )

        # 5️⃣ Esperar respuesta del TSE
        try:
            wait.until(EC.visibility_of_element_located((By.ID, "textfield")))
        except TimeoutException:
            return ("⚠️ No se pudo obtener respuesta del TSE.", "", "")

        # 6️⃣ Extraer datos
        script = """
            return [
                document.getElementById('textfield')?.value.trim().toUpperCase() || '',
                document.getElementById('textfield2')?.value.trim() || '',
                document.getElementById('textfield12')?.value.trim() || ''
            ];
        """
        estado_text, nombre_ciudadano, municipio_residencia = driver.execute_script(script)

        # 7️⃣ Evaluar resultado
        if estado_text == "ACTIVO":
            mensaje = "✅ El ciudadano está EMPADRONADO (ACTIVO)"
        elif estado_text == "INACTIVO":
            mensaje = "❌ El ciudadano NO está empadronado (INACTIVO)"
        else:
            mensaje = "⚠️ No se pudo obtener información del TSE."

        return (mensaje, nombre_ciudadano, municipio_residencia)

    except Exception as e:
        return (f"❌ Error en Selenium: {str(e)}", "", "")

    finally:
        driver.quit()
