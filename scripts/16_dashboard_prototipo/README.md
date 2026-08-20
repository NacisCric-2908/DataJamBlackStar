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
| `02_payload.py` | `data/gold/` + `data/dashboard/` + `geo.json` | `data/dashboard/prototipo/payload.json` (160 KB) |
| `03_build.py` | `src/` + `payload.json` | `outputs/dashboard_prototipo_atlas.html` (198 KB) |

Los fuentes viven separados en `src/` (`head.html` con el CSS, `body.html` con
el marcado, `app.js` con la lógica) porque editar los tres dentro de un archivo
de 198 KB con el JSON incrustado en la mitad es inmanejable. `03_build.py` los
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

**Las comparaciones son por km², nunca por habitante.** No existe población
oficial por UPZ en las fuentes usadas, así que no se pueden construir tasas por
cada 100.000 habitantes. El tablero lo declara.

## Cortes parciales que el tablero advierte

Cada serie temporal lleva su propia nota al pie, porque las ventanas no
coinciden y ninguna corrección está aplicada:

- UAECOB (emergencias, incendios, rescates, ambientales): 2020 llega hasta agosto.
- UAECOB emergencias ambientales: 2016 aparece en cero, la categoría no se registraba.
- RBL (residuos recogidos): 2026 tiene 5 de los 12 archivos mensuales.
- DAILoc (homicidios, violencia intrafamiliar): 2026 es año en curso.
