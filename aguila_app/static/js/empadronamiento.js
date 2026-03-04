(function ($) {
  'use strict';

  function limpiarDpi(valor) {
    return (valor || '').replace(/\D/g, '');
  }

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function renderEstado($output, tipo, mensaje) {
    $output.html('<div class="alert alert-' + tipo + ' mb-0 py-2">' + mensaje + '</div>');
  }

  function completarSiVacio(selector, valor) {
    if (!valor) return;
    var $field = $(selector);
    if ($field.length && !$field.val()) {
      $field.val(valor);
    }
  }

  async function verificarEmpadronamiento(event) {
    event.preventDefault();
    event.stopPropagation();

    var $btn = $('#btnVerificarEmp');
    if (!$btn.length) return;

    var endpoint = $btn.data('url');
    var $output = $('#resultadoEmpadronamiento');
    var dpiLimpio = limpiarDpi($('#id_dpi').val());

    if (!dpiLimpio || dpiLimpio.length < 13) {
      renderEstado($output, 'warning', 'Ingrese un DPI válido (13 dígitos).');
      return;
    }

    var originalText = $btn.text();
    $btn.prop('disabled', true).text('Consultando...');
    renderEstado($output, 'info', 'Consultando padrón local...');

    try {
      var response = await fetch(endpoint + '?dpi=' + encodeURIComponent(dpiLimpio), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
          'X-CSRFToken': getCookie('csrftoken') || ''
        },
        credentials: 'same-origin'
      });

      var data = {};
      try {
        data = await response.json();
      } catch (e) {
        data = { ok: false, error: 'Respuesta inválida del servidor.' };
      }

      if (!response.ok) {
        if (response.status === 403) {
          renderEstado($output, 'danger', 'Error CSRF o sesión expirada. Recargue la página e intente de nuevo.');
        } else if (response.status === 404) {
          renderEstado($output, 'danger', 'Endpoint de verificación no disponible (404).');
        } else if (response.status >= 500) {
          renderEstado($output, 'danger', 'Error interno del servidor al consultar padrón.');
        } else {
          renderEstado($output, 'danger', data.error || data.message || 'No fue posible verificar el padrón.');
        }
        $('#id_empadronado').prop('checked', false);
        return;
      }

      if (data.ok && data.found) {
        var persona = data.data || {};
        completarSiVacio('#id_nombre_completo', persona.nombre_completo);
        completarSiVacio('#id_direccion', persona.municipio);
        $('#id_empadronado').prop('checked', true);
        renderEstado($output, 'success', 'Empadronado: SÍ. ' + (data.message || 'Encontrado en padrón local.'));
      } else {
        $('#id_empadronado').prop('checked', false);
        renderEstado($output, 'warning', 'Empadronado: NO. ' + (data.message || 'No se encontró en padrón local.'));
      }
    } catch (error) {
      $('#id_empadronado').prop('checked', false);
      renderEstado($output, 'danger', 'Error de red al consultar padrón. Verifique su conexión e intente de nuevo.');
    } finally {
      $btn.prop('disabled', false).text(originalText);
    }
  }

  $(document).on('click', '#btnVerificarEmp', verificarEmpadronamiento);
})(jQuery);
