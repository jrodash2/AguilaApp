(function () {
  'use strict';

  const OUTPUT_SIZE = 600;
  const JPEG_QUALITY = 0.86;

  function init(root) {
    if (root.dataset.ready) return;
    root.dataset.ready = '1';

    const input = root.querySelector('.foto-persona-input');
    const preview = root.querySelector('[data-photo-preview]');
    const modalEl = root.querySelector('[data-photo-modal]');
    if (!input || !modalEl) return;

    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    const video = root.querySelector('[data-camera-video]');
    const cameraStep = root.querySelector('[data-camera-step]');
    const editorStep = root.querySelector('[data-editor-step]');
    const image = root.querySelector('[data-editor-image]');
    const editor = root.querySelector('[data-photo-editor]');
    const zoom = root.querySelector('[data-photo-zoom]');
    const brightness = root.querySelector('[data-photo-brightness]');
    const contrast = root.querySelector('[data-photo-contrast]');
    const cameraSelect = root.querySelector('[data-camera-select]');
    const captureButton = root.querySelector('[data-photo-capture]');
    const retakeButton = root.querySelector('[data-photo-retake]');
    const useButton = root.querySelector('[data-photo-use]');
    const error = root.querySelector('[data-camera-error]');
    let stream = null;
    let objectUrl = null;
    let naturalWidth = 0;
    let naturalHeight = 0;
    let scale = 1;
    let x = 0;
    let y = 0;
    let drag = null;
    let facingMode = 'user';
    let cameraRequest = 0;

    function stopCamera() {
      cameraRequest += 1;
      if (stream) stream.getTracks().forEach((track) => track.stop());
      stream = null;
      video.srcObject = null;
      captureButton.disabled = true;
    }

    function showMessage(text) {
      error.textContent = text;
      error.classList.toggle('d-none', !text);
    }

    function cameraErrorMessage(exception) {
      if (exception && (exception.name === 'NotAllowedError' || exception.name === 'SecurityError')) {
        return 'El permiso de cámara fue denegado. Habilítelo en el navegador o use “Cargar fotografía”.';
      }
      if (exception && (exception.name === 'NotReadableError' || exception.name === 'AbortError')) {
        return 'La cámara está ocupada por otra aplicación o no pudo iniciarse. Cierre otras aplicaciones e intente nuevamente.';
      }
      if (exception && (exception.name === 'NotFoundError' || exception.name === 'OverconstrainedError')) {
        return 'No se encontró la cámara seleccionada. Elija otra cámara o cargue una fotografía.';
      }
      return 'No fue posible acceder a la cámara. Revise la conexión y los permisos, o use “Cargar fotografía”.';
    }

    async function listCameras(selectedId) {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
      const devices = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === 'videoinput');
      cameraSelect.innerHTML = '';
      if (!devices.length) {
        cameraSelect.appendChild(new Option('No se encontraron cámaras', ''));
        cameraSelect.disabled = true;
        return;
      }
      cameraSelect.disabled = false;
      devices.forEach((device, index) => {
        cameraSelect.appendChild(new Option(device.label || `Cámara ${index + 1}`, device.deviceId));
      });
      const activeId = selectedId || (stream && stream.getVideoTracks()[0] && stream.getVideoTracks()[0].getSettings().deviceId);
      if (activeId && Array.from(cameraSelect.options).some((option) => option.value === activeId)) cameraSelect.value = activeId;
    }

    async function openCamera(deviceId) {
      const requestId = cameraRequest + 1;
      stopCamera();
      cameraRequest = requestId;
      showMessage('');
      cameraStep.classList.remove('d-none');
      editorStep.classList.add('d-none');
      captureButton.classList.remove('d-none');
      retakeButton.classList.add('d-none');
      useButton.classList.add('d-none');
      video.classList.toggle('is-mirrored', !deviceId && facingMode === 'user');
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw Object.assign(new Error('Unsupported'), { name: 'NotFoundError' });
        }
        const videoConstraint = deviceId
          ? { deviceId: { exact: deviceId } }
          : { facingMode: { ideal: facingMode } };
        const newStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false });
        if (cameraRequest !== requestId) {
          newStream.getTracks().forEach((track) => track.stop());
          return;
        }
        stream = newStream;
        video.srcObject = stream;
        const settings = stream.getVideoTracks()[0].getSettings();
        if (settings.facingMode) facingMode = settings.facingMode;
        video.classList.toggle('is-mirrored', facingMode === 'user');
        await listCameras(settings.deviceId);
      } catch (exception) {
        if (cameraRequest === requestId) showMessage(cameraErrorMessage(exception));
      }
    }

    function clampAndLayout() {
      if (!naturalWidth) return;
      const side = editor.clientWidth;
      const baseScale = Math.max(side / naturalWidth, side / naturalHeight);
      const width = naturalWidth * baseScale * scale;
      const height = naturalHeight * baseScale * scale;
      image.style.width = `${width}px`;
      image.style.height = `${height}px`;
      x = Math.min(0, Math.max(side - width, x));
      y = Math.min(0, Math.max(side - height, y));
      image.style.left = `${x}px`;
      image.style.top = `${y}px`;
    }

    function centerImage() {
      const side = editor.clientWidth;
      x = (side - parseFloat(image.style.width || side)) / 2;
      y = (side - parseFloat(image.style.height || side)) / 2;
      clampAndLayout();
    }

    function updateFilters() {
      image.style.filter = `brightness(${brightness.value}%) contrast(${contrast.value}%)`;
    }

    function resetAdjustments() {
      brightness.value = '100';
      contrast.value = '100';
      updateFilters();
    }

    function resetEditor() {
      scale = 1;
      zoom.value = '1';
      resetAdjustments();
      clampAndLayout();
      centerImage();
    }

    function edit(source, revokeSource) {
      stopCamera();
      if (objectUrl) URL.revokeObjectURL(objectUrl);
      objectUrl = revokeSource ? source : null;
      image.onload = function () {
        naturalWidth = image.naturalWidth;
        naturalHeight = image.naturalHeight;
        resetEditor();
      };
      image.src = source;
      cameraStep.classList.add('d-none');
      editorStep.classList.remove('d-none');
      captureButton.classList.add('d-none');
      retakeButton.classList.remove('d-none');
      useButton.classList.remove('d-none');
    }

    function applyPixelFilters(context, width, height) {
      const pixels = context.getImageData(0, 0, width, height);
      const brightnessFactor = Number(brightness.value) / 100;
      const contrastFactor = Number(contrast.value) / 100;
      for (let index = 0; index < pixels.data.length; index += 4) {
        for (let channel = 0; channel < 3; channel += 1) {
          pixels.data[index + channel] = Math.max(0, Math.min(255,
            (pixels.data[index + channel] * brightnessFactor - 128) * contrastFactor + 128
          ));
        }
      }
      context.putImageData(pixels, 0, 0);
    }

    root.querySelector('[data-photo-camera]').addEventListener('click', function () {
      modal.show();
      openCamera();
    });
    root.querySelector('[data-photo-upload]').addEventListener('click', () => input.click());
    root.querySelector('[data-photo-change]').addEventListener('click', () => input.click());
    input.addEventListener('change', function () {
      const file = input.files[0];
      if (!file) return;
      root.querySelector('[data-photo-remove-input]').value = '0';
      modal.show();
      edit(URL.createObjectURL(file), true);
    });
    root.querySelector('[data-photo-remove]').addEventListener('click', function () {
      input.value = '';
      root.querySelector('[data-photo-remove-input]').value = '1';
      preview.src = preview.dataset.placeholder;
    });
    video.addEventListener('loadeddata', function () {
      captureButton.disabled = !(video.videoWidth && stream);
    });
    cameraSelect.addEventListener('change', () => openCamera(cameraSelect.value));
    root.querySelector('[data-camera-switch]').addEventListener('click', function () {
      facingMode = facingMode === 'user' ? 'environment' : 'user';
      cameraSelect.value = '';
      openCamera();
    });
    captureButton.addEventListener('click', function () {
      if (!video.videoWidth || !stream) {
        showMessage('La cámara todavía no está lista. Espere un momento e intente nuevamente.');
        return;
      }
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext('2d');
      // La vista frontal puede estar reflejada, pero el archivo siempre conserva la orientación real.
      context.drawImage(video, 0, 0);
      edit(canvas.toDataURL('image/png'), false);
    });
    retakeButton.addEventListener('click', () => openCamera(cameraSelect.value));
    zoom.addEventListener('input', function () {
      const oldWidth = parseFloat(image.style.width || editor.clientWidth);
      const oldHeight = parseFloat(image.style.height || editor.clientWidth);
      const centerX = x + oldWidth / 2;
      const centerY = y + oldHeight / 2;
      scale = Number(zoom.value);
      clampAndLayout();
      x = centerX - parseFloat(image.style.width) / 2;
      y = centerY - parseFloat(image.style.height) / 2;
      clampAndLayout();
    });
    brightness.addEventListener('input', updateFilters);
    contrast.addEventListener('input', updateFilters);
    root.querySelector('[data-photo-center]').addEventListener('click', centerImage);
    root.querySelector('[data-photo-reset]').addEventListener('click', resetEditor);
    root.querySelector('[data-photo-reset-adjustments]').addEventListener('click', resetAdjustments);
    editor.addEventListener('pointerdown', function (event) {
      drag = { pointerId: event.pointerId, px: event.clientX, py: event.clientY, x, y };
      editor.setPointerCapture(event.pointerId);
    });
    editor.addEventListener('pointermove', function (event) {
      if (!drag || event.pointerId !== drag.pointerId) return;
      x = drag.x + event.clientX - drag.px;
      y = drag.y + event.clientY - drag.py;
      clampAndLayout();
    });
    function endDrag(event) {
      if (drag && event.pointerId === drag.pointerId) drag = null;
    }
    editor.addEventListener('pointerup', endDrag);
    editor.addEventListener('pointercancel', endDrag);
    useButton.addEventListener('click', function () {
      const side = editor.clientWidth;
      const canvas = document.createElement('canvas');
      canvas.width = OUTPUT_SIZE;
      canvas.height = OUTPUT_SIZE;
      const context = canvas.getContext('2d');
      const ratio = OUTPUT_SIZE / side;
      const filterSupported = typeof context.filter === 'string';
      if (filterSupported) context.filter = `brightness(${brightness.value}%) contrast(${contrast.value}%)`;
      context.drawImage(
        image, x * ratio, y * ratio,
        parseFloat(image.style.width) * ratio, parseFloat(image.style.height) * ratio
      );
      if (!filterSupported && (brightness.value !== '100' || contrast.value !== '100')) {
        applyPixelFilters(context, OUTPUT_SIZE, OUTPUT_SIZE);
      }
      canvas.toBlob(function (blob) {
        if (!blob) {
          showMessage('No fue posible procesar la fotografía. Intente nuevamente.');
          return;
        }
        const file = new File([blob], `perfil-${Date.now()}.jpg`, { type: 'image/jpeg' });
        const transfer = new DataTransfer();
        transfer.items.add(file);
        input.files = transfer.files;
        preview.src = URL.createObjectURL(blob);
        root.querySelector('[data-photo-remove-input]').value = '0';
        modal.hide();
      }, 'image/jpeg', JPEG_QUALITY);
    });

    modalEl.addEventListener('hidden.bs.modal', stopCamera);
    window.addEventListener('resize', clampAndLayout);
    window.addEventListener('pagehide', stopCamera);
  }

  function boot() {
    document.querySelectorAll('[data-foto-persona]').forEach(init);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}());
