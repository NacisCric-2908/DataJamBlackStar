# Fase 2 — Reporte de auditoría de datos

DataJam Bogotá 2026 · generado a partir de `01_auditoria_datos.py` + verificaciones puntuales. No se corrige nada en esta fase — solo se documenta.

## 1. Capas vectoriales (geometría/CRS)

| Capa | N | Tipo geom. | CRS | Geom. inválidas | Geom. nulas | Fuera de bbox Bogotá | Duplicados |
|---|---|---|---|---|---|---|---|
| IRUPZ (UPZ) | 117 | Polygon/MultiPolygon | EPSG:4686 | 1 (0.9%) | 1 | 1 | 0 |
| IRLoc (localidades) | 21 filas → 20 loc. reales | Polygon | EPSG:4686 | 1 (4.8%) | 1 | 1 | 0 |
| DAILoc (delitos) | 21 filas → 20 loc. reales | Polygon | EPSG:4686 | 1 (4.8%) | 1 | 1 | 0 |
| cestas | 101.162 (69.830 activas) | Point | EPSG:3857 | 0 | 0 | 0 | 0 |
| contenerización | 11.167 | Point | EPSG:3857 | 0 | 0 | 0 | **1** |
| puntos críticos | 478 | Point | EPSG:4326 | 0 | 0 | 0 | 0 |
| macrorutas de barrido | 179 | MultiPolygon | EPSG:4326 | **161 (89.9%)** | 0 | 1 | 0 |
| estaciones bomberos | 17 | Point | EPSG:4686 | 0 | 0 | 0 | 0 |
| cuadrantes policía | 599 | Polygon | EPSG:4686 | 0 | 0 | 0 | 0 |

**Hallazgo consistente:** IRLoc, DAILoc e IRUPZ tienen cada uno exactamente **1 fila con geometría nula/inválida y fuera del bbox de Bogotá** — casi seguro la misma fila índice en las tres (fila de totales o metadato mal formado, no una localidad real). Ver `hallazgos.csv` para el registro exacto antes de descartarlo en Silver.

**Macrorutas de barrido:** 89.9% de geometrías inválidas ya era conocido; se reparan con `make_valid()` sin pérdida de features (confirmado en sesión anterior: 179→179 tras reparar).

**Contenerización:** 1 fila duplicada por atributos + `SERIAL` 100% nulo + `FECHAINSTA` 54.2% nulo — campos poco confiables para trazabilidad temporal de instalación.

## 2. RBL (2017–2026) — auditoría de esquema

**Hallazgo nuevo y crítico, no detectado en la revisión anterior:** a partir de 2023, los archivos XLSX incluyen **dos columnas que colisionan al mismo nombre canónico** en el pipeline actual (`01_build_silver_rbl.py`):

- `arrojo_clandestino_t` recibe tanto *"Recolección de Arrojo Clandestino (Atención críticos clandestinos...)"* como *"Residuos de arrojo clandestino en punto limpio"* — ambas contienen las palabras `arrojo`/`clandestino`, así que el `dict` de mapeo de columnas las funde en una sola clave y **la segunda sobrescribe silenciosamente a la primera** (se pierde la categoría principal, se queda solo con la sub-categoría "punto limpio", mucho más pequeña).
- `total_t` recibe tanto *"Total Residuos Recogidos (t/mes)"* como *"Total Residuos Recogidos (t/mes) + Total residuos de arrojo clandestino en Punto Limpio"* — la segunda (el total combinado) sobrescribe a la primera.

Esto afecta a los archivos 2023, 2024, 2025 y 2026 (confirmado en muestra de abril-2023). El pipeline actual **no falla ni avisa** — produce un número, pero no es el que el nombre de columna promete. Esto es un defecto real de código que **no se corrigió en la sesión anterior** porque no se había auditado el esquema por año con este nivel de detalle.

**Además:** los nombres de columnas cambian de forma no trivial entre años por variaciones de codificación (`Ao/Mes` vs `Año/Mes` vs `Ano/Mes` — pérdida de acentos en distintos lotes de exportación) y de terminología (`Operador y Zona` en 2017 → `ASE y Concesionario` en 2018-2020,2023-2026 → `Area de Servicio Exclusivo y Concesionario` en 2021-2022). El script actual los tolera porque `normalizar_nombre_col` hace *matching* por substring, no por nombre exacto — funciona, pero es frágil.

**2020 usa granularidad anual, no mensual** (`t/año` en vez de `t/mes`, un solo archivo consolidado 2015-2020) — estructuralmente incompatible con 2021-2026 sin transformación adicional. El pipeline actual no lo toca (solo procesa 2021-2026), así que no hay impacto hoy, pero bloquea cualquier extensión del análisis a 2017-2020.

## 3. Incidentes UAECOB (2016–2020) — auditoría de esquema

**Duplicados exactos por archivo completo** (no muestra): 2016 → 58/36.971, 2017 → 68/34.919, 2018 → 4/36.961, 2019 → 3/37.898, 2020 → 0/20.228. Bajo porcentaje (<0.2%) pero no cero — debe documentarse y decidir si se eliminan en Silver.

