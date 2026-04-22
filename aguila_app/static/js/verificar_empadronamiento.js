(function () {
  'use strict';

  console.log('empadronamiento.js cargado');

  function byId(id) {
    return document.getElementById(id);
  }

  function limpiarDpi(valor) {
    return (valor || '').replace(/\D/g, '');
  }

  function getDpiInput() {
    return byId('dpi_afiliado') || document.querySelector('input[name="dpi"]');
  }

  function getDpiInputFromButton(btn) {
    var customInputId = (btn.dataset.dpiInput || '').trim();
    if (customInputId) {
      return byId(customInputId);
    }
    return getDpiInput();
  }

  function setDebug(lines) {
    var debug = byId('emp_debug');
    if (!debug) return;
    debug.textContent = (lines || []).join('\n');
  }

  function setResultado(message, type, outputId) {
    var output = byId(outputId || 'resultado_tse');
    if (!output) return;
    output.innerHTML = '<div class="alert alert-' + type + ' mb-0 py-2">' + message + '</div>';
  }

  function completarSiVacio(id, valor) {
    var field = byId(id);
    if (!field || !valor) return;
    if (!field.value) {
      field.value = valor;
    }
  }

  async function manejarClickVerificar(btn) {
    var dpiInput = getDpiInputFromButton(btn);
    var outputId = (btn.dataset.outputId || 'resultado_tse').trim();
    var endpoint = (btn.dataset.url || '').trim();
    var dpi = limpiarDpi(dpiInput ? dpiInput.value : '');

    var debugLines = [
      'JS OK',
      'URL: ' + (endpoint || '(vacía)'),
      'DPI: ' + (dpi || '(vacío)')
    ];

    if (!endpoint) {
      setDebug(debugLines.concat(['ERROR: data-url ausente']));
      setResultado('No se encontró la URL de verificación.', 'danger', outputId);
      return;
    }

    if (!dpi) {
      setDebug(debugLines.concat(['ERROR: DPI vacío']));
      setResultado('Ingrese DPI primero.', 'warning', outputId);
      return;
    }

    var originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Consultando...';
    setResultado('Consultando padrón local...', 'info', outputId);
    setDebug(debugLines.concat(['Solicitando...']));

    try {
      var response = await fetch(endpoint + '?dpi=' + encodeURIComponent(dpi), {
        method: 'GET',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin'
      });

      var responseText = await response.text();
      var finalUrl = response.url || endpoint;
      var redirected = !!response.redirected;
      var statusLine = 'HTTP: ' + response.status + ' ' + response.statusText;

      var parseado = null;
      try {
        parseado = responseText ? JSON.parse(responseText) : null;
      } catch (_e) {
        parseado = null;
      }

      var extra = [statusLine, 'Final URL: ' + finalUrl, 'Redirected: ' + redirected];

      if (redirected || /\/signin\/?$/i.test(finalUrl)) {
        setResultado('Sesión expirada o redirección a login.', 'warning', outputId);
        setDebug(debugLines.concat(extra, ['Detalle: redirección detectada']));
        return;
      }

      if (!response.ok) {
        if (response.status === 403) {
          setResultado('CSRF o permiso denegado (403).', 'danger', outputId);
        } else if (response.status === 404) {
          setResultado('Endpoint no encontrado (404).', 'danger', outputId);
        } else if (response.status >= 500) {
          setResultado('Error del servidor (500).', 'danger', outputId);
        } else {
          var msg = (parseado && (parseado.error || parseado.message || parseado.mensaje)) || 'Error en verificación.';
          setResultado(msg, 'danger', outputId);
        }

        setDebug(debugLines.concat(extra, ['Body: ' + (responseText || '(vacío)')]));
        return;
      }

      if (!parseado) {
        setResultado('Respuesta no JSON del servidor.', 'danger', outputId);
        setDebug(debugLines.concat(extra, ['Body: ' + (responseText || '(vacío)')]));
        return;
      }

      var empadronado = !!(parseado.ok && (parseado.empadronado || parseado.found));
      var checkbox = byId('id_empadronado');
      if (checkbox) checkbox.checked = empadronado;

      if (empadronado) {
        var persona = parseado.data || {};
        completarSiVacio('id_nombre_completo', persona.nombre_completo);
        completarSiVacio('id_direccion', persona.municipio);
        setResultado('Empadronado: SÍ. ' + (parseado.message || parseado.mensaje || ''), 'success', outputId);
      } else {
        setResultado('Empadronado: NO. ' + (parseado.message || parseado.error || parseado.mensaje || ''), 'warning', outputId);
      }

      setDebug(debugLines.concat(extra, ['JSON: ' + JSON.stringify(parseado)]));
      document.dispatchEvent(new CustomEvent('empadronamiento:resultado', { detail: parseado }));
    } catch (error) {
      setResultado('Error de red al consultar padrón.', 'danger', outputId);
      setDebug(debugLines.concat(['ERROR de red: ' + (error && error.message ? error.message : error)]));
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('#btnVerificarEmpadronamiento');
    if (!btn) return;
    e.preventDefault();
    e.stopPropagation();
    manejarClickVerificar(btn);
  });
})();
