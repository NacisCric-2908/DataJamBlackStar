# 16 · Prototipo de tablero

Prototipo de visualización (entregable 11.3) construido sobre la capa de
consumo `data/dashboard/` y sobre `data/gold/`. Produce un único HTML
autocontenido que se abre con doble clic: sin servidor, sin `npm`, sin
dependencias de JavaScript y sin llamadas de red salvo la hoja de tipografías
de Google Fonts, que degrada a las fuentes del sistema si no hay conexión.

Ninguna cifra del tablero se calcula aquí. Todo sale de una columna existente
del pipeline; estos scripts solo reempaquetan y redondean.

## Cómo se corre

```bash
python scripts/16_dashboard_prototipo/01_geometria.py   # geometría simplificada
python scripts/16_dashboard_prototipo/02_payload.py     # datos en un solo JSON
python scripts/16_dashboard_prototipo/03_build.py       # ensambla el HTML
```

Salida final: `outputs/dashboard_prototipo_atlas.html`

Solo requiere `pandas` y `pyarrow`, que ya están en `requirements.txt`. No usa
`geopandas`: la geometría se procesa como GeoJSON crudo con la librería
estándar.

## Qué hace cada paso

| Script | Entrada | Salida |
|---|---|---|
| `01_geometria.py` | `data/dashboard/spatial/*.geojson` (5,1 MB) | `data/dashboard/prototipo/geo.json` (89 KB) |
| `02_payload.py` | `data/gold/` + `data/dashboard/` + `geo.json` | `data/dashboard/prototipo/payload.json` (174 KB) |
| `03_build.py` | `src/` + `payload.json` | `outputs/dashboard_prototipo_atlas.html` (216 KB) |

Los fuentes viven separados en `src/` (`head.html` con el CSS, `body.html` con
el marcado, `app.js` con la lógica) porque editar los tres dentro de un archivo
de 216 KB con el JSON incrustado en la mitad es inmanejable. `03_build.py` los
concatena.

## Decisiones que afectan lo que se ve

**Sumapaz queda fuera de la capa de localidades.** Mide 780 km², más del doble
que toda la Bogotá urbana junta, y deforma la proyección hasta dejar la ciudad
como una mancha ilegible. Además no tiene estrato oficial de Planeación y ya
está fuera de los modelos por localidad, que corren con n=19. Se excluye por
coherencia con el análisis, y el tablero lo declara en su pie de página.

**La geometría simplificada es solo para dibujar.** Douglas-Peucker con
tolerancia de 0,00035 grados (unos 39 m), máximo tres anillos por entidad y
coordenadas a 5 decimales. Ningún cálculo del pipeline la usa: las áreas, los
cruces espaciales y las distancias salen de las capas originales de
`data/gold/`.

**Los clústeres Gi\* se leen de `hotspots.csv`, no de `gistar.parquet`.** En el
parquet la columna `idx` es el índice posicional del GeoDataFrame (0, 1, 2...),
no el código de la UPZ. Cruzarlo contra `cod_upz` produce coincidencias falsas
y silenciosas. La exportación a `hotspots.csv` ya resuelve ese índice a
`geography_id`, que sí coincide 112 de 112.

**Se usa `cluster_type` y no la bandera `significant`.** Las dos no siempre
concuerdan: la UPZ 89 (San Isidro - Patios, Chapinero) sale con
`significant=True` y p=0,001 en las seis variables, pero con `statistic` en NaN
y etiqueta `No significativo`. El Gi\* no se pudo calcular ahí. La etiqueta es
el campo conservador.

**El denominador se elige, y ninguna de las dos opciones es neutral.** Desde la
15ª fuente (proyecciones de población del DANE y Planeación, año 2024) cada
medida se puede ver por km² o por habitante. El área castiga a las UPZ
extensas; la población castiga a los parques y las zonas de oficinas, que
reciben gente de día y tienen pocos residentes de noche. Se ve en vivo: al
pasar el arrojo clandestino a per cápita, Zona Industrial (6.944 residentes)
salta del puesto 70 al primero. Por eso el control lleva su advertencia al lado
y el tablero muestra las dos vistas en vez de escoger una.

Las tasas se toman ya calculadas de Gold, que resuelve allí cuál es el
denominador correcto para cada indicador: los delitos cubren toda la localidad
y el aseo domiciliario solo la cabecera urbana. Tres UPZ (El Mochuelo, Parque
Entrenubes y Aeropuerto El Dorado) no tienen población residente y Gold deja
sus tasas en nulo; el mapa las pinta en gris y el tablero lo dice.

Dos indicadores no cambian de denominador porque no son conteos: el estrato
promedio y el índice compuesto. Las emergencias solo traen tasa per cápita a
nivel de UPZ, así que por localidad el mapa se queda en km² y lo explica.

## Cortes parciales que el tablero advierte

Cada serie temporal lleva su propia nota al pie, porque las ventanas no
coinciden y ninguna corrección está aplicada:

- UAECOB (emergencias, incendios, rescates, ambientales): 2020 llega hasta agosto.
- UAECOB emergencias ambientales: 2016 aparece en cero, la categoría no se registraba.
- RBL (residuos recogidos): 2026 tiene 5 de los 12 archivos mensuales.
- DAILoc (homicidios, violencia intrafamiliar): 2026 es año en curso.
