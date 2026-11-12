# Reportes Avanzados de Afiliados

Se accede desde **Afiliados → Reportes Avanzados**. No se sustituyen los filtros ni exportadores anteriores y no hay migraciones ni dependencias nuevas.

## Esquema y acceso real

- `Afiliado`: `nombre_completo`, `dpi`, `fecha_nacimiento`, `telefono`, `direccion`, `comunidad`, `centro_votacion`, `lider_vinculado`, `es_lider_comunitario`, `empadronado`, `comisiones`, `cargo_en_comision`, `fecha_creacion`.
- Sector: `afiliado.comunidad.sector`. Centro efectivo: primer centro del sector por nombre e ID, con respaldo en `afiliado.centro_votacion`, siguiendo el criterio del listado existente. Filtros, columnas y resúmenes utilizan ese mismo centro.
- Secretarías: pertenencia mediante las FK `afiliado` de `OrganizacionIntegrante`, `JuventudIntegrante`, `MujeresIntegrante`, `LogisticaIntegrante`, `ComunicacionIntegrante` y `PlanHormigaIntegrante`. No significa que esa secretaría haya creado la afiliación. Una persona puede aparecer en varias; los porcentajes se calculan respecto del total de afiliados únicos y pueden sumar más del 100%. Se incluye «Sin secretaría».
- Participación en estructuras: `EstructuraIntegrante` y sus variantes de Juventud, Mujeres, Logística, Comunicación y Plan Hormiga, mediante DPI original, normalizado o formato `#### ##### ####`. Es una coincidencia de identidad ya utilizada en el proyecto, no una FK nueva. No se equipara con la pertenencia como integrante de secretaría.
- Departamento y municipio: subconsultas al `PadronElectoral` local por DPI normalizado o formateado. No representan necesariamente el domicilio actual; no se deducen del texto de comunidad.
- Empadronamiento: indicador booleano persistido `Afiliado.empadronado`, igual que las estadísticas existentes. No se altera automáticamente por encontrar un registro en el padrón. No existe un tercer estado «sin verificar».
- Acceso a pantalla, AJAX, catálogos y descargas: se reutiliza `_es_usuario_afiliacion` (grupos `Administrador`, `Gestor`, `afiliados`). Incluso un superusuario necesita pertenecer a uno de esos grupos, siguiendo ese control existente. Los decoradores legacy de `permissions.py`, `utils.py` y `access.py` no restringen grupos y no se usan para autorizar este módulo.
- Estos roles ya acceden a datos personales de afiliación; se aplica el mismo acceso a DPI, teléfono y nacimiento en pantalla y descargas. El esquema actual no tiene asignaciones territoriales de usuarios ni un alcance por secretaría para esos roles. No se introducen ni se presumen restricciones inexistentes. Para añadirlas en el futuro, se debe restringir la consulta base y los catálogos antes de aplicar filtros.

**Datos que no existen en Afiliado:** sexo; nombres y apellidos separados; estado activo/inactivo; usuario creador de la afiliación; responsable de afiliación; oficina que originó la afiliación; coordinador responsable directo. Los usuarios de registro de integrantes pertenecen a registros de secretarías, y los coordinadores a estructuras distintas: no se presentan como creador o coordinador del afiliado. No se ofrecen filtros, tarjetas ni columnas ficticias para estos datos. Se busca tanto nombres como apellidos a través de `nombre_completo`.

## Funciones disponibles

Filtros combinables: período de registro (hoy, últimos 7/30 días naturales, mes actual/anterior, año actual o rango abierto/cerrado personalizado); departamento/municipio del padrón; comunidades, sectores y centros múltiples; líderes múltiples; secretarías múltiples; comisiones múltiples; cargo en comisión; es líder; pertenencia a secretaría; participación en estructura; nombre completo; DPI; teléfono; edad mínima/máxima o rangos predefinidos; nacimiento; empadronamiento.

Se aplica AND entre filtros y OR dentro de una selección múltiple. Las comisiones y pertenencias se filtran con `Exists`, evitando duplicados. La edad se calcula por cumpleaños (el 29 de febrero cumple el 1 de marzo en años no bisiestos). Las fechas finales incluyen hasta el último microsegundo local; las agrupaciones diarias respetan `TIME_ZONE`. El territorio elegido filtra el centro efectivo, no un centro directo desplazado por el sector.

Select2 busca y pagina los catálogos (30 opciones por página); permite limpiar o seleccionar hasta 30 coincidencias de búsqueda. Al cambiar sectores se limpian comunidades y centros seleccionados; sus opciones dependen de los sectores. Se admiten hasta 100 valores por filtro.

