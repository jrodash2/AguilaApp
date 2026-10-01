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
    const switchButton = root.querySelector('[data-camera-switch]');
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
    let cameras = [];
    let activeCameraIndex = -1;
    let activeDeviceId = '';
    let switchingCamera = false;

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

    function videoIsReady() {
      const ready = Boolean(stream && video.readyState >= HTMLMediaElement.HAVE_METADATA && video.videoWidth && video.videoHeight);
      captureButton.disabled = !ready;
      return ready;
    }

    async function listCameras() {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        cameras = [];
        activeCameraIndex = -1;
        switchButton.classList.remove('d-none');
        return;
      }
      try {
        cameras = (await navigator.mediaDevices.enumerateDevices()).filter((device) => device.kind === 'videoinput');
      } catch (exception) {
        cameras = [];
        activeCameraIndex = -1;
        switchButton.classList.remove('d-none');
        return;
      }
      activeCameraIndex = cameras.findIndex((device) => device.deviceId === activeDeviceId);
      // Algunos navegadores ocultan identificadores aunque concedan permiso; en ese caso
      // conservamos el botón para poder recurrir a facingMode.
      switchButton.classList.toggle('d-none', cameras.length === 1);
    }

    async function openCamera(options) {
      const config = options || {};
      const requestId = cameraRequest + 1;
      stopCamera();
      cameraRequest = requestId;
      showMessage('');
      cameraStep.classList.remove('d-none');
      editorStep.classList.add('d-none');
      captureButton.classList.remove('d-none');
      retakeButton.classList.add('d-none');
      useButton.classList.add('d-none');
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
          throw Object.assign(new Error('Unsupported'), { name: 'NotFoundError' });
        }
        const videoConstraint = config.deviceId
          ? { deviceId: { exact: config.deviceId } }
          : (config.facingMode ? { facingMode: { ideal: config.facingMode } } : true);
        const newStream = await navigator.mediaDevices.getUserMedia({ video: videoConstraint, audio: false });
        if (cameraRequest !== requestId) {
          newStream.getTracks().forEach((track) => track.stop());
          return false;
        }
        stream = newStream;
        const track = stream.getVideoTracks()[0];
        const settings = track.getSettings ? track.getSettings() : {};
        activeDeviceId = settings.deviceId || config.deviceId || '';
        const detectedFacingMode = settings.facingMode || config.facingMode || '';
        if (detectedFacingMode) facingMode = detectedFacingMode;
        video.classList.toggle('is-mirrored', detectedFacingMode === 'user');
        video.srcObject = stream;
        try { await video.play(); } catch (playError) { /* autoplay puede resolverse al mostrarse el modal */ }
        videoIsReady();
        await listCameras();
        return true;
      } catch (exception) {
        if (cameraRequest === requestId && !config.silent) showMessage(cameraErrorMessage(exception));
        return false;
      }
    }

    async function changeCamera() {
      if (switchingCamera) return;
      switchingCamera = true;
      switchButton.disabled = true;
      const previous = { deviceId: activeDeviceId, facingMode, index: activeCameraIndex };
      let nextConfig;
      if (cameras.length > 1 && cameras.every((camera) => camera.deviceId)) {
        const current = activeCameraIndex >= 0 ? activeCameraIndex : -1;
        nextConfig = { deviceId: cameras[(current + 1) % cameras.length].deviceId };
      } else {
        nextConfig = { facingMode: facingMode === 'user' ? 'environment' : 'user' };
      }

      const changed = await openCamera(nextConfig);
      if (!changed) {
        const recovered = await openCamera(previous.deviceId
          ? { deviceId: previous.deviceId, silent: true }
          : { facingMode: previous.facingMode, silent: true });
        showMessage(recovered
          ? 'No fue posible cambiar de cámara. Se restauró la cámara anterior.'
          : 'No fue posible cambiar de cámara ni recuperar la cámara anterior. Cierre el modal e intente nuevamente.');
        activeCameraIndex = previous.index;
      }
      switchingCamera = false;
      switchButton.disabled = false;
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
    ['loadedmetadata', 'loadeddata', 'canplay', 'playing'].forEach((eventName) => {
      video.addEventListener(eventName, videoIsReady);
    });
    switchButton.addEventListener('click', changeCamera);
    captureButton.addEventListener('click', function () {
      if (!videoIsReady()) {
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
    retakeButton.addEventListener('click', () => openCamera(activeDeviceId ? { deviceId: activeDeviceId } : { facingMode }));
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

    modalEl.addEventListener('hidden.bs.modal', function () {
      stopCamera();
      drag = null;
      image.onload = null;
      switchingCamera = false;
      switchButton.disabled = false;
    });
    window.addEventListener('resize', clampAndLayout);
    window.addEventListener('pagehide', stopCamera);
  }

  function boot() {
    document.querySelectorAll('[data-foto-persona]').forEach(init);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
}());
