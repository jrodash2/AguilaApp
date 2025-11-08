import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException 

def verificar_empadronamiento(num_boleta, fecha_nacimiento, tipo_doc='1'):
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--headless") 

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get("https://tse.org.gt/reg-ciudadanos/sistema-de-estadisticas/consulta-de-afiliacion")

        # 1. Esperar el iframe e ingresar
        iframe = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "blockrandom"))
        )
        driver.switch_to.frame(iframe)

        # 2. Seleccionar DPI y Llenar campos
        radio_dpi = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, 'input[name="tipo_doc"][value="3"]'))
        )
        radio_dpi.click()

        fecha_formateada = fecha_nacimiento
        try:
            if '-' in fecha_nacimiento:
                partes = fecha_nacimiento.split('-')
                if len(partes) == 3:
                    fecha_formateada = f"{partes[2]}/{partes[1]}/{partes[0]}"
        except Exception:
             pass

        driver.find_element(By.ID, "num_doc").send_keys(num_boleta)
        fecha_input = driver.find_element(By.ID, "fecha")
        driver.execute_script(
            "arguments[0].value = arguments[1]; arguments[0].dispatchEvent(new Event('change'));",
            fecha_input, fecha_formateada
        )
        

        # --- BLOQUE DE EXTRACCIÓN DE RESULTADOS ---
        nombre_ciudadano = ""
        estado_text = "DESCONOCIDO"
        STATUS_FIELD_ID = "textfield" 
        NAME_FIELD_ID = "textfield2" 

        try:
            # 1. Esperamos hasta que el campo de estado esté visible (CAPTHA resuelto)
            WebDriverWait(driver, 600).until(
                EC.visibility_of_element_located((By.ID, STATUS_FIELD_ID))
            )
            
            # 2. Inyectamos JavaScript para leer los valores DIRECTAMENTE
            script = f"""
                var estado = document.getElementById('{STATUS_FIELD_ID}').value.trim().toUpperCase();
                var nombre = '';
                var nombre_el = document.getElementById('{NAME_FIELD_ID}');
                if (nombre_el) {{
                    nombre = nombre_el.value.trim();
                }}
                return [estado, nombre];
            """
            
            estado_text, nombre_ciudadano = driver.execute_script(script)
            
        except TimeoutException:
            estado_text = "DESCONOCIDO"
            nombre_ciudadano = ""
        except Exception as e:
            print(f"Error al obtener los campos de resultado: {e}")
            estado_text = "DESCONOCIDO"
            nombre_ciudadano = ""


        # Evaluar resultado
        if estado_text == "ACTIVO":
            mensaje = "✅ El ciudadano está EMPADRONADO (Estado: ACTIVO)"
        elif estado_text == "INACTIVO":
            mensaje = "❌ El ciudadano NO está empadronado (Estado: INACTIVO)"
        else:
            mensaje = "⚠️ No se pudo determinar el estado del ciudadano. Revise los datos y la resolución del CAPTCHA."

        print(mensaje)
        
        # 🎯 NUEVO: Pausa de 10 segundos para visualización, solo si la extracción fue exitosa
        if estado_text != "DESCONOCIDO":
            print(f"La información se mostrará durante 10 segundos para confirmación.")
            time.sleep(10)
        
        return (mensaje, nombre_ciudadano)

    except Exception as e:
        print(f"❌ Error Selenium General: {str(e)}")
        return (f"Error Selenium General: {str(e)}", "")

    finally:
        # 🎯 driver.quit() cierra la ventana
        driver.quit()