La tabla utiliza paginación de servidor (10/25/50/100), ordenamiento y búsqueda por campos. Ninguna descarga se limita a la página visible. La configuración de columnas se mantiene al filtrar, paginar y exportar durante la sesión de la pantalla. Aplicar filtros fija la consulta; cambiar campos sin aplicar no cambia la descarga. Al recargar la pantalla se restablece la selección básica.

Reportes: detallado, comunidad, líder, secretaría, centro, fecha de registro (día local), empadronamiento. Agrupados: cantidad, porcentaje, total general y gráfico ECharts (15 principales; por fecha los últimos 15 días). Las tarjetas siempre cuentan afiliados únicos del conjunto filtrado, incluso cuando la tabla muestra agrupaciones.

Excel: `openpyxl` en modo escritura, iteración por lotes de 500, encabezado institucional de `Institucion.nombre`, generación/usuario/filtros/total, fechas tipadas, DPI y teléfono como texto, estilos, autofiltro y encabezados congelados. Todos los textos se fuerzan al tipo cadena de Excel para impedir fórmulas, sin alterar ceros iniciales.

PDF: ReportLab, A4, horizontal con más de 4 columnas, texto escapado y ajustado a celdas, encabezados de tabla repetidos, número de página y total. Máximo 8 columnas; se devuelve una explicación si se excede. Los resúmenes usan sus tres columnas propias. Los textos largos admiten división entre páginas.

Los archivos se generan en temporales privados, se transmiten mediante `FileResponse` y se cierran con la respuesta. No se escriben en `media` ni `static`. Respuestas privadas con `Cache-Control: no-store`. Los resultados son una consulta a datos vivos; cambios concurrentes entre consultas pueden cambiar los totales, como en los otros reportes del proyecto.

## Rutas GET

| Ruta bajo `/afiliados/` | Nombre Django |
| --- | --- |
| `reportes-avanzados/` | `afiliados:reportes_avanzados` |
| `reportes-avanzados/datos/` | `afiliados:reportes_avanzados_datos` |
| `reportes-avanzados/opciones/` | `afiliados:reportes_avanzados_opciones` |
| `reportes-avanzados/excel/` | `afiliados:reportes_avanzados_excel` |
| `reportes-avanzados/pdf/` | `afiliados:reportes_avanzados_pdf` |

Parámetros de tabla/descargas: nombres de campos en `reportes/forms.py`. Repetir nombres para selecciones múltiples, por ejemplo `comunidades=1&comunidades=2`. Columnas: `configuradas=on&columnas=dpi&columnas=nombre`. Sin columnas explícitas se usa la selección básica; una selección explícita vacía se rechaza. Los parámetros desconocidos y las opciones inválidas se rechazan con HTTP 400. Catálogos: `catalogo`, `q`, `pagina`, `sectores` repetible.

## Límites y auditoría

Opciones de Django, todas opcionales:

```python
REPORTES_MAX_EXCEL = 100000
REPORTES_MAX_PDF = 2000
REPORTES_AUDIT_LOG = '/ruta/privada/escribible/reportes/audit.jsonl'
```

Los límites se aplican al total de afiliados filtrados también en resúmenes. Para informes mayores, acotar períodos o territorio; no se truncan silenciosamente los resultados. El PDF se construye en lotes de tabla de 100 y está acotado para hosting compartido. Los resúmenes se agregan en SQL; se conservan en memoria solo las agrupaciones, no todas las personas. Se evita N+1 mediante subconsultas y precarga de relaciones. No se proponen índices sin evidencia de producción.

Cada exportación generada registra fecha, ID del usuario, formato, filtros depurados, columnas y total. Se omiten valores de nombres, DPI, teléfono, nacimiento y líderes en la auditoría; no se registra la URL bruta. El archivo se crea con modo 0600, y el directorio nuevo con 0700. Sin configuración, se usa `aguila-reportes/audit.jsonl` en el directorio temporal del sistema. Para conservar auditoría entre reinicios, configurar una ruta privada persistente, permisos del usuario de Passenger y rotación/retención. Un error al escribir auditoría impide entregar la descarga. No usar una ruta pública ni compartida con otros usuarios.

## Probar en este entorno

```bash
cd /workspace/AguilaApp/aguila_app
source /workspace/aguila-local/env.sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test afiliados_app.tests.test_reportes_avanzados --noinput
python manage.py runserver 127.0.0.1:8000 --noreload
```

Iniciar sesión con una cuenta de uno de los grupos autorizados y navegar al nuevo menú. La base SQLite de desarrollo está fuera del repositorio. No se crean cuentas con contraseñas predeterminadas ni se importan datos reales.

