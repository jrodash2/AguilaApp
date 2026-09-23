(function () {
  'use strict';

  var canvas = document.getElementById('carnetAfiliacion');
  if (!canvas) return;

  var context = canvas.getContext('2d');
  var loading = document.getElementById('carnetLoading');
  var errorBox = document.getElementById('carnetError');
  var downloadButton = document.getElementById('descargarCarnet');
  var printButton = document.getElementById('imprimirCarnet');
  var data = canvas.dataset;
  var scale = canvas.width / 856;

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
      image.onload = function () { resolve(image); };
      image.onerror = function () { reject(new Error('No fue posible cargar una imagen del carnet.')); };
      image.src = url;
    });
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
      context.fillStyle = '#315a7d';
      context.font = '700 ' + px(64) + 'px Montserrat, Arial, sans-serif';
      context.textAlign = 'center';
      context.textBaseline = 'middle';
      context.fillText(initials(data.nombre), x + width / 2, y + height / 2);
    }
    context.restore();

    context.save();
    roundedRect(x, y, width, height, radius);
    context.strokeStyle = '#ffffff';
    context.lineWidth = px(5);
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
    context.fillStyle = '#65778a';
    context.font = '600 ' + px(14) + 'px Montserrat, Arial, sans-serif';
    context.fillText(label.toUpperCase(), px(322), px(y));
    context.fillStyle = '#163a5f';
    context.font = '600 ' + px(21) + 'px Montserrat, Arial, sans-serif';
    context.fillText(value, px(322), px(y + 22), px(420));
    return y + 51;
  }

  function renderCard(background, logo, photo) {
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.drawImage(background, 0, 0, canvas.width, canvas.height);

    if (logo) drawContain(logo, px(38), px(22), px(150), px(82));

    context.textAlign = 'left';
    context.textBaseline = 'alphabetic';
    context.fillStyle = '#ffffff';
    context.font = '800 ' + px(29) + 'px Montserrat, Arial, sans-serif';
    context.fillText('CARNET DE AFILIACIÓN', px(318), px(61));
    context.fillStyle = '#dbeafa';
    context.font = '500 ' + px(14) + 'px Montserrat, Arial, sans-serif';
    context.fillText(data.institucion || '', px(320), px(88), px(475));

    drawPhoto(photo);

    var fittedName = fitName(data.nombre, px(460));
    context.fillStyle = '#082d5f';
    context.font = '800 ' + px(fittedName.size) + 'px Montserrat, Arial, sans-serif';
    fittedName.lines.slice(0, 2).forEach(function (line, index) {
      context.fillText(line, px(320), px(239 + index * (fittedName.size + 5)), px(470));
    });

    var detailsY = fittedName.lines.length > 1 ? 305 : 280;
    detailsY = drawLabel('DPI', data.dpi, detailsY);
    detailsY = drawLabel('Comunidad', data.comunidad, detailsY);
    detailsY = drawLabel('Municipio', data.municipio, detailsY);
    drawLabel('Departamento', data.departamento, detailsY);

    context.fillStyle = '#5f7488';
    context.font = '500 ' + px(12) + 'px Montserrat, Arial, sans-serif';
    context.fillText('AFILIACIÓN INSTITUCIONAL', px(54), px(510));
  }

  function showError(message) {
    errorBox.textContent = message;
    errorBox.classList.remove('d-none');
    loading.classList.add('is-hidden');
  }

  Promise.all([
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

  downloadButton.addEventListener('click', function () {
    try {
      canvas.toBlob(function (blob) {
        if (!blob || blob.type !== 'image/jpeg') {
          showError('El navegador no pudo crear el archivo JPEG.');
          return;
        }
        var link = document.createElement('a');
        link.download = 'carnet_afiliado_' + data.afiliadoId + '.jpg';
        link.href = URL.createObjectURL(blob);
        document.body.appendChild(link);
        link.click();
        link.remove();
        setTimeout(function () { URL.revokeObjectURL(link.href); }, 1000);
      }, 'image/jpeg', 0.95);
    } catch (error) {
      showError('No fue posible descargar el carnet. Verifique que las imágenes pertenezcan a este sitio.');
    }
  });

  printButton.addEventListener('click', function () {
    window.print();
  });
}());
