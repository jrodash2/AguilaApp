(function () {
  'use strict';
  const app = document.getElementById('reportes-app');
  if (!app) return;
  const form = document.getElementById('reporte-filtros');
  const error = document.getElementById('reporte-error');
  const status = document.getElementById('reporte-estado');
  const table = document.getElementById('reporte-tabla');
  const base = JSON.parse(document.getElementById('reporte-columnas-basicas').textContent);
  const checkboxes = Array.from(document.querySelectorAll('[name="reporte-columna"]'));
  let columns = base.slice(), applied = new URLSearchParams(), page = 1, pages = 1;
  let sort = '', direction = 'asc', controller, chart;
  const noSort = new Set(['numero', 'secretarias', 'comisiones']);
  function showError(message) { error.textContent = message; error.hidden = false; }
  function clearErrors() {
    error.hidden = true;
    document.querySelectorAll('[data-error]').forEach(el => { el.textContent = ''; });
  }
  function params() {
    const query = new URLSearchParams(applied);
    query.set('configuradas', 'on');
    columns.forEach(key => query.append('columnas', key));
    query.set('cantidad', document.getElementById('reporte-cantidad').value);
    query.set('pagina', page);
    if (sort) { query.set('orden', sort); query.set('direccion', direction); }
    return query;
  }
  function busy(value, message) {
    status.textContent = value ? message : '';
    app.setAttribute('aria-busy', String(value));
    document.querySelectorAll('[data-export]').forEach(el => { el.disabled = value; });
  }
  function cell(tag, text) {
    const node = document.createElement(tag);
    node.textContent = text == null ? '' : String(text);
    return node;
  }
  function display(value, key) {
    if (key === 'creacion' && value) return value.replace('T', ' ').slice(0, 16);
    return key === 'porcentaje' ? `${value}%` : value;
  }
  function render(data) {
    document.querySelectorAll('[data-stat]').forEach(el => { el.textContent = data.estadisticas[el.dataset.stat]; });
    table.tHead.replaceChildren(); table.tBodies[0].replaceChildren();
    const head = document.createElement('tr');
    data.columnas.forEach(([key, label]) => {
      const th = cell('th', ''); th.scope = 'col';
      if (!noSort.has(key)) {
        const btn = cell('button', label + (sort === key ? (direction === 'asc' ? ' ↑' : ' ↓') : ' ↕'));
        btn.type = 'button'; btn.title = `Ordenar por ${label}`;
        btn.addEventListener('click', () => { direction = sort === key && direction === 'asc' ? 'desc' : 'asc'; sort = key; page = 1; load(); });
        th.append(btn);
        if (sort === key) th.setAttribute('aria-sort', direction === 'asc' ? 'ascending' : 'descending');
      } else th.textContent = label;
      head.append(th);
    });
    table.tHead.append(head);
    data.filas.forEach(row => {
      const tr = document.createElement('tr');
      row.forEach((value, i) => tr.append(cell('td', display(value, data.columnas[i][0]))));
      table.tBodies[0].append(tr);
    });
    if (!data.filas.length) {
      const tr = document.createElement('tr'), td = cell('td', 'No se encontraron resultados con estos filtros.');
      td.colSpan = data.columnas.length; tr.append(td); table.tBodies[0].append(tr);
    }
    page = data.pagina; pages = data.paginas;
    document.getElementById('reporte-total').textContent = `${data.estadisticas.total} afiliados filtrados · ${data.total_filas} ${data.tipo === 'detalle' ? 'registros' : 'grupos'}`;
    document.getElementById('reporte-pagina').textContent = `Página ${page} de ${pages}`;
    document.getElementById('reporte-anterior').disabled = page <= 1;
    document.getElementById('reporte-siguiente').disabled = page >= pages;
    document.getElementById('reporte-nota').textContent = data.nota;
    const card = document.getElementById('reporte-grafico-card');
    card.hidden = data.tipo === 'detalle' || !data.grafico.length;
    if (!card.hidden && window.echarts) {
      chart = chart || window.echarts.init(document.getElementById('reporte-grafico'));
      const pie = data.tipo === 'empadronamiento';
      chart.setOption({tooltip: {trigger: 'item', renderMode: 'richText'},
        grid: {containLabel: true, left: 20, right: 20, bottom: 80},
        xAxis: pie ? undefined : {type: 'category', data: data.grafico.map(r => r.grupo), axisLabel: {rotate: 30, width: 110, overflow: 'truncate'}},
        yAxis: pie ? undefined : {type: 'value', minInterval: 1},
        series: [{type: pie ? 'pie' : data.tipo === 'fecha' ? 'line' : 'bar', radius: pie ? ['40%', '70%'] : undefined,
          data: data.grafico.map(r => ({name: r.grupo, value: r.total})), itemStyle: {color: '#006a67'}}]}, true);
      chart.resize();
    }
  }
  async function responseError(response) {
    if (response.status === 403) return 'No tiene permisos para consultar o descargar estos reportes.';
    if (response.redirected) return 'Su sesión terminó. Vuelva a iniciar sesión.';
    try {
      const data = await response.json();
      Object.entries(data.campos || {}).forEach(([key, errors]) => {
        const target = document.querySelector(`[data-error="${key}"]`);
        if (target) { target.textContent = errors.map(e => e.message).join(' '); target.closest('details').open = true; }
      });
      return data.error || 'No se pudo completar la solicitud.';
    } catch (_) { return 'No se pudo completar la solicitud. Intente nuevamente.'; }
  }
  async function load() {
    if (controller) controller.abort();
    controller = new AbortController();
    const current = controller;
    clearErrors(); busy(true, 'Cargando resultados…');
    try {
      const response = await fetch(`${app.dataset.datos}?${params()}`, {signal: current.signal, headers: {'Accept': 'application/json'}});
      if (!response.ok || response.redirected) throw new Error(await responseError(response));
      render(await response.json());
    } catch (err) { if (err.name !== 'AbortError') showError(err.message); }
    finally { if (controller === current) busy(false); }
  }
  form.addEventListener('submit', event => {
    event.preventDefault(); applied = new URLSearchParams(new FormData(form)); page = 1; sort = ''; load();
  });
  document.getElementById('reporte-limpiar').addEventListener('click', () => {
    form.reset();
    if (window.jQuery && jQuery.fn.select2) jQuery(form).find('select[multiple]').val(null).trigger('change');
    applied = new URLSearchParams(); page = 1; sort = ''; load();
  });
  document.getElementById('reporte-cantidad').addEventListener('change', () => { page = 1; load(); });
  document.getElementById('reporte-anterior').addEventListener('click', () => { if (page > 1) { page--; load(); } });
  document.getElementById('reporte-siguiente').addEventListener('click', () => { if (page < pages) { page++; load(); } });
  function checkColumns(keys) { checkboxes.forEach(el => { el.checked = keys.includes(el.value); }); }
  checkColumns(columns);
  document.querySelectorAll('[data-cols]').forEach(el => el.addEventListener('click', () => {
    checkColumns(el.dataset.cols === 'todas' ? checkboxes.map(c => c.value) : el.dataset.cols === 'basicas' ? base : []);
  }));
  document.getElementById('reporte-aplicar-columnas').addEventListener('click', () => {
    const selected = checkboxes.filter(c => c.checked).map(c => c.value);
    if (!selected.length) { showError('Seleccione al menos una columna.'); return; }
    columns = selected;
    bootstrap.Modal.getInstance(document.getElementById('reporte-columnas')).hide();
    page = 1; load();
  });
  // Descarga con los filtros aplicados, sin incluir el estado todavía sin aplicar del formulario.
  document.querySelectorAll('[data-export]').forEach(button => button.addEventListener('click', async () => {
    clearErrors(); busy(true, 'Generando archivo…');
    try {
      const response = await fetch(`${app.dataset[button.dataset.export]}?${params()}`);
      if (!response.ok || response.redirected) throw new Error(await responseError(response));
      const url = URL.createObjectURL(await response.blob()), link = document.createElement('a');
      link.href = url;
      const disposition = response.headers.get('Content-Disposition') || '';
      link.download = (disposition.match(/filename="([^"]+)"/) || [])[1] || `reporte_afiliados.${button.dataset.export === 'excel' ? 'xlsx' : 'pdf'}`;
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { showError(err.message); }
    finally { busy(false); }
  }));
  if (window.jQuery && jQuery.fn.select2) {
    jQuery(form).find('select[multiple]').each(function () {
      const el = jQuery(this), catalogo = this.dataset.catalogo;
      const config = {width: '100%', placeholder: 'Buscar y seleccionar varios', allowClear: true, closeOnSelect: false};
      let search = '';
      if (catalogo) config.ajax = {url: app.dataset.opciones, delay: 250, dataType: 'json',
        data: p => { search = p.term || ''; return {catalogo, q: search, pagina: p.page || 1, sectores: jQuery('#id_sectores').val() || []}; },
        traditional: true, processResults: data => data};
      el.select2(config);
      const clear = document.createElement('button'); clear.type = 'button'; clear.className = 'btn btn-link btn-sm px-0'; clear.textContent = 'Limpiar selección';
      clear.addEventListener('click', () => el.val(null).trigger('change'));
      el.parent().append(clear);
      const all = document.createElement('button'); all.type = 'button'; all.className = 'btn btn-link btn-sm ms-3 px-0';
      all.textContent = catalogo ? 'Seleccionar coincidencias (máx. 30)' : 'Seleccionar todas';
      all.addEventListener('click', async () => {
        if (!catalogo) { el.find('option').prop('selected', true); el.trigger('change'); return; }
        try {
          const query = new URLSearchParams({catalogo, q: search});
          (jQuery('#id_sectores').val() || []).forEach(id => query.append('sectores', id));
          const response = await fetch(`${app.dataset.opciones}?${query}`);
          if (!response.ok || response.redirected) throw new Error(await responseError(response));
          const result = await response.json();
          result.results.forEach(option => {
            const existing = Array.from(this.options).find(o => o.value === String(option.id));
            if (existing) existing.selected = true;
            else this.add(new Option(option.text, option.id, true, true));
          });
          el.trigger('change');
        } catch (err) { showError(err.message); }
      });
      el.parent().append(all);
    });
    jQuery('#id_sectores').on('change', () => jQuery('#id_comunidades,#id_centros').val(null).trigger('change'));
  }
  window.addEventListener('resize', () => { if (chart) chart.resize(); });
  load();
})();