**Evolución de esquema confirmada con precisión:**
- **Coordenadas (LATITUD/LONGITUD):** solo existen desde 2019 (2016-2018 no las tienen en absoluto — no es que falten valores, la columna no existe).
- **Desagregación de niñez por género:** 2016-2018 solo tienen `MENORES *` (sin diferenciar niñas/niños). Las columnas `MENORES NIÑAS *` / `MENORES NIÑOS *` aparecen recién en 2019. Esto confirma con exactitud el hallazgo de la sesión anterior sobre cobertura parcial del análisis de género/niñez.
- Inconsistencias de tildes en nombres de columna (`ESTACION`/`ESTACIÓN`, `NUMERO SERVICIO`/`NÚMERO SERVICIO`) — cosmético, no afecta al *matching* por substring ya usado en el script.

## 4. Estrato socioeconómico (Esoc.csv, capa `ESoc` del GDB)

**Aclaración importante sobre "duplicados":** `ESoCLote` (código de lote) tiene 2.063.250 filas en códigos duplicados — a primera vista parecía un problema grave. Al cruzar contra `ESoChip` (código de unidad/predio, **0 duplicados en 2.988.992 filas**), se confirma que **no es un error**: un lote catastral (`CLote`) agrupa muchas unidades/predios (`CHIP`) — ej. un lote con un edificio de apartamentos tiene un CHIP por unidad. La tabla está correctamente a nivel de CHIP (unidad), no de lote.

**Sí es un hallazgo real:** de los 66.043 lotes con más de un CHIP, **24.649 (37%)** tienen **estratos inconsistentes entre las unidades del mismo lote** (mismo lote, distintas unidades con distinto estrato oficial — plausible en edificios mixtos o predios reclasificados en momentos distintos). Esto importa si en algún momento se agrega a nivel de lote en vez de CHIP: el "estrato del lote" no está bien definido para ese 37%.

**Estrato = 0** en 957.149 filas (32% del total) — código reservado para "sin estratificar" (rural, institucional, en trámite). El script 04 ya los excluye correctamente al filtrar `estrato.between(1,6)`.

**Limitación de esta fuente (Esoc.csv):** ninguno de sus campos (`ESoCLote`, `ESoChip`) es una llave espacial verificable a UPZ/localidad — ver detalle en el informe final, sección "Limitaciones" (histórico) y sección 4.1 de este documento.

## 4.1. Estrato socioeconómico — 14ª fuente (manzanaestratificacion.json)

**Añadida después de la auditoría original**, cuando se determinó que `Esoc.csv` no tenía llave espacial. Auditada retroactivamente con el mismo criterio (`02_auditoria_estrato_oficial.py`, 11 chequeos, ver `hallazgos.csv`):

- 44.260 manzanas, CRS local `PCS_CarMAGBOG` (proyección cartesiana de Bogotá, sin nombre EPSG estándar, pero con WKT completo — reproyecta bien a EPSG:4326).
- 3/44.260 geometrías inválidas (0.01%) — reparadas con `make_valid()`.
- 0 geometrías nulas, 0 duplicados exactos, 0 `CODIGO_MANZANA` duplicados.
- 5.110 manzanas (11.5%) con `ESTRATO` 0/nulo — correctamente excluidas (uso comercial/industrial/institucional, no residencial).
- **A diferencia de `Esoc.csv`, esta fuente SÍ trae geometría real (polígono) por manzana** → *spatial join* directo (`representative_point` dentro de UPZ/localidad) sin necesidad de ningún cruce de códigos frágil. Resultado: 98.5% de cobertura a UPZ, 100% a Localidad (ver `03_limpieza/08_normalizacion_estrato_oficial.py`).
- Esta fuente **no cubre Sumapaz** (localidad rural) — consistente con que es estratificación urbana por manzana.

## 5. Resumen de severidad

| Severidad | Hallazgo | Fase donde se resuelve |
|---|---|---|
| 🔴 Alto | Colisión de columnas RBL 2023-2026 (arrojo/total se sobrescriben) | 04_normalizacion — requiere *rename* explícito por posición/orden, no por substring genérico |
| 🔴 Alto | *Join* UPZ↔incidentes por texto libre (solo 19% de match, hallado en sesión anterior) | 05_integracion_espacial — se reemplaza por *spatial join* real |
| 🟡 Medio | 89.9% geometrías inválidas en macrorutas | 04_normalizacion — reparar con `make_valid`, documentado |
| 🟡 Medio | 1 fila inválida/nula/fuera-de-bbox en IRUPZ/IRLoc/DAILoc (misma fila, aparente fila de metadatos) | 04_normalizacion — excluir con justificación explícita |
| 🟡 Medio | Duplicados exactos UAECOB (58,68,4,3,0 por año) | 04_normalizacion — deduplicar con conteo documentado |
| 🟡 Medio | 37% de lotes con estrato inconsistente entre sus propias unidades | 06_construccion_variables — usar CHIP como unidad base, nunca lote |
| 🟢 Bajo | 1 duplicado en contenerización; `SERIAL`/`FECHAINSTA` mayormente nulos | 04_normalizacion |
| 🟢 Bajo | Esquema RBL cambia nombres de columna cada año (encoding/terminología) | Ya tolerado por *matching* de substring; documentado para no romperlo |
| ~~🔴 Alto~~ 🟢 Resuelto | `Esoc.csv` sin llave espacial a UPZ/localidad | Resuelto con 14ª fuente (`manzanaestratificacion.json`, sección 4.1) — 3 geometrías inválidas de 44.260 (0.01%), reparadas |

Ver `hallazgos.csv` para el detalle programático de cada chequeo (111 registros, incluye la auditoría retroactiva de la 14ª fuente).
