(function () {
  'use strict';

  var canvas = document.getElementById('carnetAfiliacion');
  if (!canvas) return;

  var context = canvas.getContext('2d');
  var loading = document.getElementById('carnetLoading');
  var errorBox = document.getElementById('carnetError');
  var downloadButton = document.getElementById('descargarCarnet');
  var printButton = document.getElementById('imprimirCarnet');
  var previewShell = canvas.closest('.carnet-preview-shell');
  var qrImage = document.getElementById('qrValidacion');
  var qrLink = qrImage ? qrImage.closest('.qr-validacion-link') : null;
  var data = canvas.dataset;
  var scale = canvas.width / 856;
  var cardTextColor = window.getComputedStyle(canvas)
    .getPropertyValue('--carnet-accent-color').trim() || '#0d47a1';

  function px(value) {
    return value * scale;
  }

  function loadImage(url) {
    return new Promise(function (resolve, reject) {
      if (!url) {
        resolve(null);
        return;
      }
      var image = new Image();
      image.onload = function () {
        if (typeof image.decode === 'function') {
          image.decode().catch(function () {
            // El evento load confirma que la imagen ya puede dibujarse.
          }).then(function () { resolve(image); });
          return;
        }
        resolve(image);
      };
      image.onerror = function () { reject(new Error('No fue posible cargar una imagen del carnet.')); };
      image.src = url;
    });
  }

  function esperarImagenes(contenedor) {
    if (!contenedor) return Promise.resolve();
    var imagenes = Array.prototype.slice.call(contenedor.querySelectorAll('img'));
    return Promise.all(imagenes.map(function (image) {
      var cargada = image.complete && image.naturalWidth > 0
        ? Promise.resolve()
        : new Promise(function (resolve, reject) {
          image.addEventListener('load', resolve, { once: true });
          image.addEventListener('error', reject, { once: true });
        });

      return cargada.then(function () {
        if (typeof image.decode !== 'function') return undefined;
        return image.decode().catch(function () {
          // Puede estar decodificada después del evento load.
        });
      });
    }));
  }

  function esperarPintado() {
    return new Promise(function (resolve) {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(resolve);
      });
    });
  }

  function validarQrDibujado(contexto, x, y, width, height) {
    var muestra = contexto.getImageData(
      Math.max(0, Math.floor(x)),
      Math.max(0, Math.floor(y)),
      Math.max(1, Math.floor(width)),
      Math.max(1, Math.floor(height))
    ).data;
    var pixelesOscuros = 0;
    var pixelesClaros = 0;
    var salto = Math.max(4, Math.floor(muestra.length / 16000 / 4) * 4);

    for (var index = 0; index < muestra.length; index += salto) {
      var luminosidad = (muestra[index] * 299 + muestra[index + 1] * 587 + muestra[index + 2] * 114) / 1000;
      if (luminosidad < 120) pixelesOscuros += 1;
      if (luminosidad > 220) pixelesClaros += 1;
    }

    if (!pixelesOscuros || !pixelesClaros) {
      throw new Error('No fue posible verificar el QR en el carnet exportado.');
    }
  }

  function canvasToJpegDataUrl(exportCanvas) {
    var dataUrl = exportCanvas.toDataURL('image/jpeg', 0.95);
    if (dataUrl.indexOf('data:image/jpeg') !== 0) {
      throw new Error('El navegador no pudo crear el archivo JPEG.');
    }
    return dataUrl;
  }

  function drawCover(image, x, y, width, height) {
    var ratio = Math.max(width / image.naturalWidth, height / image.naturalHeight);
    var sourceWidth = width / ratio;
    var sourceHeight = height / ratio;
    var sourceX = (image.naturalWidth - sourceWidth) / 2;
    var sourceY = (image.naturalHeight - sourceHeight) / 2;
    context.drawImage(image, sourceX, sourceY, sourceWidth, sourceHeight, x, y, width, height);
  }

  function drawContain(image, x, y, width, height) {
    var ratio = Math.min(width / image.naturalWidth, height / image.naturalHeight);
    var targetWidth = image.naturalWidth * ratio;
    var targetHeight = image.naturalHeight * ratio;
    context.drawImage(image, x + (width - targetWidth) / 2, y + (height - targetHeight) / 2, targetWidth, targetHeight);
  }

  function roundedRect(x, y, width, height, radius) {
    context.beginPath();
    context.moveTo(x + radius, y);
    context.arcTo(x + width, y, x + width, y + height, radius);
    context.arcTo(x + width, y + height, x, y + height, radius);
    context.arcTo(x, y + height, x, y, radius);
    context.arcTo(x, y, x + width, y, radius);
    context.closePath();
  }

  function initials(name) {
    var words = (name || '').trim().split(/\s+/).filter(Boolean);
    if (!words.length) return 'AF';
    return (words[0].charAt(0) + (words.length > 1 ? words[words.length - 1].charAt(0) : '')).toUpperCase();
  }

  function drawPhoto(photo) {
    var x = px(54);
    var y = px(178);
    var width = px(210);
    var height = px(286);
    var radius = px(16);

    context.save();
    roundedRect(x, y, width, height, radius);
    context.clip();
    if (photo) {
      drawCover(photo, x, y, width, height);
    } else {
      var gradient = context.createLinearGradient(x, y, x + width, y + height);
      gradient.addColorStop(0, '#dce8f4');
      gradient.addColorStop(1, '#b9ccdf');
      context.fillStyle = gradient;
      context.fillRect(x, y, width, height);
      context.fillStyle = cardTextColor;
      context.font = '700 ' + px(64) + 'px Montserrat, Arial, sans-serif';
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(initials(data.nombre), x + width / 2, y + height / 2);
    }
    context.restore();

    context.save();
    roundedRect(x, y, width, height, radius);
    context.strokeStyle = cardTextColor;
    context.lineWidth = px(2);
    context.stroke();
    context.restore();
  }

  function fitName(name, maxWidth) {
    var words = (name || 'Afiliado').trim().split(/\s+/);
    var fontSize = 35;
    while (fontSize >= 25) {
      context.font = '800 ' + px(fontSize) + 'px Montserrat, Arial, sans-serif';
      var lines = [];
      var current = '';
      words.forEach(function (word) {
        var candidate = current ? current + ' ' + word : word;
        if (current && context.measureText(candidate).width > maxWidth) {
          lines.push(current);
          current = word;
        } else {
          current = candidate;
        }
      });
      if (current) lines.push(current);
      if (lines.length <= 2 && lines.every(function (line) { return context.measureText(line).width <= maxWidth; })) {
        return { lines: lines, size: fontSize };
      }
      fontSize -= 2;
    }
    return { lines: [words.join(' ')], size: 23 };
  }

  function drawLabel(label, value, y) {
    if (!value) return y;
    context.fillStyle = cardTextColor;
    context.font = '600 ' + px(14) + 'px Montserrat, Arial, sans-serif';
    context.fillText(label.toUpperCase(), px(322), px(y));
    context.fillStyle = cardTextColor;
    context.font = '600 ' + px(21) + 'px Montserrat, Arial, sans-serif';
    context.fillText(value, px(322), px(y + 22), px(420));
    return y + 51;
  }

  function renderCard(background, logo, photo) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    drawCover(background, 0, 0, canvas.width, canvas.height);

    if (logo) drawContain(logo, px(38), px(22), px(150), px(82));

    context.textAlign = 'left';
    context.textBaseline = 'alphabetic';
    context.fillStyle = cardTextColor;
    context.font = '800 ' + px(35) + 'px Montserrat, Arial, sans-serif';
    context.fillText('CARNET DE AFILIACIÓN', px(218), px(61));
    context.fillStyle = cardTextColor;
    context.font = '500 ' + px(14) + 'px Montserrat, Arial, sans-serif';
    context.fillText(data.institucion || '', px(320), px(88), px(370));

    context.save();
    context.textAlign = 'center';
    context.fillStyle = cardTextColor;
    context.font = '700 ' + px(16) + 'px Montserrat, Arial, sans-serif';
    context.fillText('CÓDIGO DE AFILIACIÓN:', px(159), px(505));
    context.font = '800 ' + px(16) + 'px Montserrat, Arial, sans-serif';
    context.fillText(data.codigo, px(490), px(505));
    context.restore();

    context.save();
    context.textAlign = 'right';
    context.fillStyle = cardTextColor;
    context.font = '700 ' + px(16) + 'px Montserrat, Arial, sans-serif';

    context.restore();

    drawPhoto(photo);

    var fittedName = fitName(data.nombre, px(460));
    context.fillStyle = cardTextColor;
    context.font = '800 ' + px(fittedName.size) + 'px Montserrat, Arial, sans-serif';
    fittedName.lines.slice(0, 2).forEach(function (line, index) {
      context.fillText(line, px(320), px(210 + index * (fittedName.size + 5)), px(470));
    });

    var detailsY = fittedName.lines.length > 1 ? 280 : 280;
    detailsY = drawLabel('DPI', data.dpi, detailsY);
    detailsY = drawLabel('Comunidad', data.comunidad, detailsY);
    detailsY = drawLabel('Municipio', data.municipio, detailsY);
    drawLabel('Departamento', data.departamento, detailsY);

    context.fillStyle = cardTextColor;
    context.font = '500 ' + px() + 'px Montserrat, Arial, sans-serif';

  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove('d-none');
    loading.classList.add('is-hidden');
  }

  var renderPromise = Promise.all([
    loadImage(data.fondoUrl),
    loadImage(data.logoUrl).catch(function () { return null; }),
    loadImage(data.fotoUrl).catch(function () { return null; }),
    document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve()
  ]).then(function (assets) {
    if (!assets[0]) throw new Error('No fue posible cargar el fondo SVG del carnet.');
    renderCard(assets[0], assets[1], assets[2]);
    loading.classList.add('is-hidden');
    downloadButton.disabled = false;
    printButton.disabled = false;
  }).catch(function (error) {
    showError(error.message || 'No fue posible generar la vista previa del carnet.');
  });

  downloadButton.addEventListener('click', async function () {
    try {
      await renderPromise;
      await esperarImagenes(previewShell);
      await esperarPintado();
      if (!qrImage || !qrLink || !qrImage.complete || qrImage.naturalWidth === 0) {
        throw new Error('No fue posible cargar el código QR del carnet.');
      }
      if (!previewShell.contains(qrImage)) {
        throw new Error('El código QR no está dentro del carnet.');
      }
      if (typeof window.html2canvas !== 'function') {
        throw new Error('No fue posible iniciar la captura del carnet.');
      }

      var carnetRect = previewShell.getBoundingClientRect();
      var qrRect = qrLink.getBoundingClientRect();
      var exportQrImage = await loadImage(qrImage.currentSrc || qrImage.src);
      var previousVisibility = qrLink.style.visibility;
      var exportCanvas;

      qrLink.style.visibility = 'hidden';
      try {
        exportCanvas = await window.html2canvas(previewShell, {
          scale: 2,
          useCORS: true,
          backgroundColor: null,
          logging: false
        });
      } finally {
        qrLink.style.visibility = previousVisibility;
      }

      var scaleX = exportCanvas.width / carnetRect.width;
      var scaleY = exportCanvas.height / carnetRect.height;
      var qrX = (qrRect.left - carnetRect.left) * scaleX;
      var qrY = (qrRect.top - carnetRect.top) * scaleY;
      var qrWidth = qrRect.width * scaleX;
      var qrHeight = qrRect.height * scaleY;
      var exportContext = exportCanvas.getContext('2d');
      exportContext.drawImage(
        exportQrImage,
        qrX,
        qrY,
        qrWidth,
        qrHeight
      );
      validarQrDibujado(exportContext, qrX, qrY, qrWidth, qrHeight);

      var link = document.createElement('a');
      link.download = 'carnet_afiliado_' + data.afiliadoId + '.jpg';
      link.href = canvasToJpegDataUrl(exportCanvas);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      showError(error.message || 'No fue posible descargar el carnet.');
    }
  });

  printButton.addEventListener('click', function () {
    window.print();
  });
}());
