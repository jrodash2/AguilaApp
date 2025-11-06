import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

def verificar_empadronamiento(num_boleta, fecha_nacimiento, tipo_doc='1'):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless")  # Descomenta si quieres que corra sin ventana

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://tse.org.gt/reg-ciudadanos/sistema-de-estadisticas/consulta-de-afiliacion")

        # Esperar el iframe e ingresar
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "blockrandom"))
        )
        driver.switch_to.frame(iframe)

        # Seleccionar tipo de documento
        tipo_radio = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, f'input[name="tipo_doc"][value="{tipo_doc}"]'))
        )
        tipo_radio.click()

        # --- 🔧 Convertir formato de fecha ---
        # Si viene como YYYY-MM-DD → convertir a DD/MM/YYYY
        # Si ya viene como DD/MM/YYYY → dejar igual
        try:
            if '-' in fecha_nacimiento:
                partes = fecha_nacimiento.split('-')
                if len(partes) == 3:
                    fecha_formateada = f"{partes[2]}/{partes[1]}/{partes[0]}"
                else:
                    fecha_formateada = fecha_nacimiento
            else:
                fecha_formateada = fecha_nacimiento
        except Exception:
            fecha_formateada = fecha_nacimiento

        # --- 🧾 Llenar número de documento y fecha ---
        driver.find_element(By.ID, "num_doc").send_keys(num_boleta)
        fecha_input = driver.find_element(By.ID, "fecha")
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
            fecha_input, fecha_formateada
        )

        print("🧩 Esperando que resuelvas el CAPTCHA y se cargue el resultado...")

        # Esperar hasta que aparezca el resultado
        try:
            estado_input = WebDriverWait(driver, 600).until(  # hasta 10 minutos
                EC.presence_of_element_located((By.ID, "textfield"))
            )
            estado_text = estado_input.get_attribute("value").strip().upper()
        except:
            estado_text = "DESCONOCIDO"

        # Evaluar resultado
        if estado_text == "ACTIVO":
            mensaje = "✅ El ciudadano está EMPADRONADO (Estado: ACTIVO)"
        elif estado_text == "INACTIVO":
            mensaje = "❌ El ciudadano NO está empadronado (Estado: INACTIVO)"
        else:
            mensaje = "⚠️ No se pudo determinar el estado del ciudadano."

        print(mensaje)
        time.sleep(2)
        return mensaje

    except Exception as e:
        print(f"❌ Error Selenium: {str(e)}")
        return f"Error Selenium: {str(e)}"

    finally:
        driver.quit()
