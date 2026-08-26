import datetime
import json
from django.test import SimpleTestCase, override_settings
from afiliados_app.views import (
    _agrupar_fechas_por_mes_seguro,
    _construir_series_crecimiento,
)


class _ModeloPrueba(object):
    pass


class _QuerySetFechas(object):
    model = _ModeloPrueba

    def __init__(self, fechas):
        self.fechas = fechas
        self.campo_solicitado = None

    def values_list(self, campo, flat=False):
        self.campo_solicitado = campo
        if not flat:
            raise AssertionError('La consulta debe solicitar únicamente valores planos.')
        return self.fechas


class _FechaConMesInvalido(object):
    year = 2026
    month = 13


class CrecimientoMensualSeguroTests(SimpleTestCase):
    def test_agrupa_vacio_unico_repetidos_meses_y_anios(self):
        casos = [
            ([], []),
            ([datetime.date(2026, 8, 1)], [{'mes': '2026-08', 'total': 1}]),
            (
                [
                    datetime.date(2025, 12, 31),
                    datetime.date(2026, 8, 1),
                    datetime.date(2026, 8, 20),
                    datetime.date(2026, 9, 1),
                ],
                [
                    {'mes': '2025-12', 'total': 1},
                    {'mes': '2026-08', 'total': 2},
                    {'mes': '2026-09', 'total': 1},
                ],
            ),
        ]

        for fechas, esperado in casos:
            queryset = _QuerySetFechas(fechas)
            with self.subTest(fechas=fechas):
                self.assertEqual(_agrupar_fechas_por_mes_seguro(queryset), esperado)
                self.assertEqual(queryset.campo_solicitado, 'fecha_creacion')

    def test_ignora_none_y_valores_anormales_con_warning(self):
        queryset = _QuerySetFechas([
            None,
            '2026-08-01',
            object(),
            _FechaConMesInvalido(),
        ])

        with self.assertLogs('afiliados_app.views', level='WARNING') as logs:
            resultado = _agrupar_fechas_por_mes_seguro(queryset)

        self.assertEqual(resultado, [])
        self.assertEqual(len(logs.output), 4)

    @override_settings(USE_TZ=True, TIME_ZONE='America/Guatemala')
    def test_convierte_datetime_utc_a_zona_local_en_python(self):
        utc = datetime.timezone.utc
        fecha = datetime.datetime(2026, 9, 1, 2, 0, tzinfo=utc)

        resultado = _agrupar_fechas_por_mes_seguro(_QuerySetFechas([fecha]))

        self.assertEqual(resultado, [{'mes': '2026-08', 'total': 1}])

    def test_series_conservan_contrato_y_son_json_valido(self):
        querysets = {
            'coordinadores': _QuerySetFechas([]),
            'lideres': _QuerySetFechas([datetime.date(2026, 8, 1)]),
            'estructuras': _QuerySetFechas([datetime.date(2026, 9, 1)]),
            'reuniones': _QuerySetFechas([
                datetime.date(2026, 8, 2),
                datetime.date(2026, 8, 3),
            ]),
        }

        crecimiento, series = _construir_series_crecimiento(querysets)

        self.assertEqual(series, {
            'labels': ['2026-08', '2026-09'],
            'coordinadores': [0, 0],
            'lideres': [1, 0],
            'estructuras': [0, 1],
            'reuniones': [2, 0],
        })
        self.assertEqual(json.loads(json.dumps(crecimiento)), crecimiento)
        self.assertEqual(json.loads(json.dumps({'crecimiento': series})), {
            'crecimiento': series,
        })

    def test_todos_los_querysets_vacios(self):
        crecimiento, series = _construir_series_crecimiento({
            nombre: _QuerySetFechas([])
            for nombre in ('coordinadores', 'lideres', 'estructuras', 'reuniones')
        })

        self.assertTrue(all(datos == [] for datos in crecimiento.values()))
        self.assertEqual(series, {
            'labels': [],
            'coordinadores': [],
            'lideres': [],
            'estructuras': [],
            'reuniones': [],
        })
