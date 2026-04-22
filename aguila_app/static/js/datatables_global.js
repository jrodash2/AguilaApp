(function ($) {
  'use strict';

  function getDefaultOptions() {
    return {
      retrieve: true,
      responsive: !!($.fn.dataTable && $.fn.dataTable.Responsive),
      pageLength: 10,
      lengthMenu: [10, 25, 50, 100],
      ordering: true,
      autoWidth: false,
      dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>rt<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
      language: {
        lengthMenu: 'Mostrar _MENU_ registros',
        zeroRecords: 'No se encontraron resultados',
        info: 'Mostrando _START_ a _END_ de _TOTAL_ registros',
        infoEmpty: 'Mostrando 0 a 0 de 0 registros',
        infoFiltered: '(filtrado de _MAX_ registros totales)',
        search: 'Buscar:',
        paginate: {
          first: 'Primero',
          last: 'Último',
          next: 'Siguiente',
          previous: 'Anterior'
        }
      }
    };
  }

  window.initDataTable = function (selector, optionsExtra) {
    if (!$.fn.DataTable) {
      return null;
    }

    var $table = $(selector);
    if (!$table.length) {
      return null;
    }

    if ($.fn.dataTable.isDataTable($table)) {
      return $table.DataTable();
    }

    var options = $.extend(true, {}, getDefaultOptions(), optionsExtra || {});
    return $table.DataTable(options);
  };

  $(function () {
    var selector = '.datatable';
    $(selector).each(function () {
      window.initDataTable(this);
    });
  });
})(jQuery);
