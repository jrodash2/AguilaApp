(function () {
  'use strict';

  function byId(id) {
    return document.getElementById(id);
  }

  function limpiarDpi(valor) {
    return (valor || '').replace(/\D/g, '');
  }

  function renderResultado(mensaje, tipo) {
    var contenedor = byId('resultado_tse') || byId('resultadoEmpadronamiento');
    if (!contenedor) return;
    contenedor.innerHTML = '<div class="alert alert-' + tipo + ' mb-0 py-2">' + mensaje + '</div>';
  }

  function completarSiVacio(id, valor) {
    var campo = byId(id);
    if (!campo || !valor) return;
    if (!campo.value) {
      campo.value = valor;
    }
  }

  async function onVerificarClick(event) {
    event.preventDefault();
    event.stopPropagation();

    var boton = event.currentTarget;
    var dpiInput = byId('dpi_afiliado') || byId('id_dpi');
    var endpoint = boton.dataset.url;

    if (!endpoint) {
      renderResultado('No se encontró la URL de verificación.', 'danger');
      return;
    }

    var dpi = limpiarDpi(dpiInput ? dpiInput.value : '');
    if (!dpi || dpi.length !== 13) {
      renderResultado('Ingrese un DPI válido (13 dígitos).', 'warning');
      return;
    }

    var textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = 'Consultando...';
    renderResultado('Consultando padrón local...', 'info');

    try {
      var response = await fetch(endpoint + '?dpi=' + encodeURIComponent(dpi), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest'
        },
        credentials: 'same-origin'
      });

      var data;
      try {
        data = await response.json();
      } catch (_e) {
        data = { ok: false, error: 'Respuesta inválida del servidor.' };
      }

      if (!response.ok) {
        if (response.status === 404) {
          renderResultado('Endpoint no disponible (404).', 'danger');
        } else if (response.status === 403) {
          renderResultado('Sesión expirada o acceso denegado (403).', 'danger');
        } else if (response.status >= 500) {
          renderResultado('Error interno del servidor (500).', 'danger');
        } else {
          renderResultado(data.error || data.message || 'No fue posible verificar el empadronamiento.', 'danger');
        }
        var emp = byId('id_empadronado');
        if (emp) emp.checked = false;
        return;
      }

      var empadronado = !!(data.ok && (data.empadronado || data.found));
      var checkbox = byId('id_empadronado');
      if (checkbox) checkbox.checked = empadronado;

      if (empadronado) {
        var persona = data.data || {};
        completarSiVacio('id_nombre_completo', persona.nombre_completo);
        completarSiVacio('id_direccion', persona.municipio);
        renderResultado('Empadronado: SÍ. ' + (data.message || 'Encontrado en padrón local.'), 'success');
      } else {
        renderResultado('Empadronado: NO. ' + (data.message || 'No se encontró en padrón local.'), 'warning');
      }
    } catch (error) {
      renderResultado('Error de red al consultar padrón. Intente nuevamente.', 'danger');
      var empadronadoInput = byId('id_empadronado');
      if (empadronadoInput) empadronadoInput.checked = false;
    } finally {
      boton.disabled = false;
      boton.textContent = textoOriginal;
    }
  }

  function init() {
    var boton = byId('btnVerificarEmpadronamiento');
    if (!boton) return;
    boton.addEventListener('click', onVerificarClick);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
