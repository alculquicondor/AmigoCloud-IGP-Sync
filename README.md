# Consultas Espaciales sobre Datos Abiertos

Algunas instituciones gubernamentales peruanas publican datos en sus portales
de datos abiertos. Sin embargo, los datos muchas veces se encuentran en tablas
estáticas u otros formatos anticuados que dificultan su procesamiento. En este
tutorial aprenderemos cómo extraer datos de algunos de estos portales para
poder subirlos a una base de datos espacial como [PostGIS](http://postgis.net).
Una vez allí, podremos hacer una gran variedad de consultas clásicas y/o
espaciales. En este ejemplo, elaboraremos un plan de rescate de centros
poblados vulnerables después de un movimiento telúrico.


## Outline

- [Portales de Datos a Utilizar](#portales-de-datos-a-utilizar)
- [Obteniendo Datos de ArcGIS Online](#obteniendo-datos-de-arcgis-online)
- [Sincronizando Datos desde Portales Web](#sincronizando-datos-desde-portales-web)
- [Consultando con SQL](#consutando-con-sql)
- [Consultas Espaciales con PostGIS](#consultas-espaciales-con-postgis)


## Portales de Datos a Utilizar

- [IGP: Instituto Geofísico del Perú](http://www.igp.gob.pe/) del Ministerio
    del Ambiente.
- [IDEP: Infraestructura de Datos Espaciales del Perú](http://www.geoidep.gob.pe/)
    de la Presidencia del Consejo Ministros.

## Obteniendo Datos de ArcGIS Online

- [Portal ArcGIS Online del GEO IDEP](http://mapas.geoidep.gob.pe)

    En este portal se encuentran diversos conjuntos de datos como:
    
    - Límites Políticos
    - Consesiones
    - Red Vial
    - Minería
    - Centros Poblados

### GDAL: GeoSpatial Data Abstraction Layer

[GDAL](http://gdal.org) es una librería que nos permite manipular datos espaciales
(vectoriales y raster) de manera homogénea. Soporta una gran cantidad de
formatos como:

- Raster: JPEG, PNG, Erdas IMG, GeoTIFF, MrSID, MBtiles
- Vector: ESRI Shapefile, FileGDB, GML, GM, GeoJSON

Trae algunos utilitarios como:
 
- `gdalinfo`: listar metadata de rasters
- `gdal_translate`: convertir entre formatos raster o extraer ventanas
- `gdaltransform`: reproyectar rasters
- `ogrinfo`: listar metadata de layers vectoriales y hacer consultas
- `ogr2ogr`: convertir entre formatos y reproyectar.

### Extrayendo datos con ogr2ogr

Podemos usar [`ogr2ogr`](http://www.gdal.org/ogr2ogr.html) para extraer datos
de un layer ArcGIS (en formato GeoJSON) y convertirlos a cualquier otro
(Shapefile en el ejemplo). ArcGIS Online limita las consultas a 1000 registros,
por lo que serán necesarias varias consultas hasta obtener todos los datos.

```sh
ogr2ogr -progress -f "ESRI Shapefile" centros_poblados "http://mapas.geoidep.gob.pe/geoidep/rest/services/Sistema_de_Centros_Poblados/MapServer/2/query?where=FID<1000&outfields=*&f=json" OGRGeoJSON
ogr2ogr -progress -f "ESRI Shapefile" centros_poblados "http://mapas.geoidep.gob.pe/geoidep/rest/services/Sistema_de_Centros_Poblados/MapServer/2/query?where=FID>=1000+AND+FID<2000&outfields=*&f=json" OGRGeoJSON
zip centros_poblados.zip centros_poblados/*
```

Este archivo zip puede ser compartido, subido a software GIS de escritorio o
en la nube.

## Sincronizando datos desde Portales Web

Algunas instituciones publican datos en sus propios portales, mostrándolos en
tablas sin ningún formato en particular. Este es el caso de los datos sobre los
[últimos sismos sentidos](http://www.igp.gob.pe/bdsismos/ultimosSismosSentidos.php)
que reporta el IGP.

En estas situaciones, no hay una estrategia de extracción de datos que funcione
para todas los casos. Entonces, es necesario programar un _parser_ en cada
caso, como [este](celery/utils.py#L13-L43).
Una vez cargados los datos en objetos manipulables (como diccionarios de
Python), se pueden procesar o exportar como se desee. Generar archivos CSV,
JSON o GeoJSON son buenas opciones.

En este caso, hemos realizado una tarea programada que sincronice estos datos
a un proyecto [AmigoCloud](https://www.amigocloud.com). Para ello, hemos usado
la librería [python-amigocloud](https://pypi.python.org/pypi/amigocloud/) y
[Celery](http://www.celeryproject.org), como puede verse
[aquí](celery/tasks.py#L22-L40).
Esta tarea Celery se ejecutará cada 5 minutos para mantener los datos
al día.


## Consultando con SQL

Ahora que tenemos los datos disponibles, podemos cargarlos en una base de datos
espacial como PostGIS. En este tutorial, cargaremos los datos extraídos a un
proyecto de AmigoCloud, el cual nos proporciona una base de datos PostGIS en la
nube, con la ventaja adicional que se encarga de generar visualizaciones.

_NOTA_: También puedes usar `ogr2ogr` para cargar los datos a tu [propia
instancia de PostGIS](http://www.gdal.org/drv_pg.html)

### ¿De qué materiales son las viviendas en centros poblados del Perú?

Cuando carguemos los datos de centros poblados en nuestra base de datos nos
daremos cuenta que trae muchas columnas con información como población,
nivel educativo, servicios disponibles, etc. Nos concentraremos en los
tipos de vivienda según el material de construcción y en particular queremos
saber cuántas de ellas no son de material noble.

Las columna `v_pared_1` contiene el número de viviendas de material noble,
mientras que las columnas `v_pared_2`, `v_pared_3` y posteriores muestran
números para otros materiales. Aquí nos enfrentamos al primer problema: muchos
datos que debieran ser numéricos han sido cargados como cadenas de texto. Pero
eso puede resolverse con _casting_. La consulta queda como sigue:

```sql
SELECT wkb_geometry, amigo_id, arnombre, nomb_dep, nomb_pro, nomb_dist, pob_total, viv_total::INTEGER as viv_total,
  (v_pared_2::INTEGER + v_pared_3::INTEGER + v_pared_4::INTEGER + v_pared_5::INTEGER + v_pared_6::INTEGER + v_pared_8::INTEGER) AS no_noble
FROM centros_poblados
```

También podemos obtener los centros poblados con mayor porcentaje de viviendas
de material no noble:

```sql
SELECT *, (no_noble::DECIMAL / viv_total::DECIMAL) AS no_noble_per
FROM centros_poblados_mas_no_noble
WHERE viv_total > 0
ORDER BY no_noble_per DESC
```

### ¿Cuáles han sido los temblores más fuertes de la última semana?

Tomando ahora los datos de temblores del IGP, averigüemos cuáles han sido
los temblores de magnitud mayor a 5 en la última semana:

```sql
SELECT *
FROM temblores
WHERE magnitude_ml > 5 AND datetime > now() - INTERVAL '2 weeks'
```


## Consultas Espaciales con PostGIS

PostGIS es una extensión para PostgreSQL que le añade índices y funciones para
hacer consultas espaciales. Estas funciones llevan el prefijo `ST_`
(_Spatial Type_).

### Estableciendo Perímetros

Una operación básica es establecer perímetros alrededor de puntos u otros
objetos geométricos como líneas o polígonos. A estos perímetros se les conoce
como _buffers_.

Recordemos que los datos obtenidos de las ubicaciones de los temblores estaban
expresadas en latitud y longitud (a esto se le conoce como proyección geodésica
o [WGS84](https://en.wikipedia.org/wiki/World_Geodetic_System)). El perímetro
tendría que expresarse en las mismas unidades, pero no es más familiar expresar
distancias en el sistema métrico. Lo más sencillo es realizar un _casting_ del
tipo `GEOMETRY` al tipo `GEOGRAPHY`, que usa unidades en metros.

```sql
SELECT amigo_id, magnitude_ml, st_buffer(location::geography, 100000)::geometry
FROM temblores
WHERE magnitude_ml > 5 AND datetime > now() - INTERVAL '1 month'
```

### Efectuando un plan de rescate

Es momento de juntar todas las consultas vistas para realizar un plan de
rescate en el caso de una catástrofe. Obtendremos los centros poblados más
vulnerables alrededor de un radio de 80km de temblores más recientes con
magnitud superior a 5.

```sql
WITH terremotos AS (
    SELECT magnitude_ml, st_buffer(location::geography, 100000)::geometry as area
    FROM temblores
    WHERE magnitude_ml > 5 AND datetime > now() - INTERVAL '1 week'
)
SELECT DISTINCT dataset_79609.*, magnitude_ml
FROM centros_poblados_con_no_noble_per INNER JOIN
  terremotos ON (st_intersects(wkb_geometry, area))
WHERE no_noble_per > .95
ORDER BY no_noble_per DESC
```


## Autor

[Aldo Culquicondor](https://github.com/alculquicondor)
