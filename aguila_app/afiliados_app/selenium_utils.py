import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

def verificar_empadronamiento(num_boleta, fecha_nacimiento, tipo_doc='3'):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless")  # puedes activarlo si no quieres ver el navegador

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://tse.org.gt/reg-ciudadanos/sistema-de-estadisticas/consulta-de-afiliacion")

        # 1️⃣ Esperar iframe y acceder
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "blockrandom"))
        )
        driver.switch_to.frame(iframe)

        # 2️⃣ Seleccionar tipo de documento (DPI)
        radio_dpi = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'input[name="tipo_doc"][value="{tipo_doc}"]'))
        )
        radio_dpi.click()

        # 3️⃣ Formatear fecha al formato dd/mm/yyyy
        if "-" in fecha_nacimiento:
            partes = fecha_nacimiento.split("-")
            if len(partes) == 3:
                fecha_nacimiento = f"{partes[2]}/{partes[1]}/{partes[0]}"

        # 4️⃣ Llenar campos
        driver.find_element(By.ID, "num_doc").send_keys(num_boleta)
        fecha_input = driver.find_element(By.ID, "fecha")
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
            fecha_input, fecha_nacimiento
        )

        # 5️⃣ Esperar unos segundos por posible mensaje de error
        time.sleep(1)

        # 🔹 Buscar directamente si existe el texto de advertencia del TSE
        if "Es posible que su empadronamiento sea muy reciente" in driver.page_source:
            mensaje = "❌ El ciudadano no está empadronado o los datos son incorrectos."
            print(mensaje)
            # 🔥 Cierra navegador inmediatamente
            driver.quit()
            return (mensaje, "", "")

        # 6️⃣ Extraer los campos de resultado
        campos = {
            "estado": "textfield",
            "nombre": "textfield2",
            "municipio": "textfield12"
        }

        try:
            WebDriverWait(driver, 5).until(
                EC.visibility_of_element_located((By.ID, campos["estado"]))
            )

            script = f"""
                var estado = document.getElementById('{campos["estado"]}')?.value.trim().toUpperCase() || '';
                var nombre = document.getElementById('{campos["nombre"]}')?.value.trim() || '';
                var municipio = document.getElementById('{campos["municipio"]}')?.value.trim() || '';
                return [estado, nombre, municipio];
            """
            estado_text, nombre_ciudadano, municipio_residencia = driver.execute_script(script)

        except TimeoutException:
            estado_text, nombre_ciudadano, municipio_residencia = "", "", ""

        # 7️⃣ Evaluar resultado
        if estado_text == "ACTIVO":
            mensaje = f"✅ El ciudadano está EMPADRONADO (Estado: ACTIVO)"
        elif estado_text == "INACTIVO":
            mensaje = f"❌ El ciudadano NO está empadronado (Estado: INACTIVO)"
        else:
            mensaje = f"⚠️ No se pudo obtener información del TSE."

        print("\n📋 Resultado del TSE:")
        print(f" - Estado: {estado_text}")
        print(f" - Nombre: {nombre_ciudadano}")
        print(f" - Municipio: {municipio_residencia}")
        print(f" - Mensaje: {mensaje}")

        return (mensaje, nombre_ciudadano, municipio_residencia)

    except Exception as e:
        return (f"❌ Error en Selenium: {str(e)}", "", "")

    finally:
        # Garantiza que siempre se cierre, incluso si hay errores
        try:
            driver.quit()
        except:
            pass