Pruebas automatizadas: sin filtros; final de día en Guatemala; períodos y fechas inválidas; multicomunidades; líder; empadronamiento; edad y cumpleaños bisiesto; combinación de más de cinco filtros; DPI con/sin espacios; territorio del padrón; centro efectivo compartido; secretarías/comisiones sin duplicar; participación en estructuras; todos los grupos; vacíos; orden/paginación; columnas inválidas y seleccionadas; formato Excel; inyección de fórmulas; auditoría depurada; PDF y agrupaciones exportadas; límites; acceso anónimo/no autorizado y grupos autorizados; catálogos dependientes; consulta acotada y exportación de 2,101 filas a Excel y PDF con todas las páginas.

Validación local: las 21 pruebas nuevas pasan. La suite completa ejecutó 91 pruebas: 84 aprobadas, 6 fallos y 1 error, todos los problemas restantes coinciden con la línea base anterior. Chromium verificó paginación, Select2, validaciones, gráficos, configuración de columnas y descargas Excel/PDF; no hubo errores JavaScript y se comprobó el diseño a 1440 y 390 píxeles. `manage.py check` y `makemigrations --check --dry-run` no reportaron problemas ni cambios.

La suite anterior tenía 6 fallos y 1 error en carnet, mensajes de creación de estructuras, modal de afiliación pendiente y un caso que pasa `dpi=None` al cliente de Django. Se mantienen diferenciados de las pruebas nuevas.

## Desplegar en cPanel / MariaDB

1. Respaldar y desplegar los archivos modificados/nuevos sin reemplazar configuración ni base de producción. Este módulo no necesita migraciones nuevas. No cambiar el motor de una base existente para instalarlo: el `settings.py` de este checkout usa PostgreSQL, aunque el destino descrito sea MariaDB/MySQL.
2. Activar el entorno virtual de la aplicación Passenger, usar una versión Python compatible con Django 5.1.4 y las dependencias fijadas existentes. Se reutilizan `openpyxl==3.1.5`, `reportlab==4.4.1`, Select2 y ECharts locales; no hay paquetes nuevos para el módulo.
3. Mantener el backend y credenciales de producción en configuración privada. Si el despliegue ya usa MySQL/MariaDB, conservar su adaptador y `DATABASES`; no copiar el override SQLite de la nube. Django 5.1 requiere MySQL 8+ o MariaDB 10.5+ y su adaptador compatible. No se suministran credenciales.
4. Con `USE_TZ=True`, MySQL/MariaDB necesita tablas de zona horaria cargadas para `TruncDate` en `America/Guatemala`. Pedir al proveedor que las configure si no están disponibles. No desactivar la zona horaria para forzar un resultado.
5. Establecer `REPORTES_AUDIT_LOG` fuera de `public_html`, `media` y `static`, verificar escritura con el usuario de Passenger y configurar rotación. Revisar los límites de filas de acuerdo con memoria y timeout del plan.
6. Ejecutar `python manage.py check` y `python manage.py test afiliados_app.tests.test_reportes_avanzados --noinput` contra una **base de pruebas separada**, con permisos para crear/eliminar esa base. Nunca correr pruebas destructivas sobre la base de producción. Validar especialmente los rangos y agrupaciones por fecha/centro en el motor del destino.
7. Ejecutar `python manage.py collectstatic --noinput` con el destino de estáticos del hosting y reiniciar Passenger mediante el panel. Verificar pantalla, filtros, Excel/PDF y auditoría con datos autorizados.

**Verificación de compatibilidad:** la implementación usa ORM portable (`Exists`, `Subquery`, `Replace`, `Coalesce`, `TruncDate`), sin SQL específico de PostgreSQL. Las pruebas de ejecución se realizaron en SQLite y Chromium Linux. Este entorno no dispone de servidor MariaDB/MySQL ni de acceso a cPanel; no se afirma validación de ejecución en esos destinos. Esa comprobación queda pendiente en una base separada del hosting.

## Archivos

Nuevos: `afiliados_app/reportes/{__init__,forms,queries,exports,views}.py`, `afiliados_app/templates/afiliados/reportes_avanzados.html`, `static/js/reportes_avanzados.js`, `afiliados_app/tests/test_reportes_avanzados.py`, este documento.

Modificados: `afiliados_app/urls.py` (rutas), `afiliados_app/context_processors.py` (visibilidad por permiso), `afiliados_app/templates/afiliados/base.html` (menú). Modelos, migraciones, dependencias y exportadores anteriores permanecen sin cambios.
