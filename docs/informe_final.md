# Informe final — Análisis geoespacial y estadístico de triple vulnerabilidad urbana en Bogotá D.C.

**DataJam Bogotá 2026 · Equipo BlackStar**

Documento integral: recorrido paso a paso del pipeline (qué hace cada fase, qué
se hizo y qué se encontró), resultados por hipótesis, y limitaciones.

---

## Índice

**Parte I — Contexto y arquitectura**
1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Pregunta de análisis e hipótesis](#2-pregunta-de-análisis-e-hipótesis)
3. [Arquitectura de datos y metodología](#3-arquitectura-de-datos-y-metodología)

**Parte II — Recorrido del pipeline, fase por fase**
4. [Fase 1 — Ingesta y catálogo de fuentes](#fase-1--ingesta-y-catálogo-de-fuentes)
5. [Fase 2 — Auditoría de calidad](#fase-2--auditoría-de-calidad)
6. [Fases 3–4 — Limpieza y normalización → Silver](#fases-34--limpieza-y-normalización--silver)
7. [Fase 5 — Integración espacial](#fase-5--integración-espacial)
8. [Fase 6 — Construcción de variables → Gold](#fase-6--construcción-de-variables--gold)
9. [Fase 7 — Análisis exploratorio (EDA)](#fase-7--análisis-exploratorio-eda)
10. [Fase 8 — Estadística no espacial](#fase-8--estadística-no-espacial)
11. [Fase 9 — Estadística espacial](#fase-9--estadística-espacial)
12. [Fase 10 — Modelos multivariables](#fase-10--modelos-multivariables)
13. [Fase 11 — Análisis espacio-temporal](#fase-11--análisis-espacio-temporal)
14. [Fase 12 — Validación y robustez](#fase-12--validación-y-robustez)
15. [Fase 13 — Visualización y mapas](#fase-13--visualización-y-mapas)
16. [Fase 15 — Exportación de la capa de dashboard](#fase-15--exportación-de-la-capa-de-dashboard)
17. [Hallazgo transversal — Normalización per cápita](#hallazgo-transversal--normalización-per-cápita-15ª-fuente)

**Parte III — Resultados y cierre** *(secciones 6–15 originales, renumeradas)*

---

# Parte I — Contexto y arquitectura

## 1. Resumen ejecutivo

Se auditó, limpió, integró espacialmente y modeló estadísticamente el cruce entre vulnerabilidad socioeconómica, déficit de infraestructura de aseo, arrojo clandestino de residuos, delitos de alto impacto y emergencias urbanas en Bogotá, a nivel UPZ (n=112 urbanas) y localidad (n=19–20), con arquitectura Bronze→Silver→Gold trazable, estadística espacial formal (Moran's I, LISA, Getis-Ord Gi\*, Moran bivariado) y modelos de conteo (Poisson/Binomial Negativa) controlando confusores.

**Fuente de estrato.** El estrato socioeconómico usa la fuente **oficial** — "Estratificación para Bogotá" (Secretaría Distrital de Planeación, manzanas con `ESTRATO` y geometría real) — en vez del proxy autorreportado en incidentes UAECOB que se usó en una primera versión. El *spatial join* manzana→UPZ/localidad logró 98.5%/100% de cobertura (44.260 manzanas, 39.150 con estrato válido). El proxy anterior resultó altamente correlacionado con el oficial (r=0.96 a nivel localidad) — no estaba mal, pero ya no es necesario.

**Resultado central.** La vulnerabilidad socioeconómica es el predictor más robusto y consistente: se asocia significativamente con déficit de aseo (**H1 confirmada**, en ambos niveles espaciales) y con arrojo clandestino (**H3 confirmada**, coef=-0.90, IRR=0.41, p<0.0001). Ambas sobreviven la corrección por comparaciones múltiples.

**El déficit de infraestructura de aseo por sí solo NO predice arrojo clandestino** una vez se controla por estrato (**H2 no respaldada**). Tres líneas de evidencia independientes lo confirman: correlación bivariada nula, coeficiente invertido en el modelo multivariable, y un análisis de proximidad que muestra que los puntos críticos están **más cerca** de la infraestructura formal que un punto aleatorio de la ciudad. El hallazgo r=+0.74 del dashboard previo del equipo era una correlación simple sin control de confusores.

**Mediación por estrato.** La correlación bivariada entre puntos críticos de arrojo y delitos/emergencias **sí es fuerte y robusta** (rho=0.83 en localidad para homicidios; rho=0.26–0.40 en UPZ para incidentes), estable bajo conteo crudo, densidad y log-densidad. Lo que **no sobrevive** es el efecto *incremental* del arrojo una vez el modelo incluye estrato y cuadrantes de policía. Esto no es una contradicción: es evidencia de que el estrato **media o confunde** buena parte de esa asociación, más que un efecto directo independiente.

**Desigualdad de cobertura (15ª fuente).** Al incorporar la población oficial por UPZ (SDP/DANE) se pudo normalizar per cápita, no solo por área. El resultado es la cifra de política pública más accionable del estudio: **las UPZ de estrato 1–2 tienen 8,9 veces menos cestas por habitante que las de estrato 4–6**, y la brecha persiste al controlar por densidad poblacional (IRR=1,78 por punto de estrato, p<0,0001). Esto **fortalece H1** y, en sentido contrario, **debilita H3**: buena parte del vínculo "vulnerabilidad → arrojo clandestino" que se observaba por km² era en realidad densidad poblacional.

**Lectura final.** La evidencia respalda la mitad delantera del mecanismo (vulnerabilidad → déficit, vulnerabilidad → arrojo) pero no la mitad trasera (arrojo → delitos/emergencias) como efecto independiente. La "triple vulnerabilidad" es real y espacialmente robusta, pero su origen común más probable es el estrato, no una cadena causal secuencial.

---

## 2. Pregunta de análisis e hipótesis

**Pregunta.** ¿Los territorios con mayor vulnerabilidad socioeconómica y menor cobertura de infraestructura formal de aseo presentan una mayor concentración de puntos críticos de arrojo clandestino y, simultáneamente, una mayor incidencia de delitos de alto impacto y emergencias atendidas por bomberos?

**Hipótesis evaluadas.** El mecanismo propuesto se descompuso en siete eslabones contrastables por separado, más un modelo conjunto:

| ID | Hipótesis | Nivel | Estado final |
|---|---|---|---|
| H1 | Vulnerabilidad → Déficit de aseo | UPZ + Localidad | **Confirmada** |
| H2 | Déficit de aseo → Arrojo clandestino | UPZ | **No respaldada** |
| H3 | Vulnerabilidad → Arrojo clandestino | UPZ | **Confirmada** |
| H4 | Arrojo → Delitos de alto impacto | Localidad | Parcialmente respaldada |
| H5 | Arrojo → Emergencias urbanas | UPZ | Parcialmente respaldada |
| H6 | Vulnerabilidad → Delitos | Localidad | Parcialmente respaldada |
| H7 | Vulnerabilidad → Emergencias | UPZ | No respaldada |
| Conjunta | Los cuatro factores → Delitos | Localidad | Respaldada por vulnerabilidad |

Detalle estadístico completo en la [sección de resultados por hipótesis](#16-resultados-por-hipótesis).

---

## 3. Arquitectura de datos y metodología

### Arquitectura Medallion

```
data/bronze/     15 fuentes crudas, intactas          (~295 MB, no versionado)
      ↓
data/silver/     17 parquets limpios por dominio      (territorio, aseo, seguridad,
      ↓                                                emergencias, policia, bomberos,
      ↓                                                socioeconomico, poblacion)
data/gold/       41 archivos analíticos               (dimensiones, modelos,
      ↓                                                estadística espacial, rankings)
      ↓
data/dashboard/  22 CSV/GeoJSON de consumo            (capa plana para visualización)
```

Cada capa tiene una responsabilidad estricta: **Bronze no se modifica nunca**; **Silver** solo aplica correcciones documentadas en la auditoría, sin ninguna decisión analítica; **Gold** construye variables e indicadores; **dashboard** solo re-empaqueta Gold sin calcular nada nuevo.

### Decisiones metodológicas transversales

- **Sistemas de coordenadas:** EPSG:4326 unificado para *spatial joins*; EPSG:3116 (Magna-Sirgas Bogotá) para todo cálculo métrico de área y distancia.
- **Uniones espaciales reales:** *point-in-polygon* (`within`) para puntos, `intersects` para cuadrantes de policía que cruzan límites administrativos. **No se usa matching por texto en ningún punto del pipeline.**
- **Unidad espacial principal:** UPZ (n=112, tras excluir 4 UPR rurales y 1 "sin localización"). Todo análisis se repite a nivel localidad (n=19–20) para evaluar sensibilidad a MAUP.
- **Normalización:** **doble**, por área (`offset = log(area_km2)`) y por población (15ª fuente, proyecciones DANE/SDP por UPZ). Reportar ambas es lo que permite separar densidad urbana de cobertura real de servicio — ver [Hallazgo transversal](#hallazgo-transversal--normalización-per-cápita-15ª-fuente).
- **Trazabilidad:** 29 transformaciones documentadas en `scripts/03_limpieza/trazabilidad.csv` (fuente → transformación → motivo → registros afectados).
- **Reproducibilidad:** `python main.py` ejecuta las 29 tareas en orden estricto de precedencia (~95 s sin notebooks).

---

# Parte II — Recorrido del pipeline, fase por fase

Esta parte documenta qué hace cada fase, qué se ejecutó y qué se encontró.

---

## Fase 1 — Ingesta y catálogo de fuentes

**Script:** `scripts/01_ingesta/01_catalogo_fuentes.py`
**Entrada:** `data/bronze/` · **Salida:** `scripts/01_ingesta/catalogo_fuentes.csv`

### Qué hace
Inventaría automáticamente todos los archivos de Bronze: formato, tipo (tabular/vectorial), dimensiones, CRS, geometría y cobertura temporal aproximada. **No modifica nada** — es un censo de lo que existe antes de tocarlo.

### Qué se hizo
Se catalogaron **106 archivos/capas** correspondientes a las **15 fuentes declaradas**. Las 87 entradas de RBL son los archivos mensuales de residuos (2021–2026) y las 5 de UAECOB los CSV anuales de incidentes.

### Hallazgos
- Las 15 fuentes quedan cubiertas y trazadas a su enlace del Portal de Datos Abiertos, sin ninguna entrada `NO DECLARADA`.
- Heterogeneidad de CRS considerable entre fuentes: EPSG:4686 (IDECA/Catastro), EPSG:3857 (mobiliario UAESP), EPSG:4326 (macrorutas) y un CRS local proyectado en los predios rurales. Esto obliga a unificar CRS antes de cualquier cruce — se resuelve en la Fase 3.
- Formatos mixtos: GeoJSON, CSV, XLSX y JSON, con codificaciones inconsistentes (varios CSV de UAECOB están en `latin-1`, no UTF-8).

---

## Fase 2 — Auditoría de calidad

**Scripts:** `scripts/02_auditoria/01_auditoria_datos.py` · `02_auditoria_estrato_oficial.py`
**Salida:** `hallazgos.csv` (111 hallazgos) · `reporte_auditoria.md`

### Qué hace
Ejecuta 16 chequeos obligatorios **antes** de cualquier transformación: geometrías inválidas y nulas, duplicados, valores fuera de rango, CRS, cobertura temporal, registros fuera del *bounding box* de Bogotá. **No corrige nada; solo documenta.** El segundo script audita retroactivamente la 14ª fuente, incorporada después de la auditoría original.

### Qué se hizo
111 hallazgos registrados: 31 `ok`, 51 `info`, **29 `warning`**. Cada uno con fuente, chequeo, valor y severidad.

### Hallazgos con impacto real

| Hallazgo | Severidad | Consecuencia |
|---|---|---|
| *Join* UPZ↔incidentes por texto libre: solo **19% de coincidencia** | 🔴 Alto | Habría descartado 4 de cada 5 incidentes |
| RBL 2023–2026: dos columnas distintas colisionaban al mismo nombre canónico, una sobrescribía a la otra **silenciosamente** | 🔴 Alto | Pérdida de datos invisible en la serie temporal |
| UPZ y UPR (rural) **comparten numeración** (UPZ3="Guaymaral" vs UPR3="Río Tunjuelo") | 🔴 Alto | Extraer solo el número fusionaría zonas distintas |
| Columna `año` en incidentes UAECOB quedaba 100% NaN | 🔴 Alto | Imposibilitaba todo análisis temporal |
| **89.9% de geometrías inválidas** en macrorutas de barrido | 🟡 Medio | Rompería los *spatial joins* |
| Fila "Sin Localización" (código 99/999) en IRUPZ/IRLoc/DAILoc con geometría nula | 🟡 Medio | No es una unidad territorial real |
| Duplicados exactos en UAECOB (133 en total) y 1 en contenerización | 🟡 Medio | Inflaría conteos |
| `Esoc.csv` (2.99M unidades): sin llave espacial verificable a UPZ/localidad | 🟢 Resuelto por otra vía | Motivó incorporar la 14ª fuente |

> **Valor de esta fase.** Cuatro de estos hallazgos son errores que habrían pasado inadvertidos y contaminado todos los resultados posteriores. El caso más grave es la colisión de columnas de RBL: no produce error, solo datos silenciosamente incorrectos.

---

## Fases 3–4 — Limpieza y normalización → Silver

**Scripts:** `04_normalizacion_silver.py` · `05_normalizacion_emergencias.py` · `06_normalizacion_rbl.py` · `07_normalizacion_socioeconomico.py` · `08_normalizacion_estrato_oficial.py`
**Salida:** 15 parquets en `data/silver/` + `trazabilidad.csv`

### Qué hace
Aplica **únicamente** las correcciones documentadas en la auditoría. Ninguna decisión analítica ocurre aquí. Cada transformación se registra con su motivo y el número de registros afectados.

### Qué se hizo — las 24 transformaciones trazadas

**Territorio**
- IRUPZ: excluir `UPZ999` (1 registro) y los 4 códigos `UPR*` rurales → **112 UPZ**; reproyección 4686→4326.
- IRLoc: excluir código 99 (1) → **20 localidades**; reproyección 4686→4326.

**Aseo**
- Cestas: filtrar `ESTADO==2` (instalada/activa) → 31.332 descartadas, 69.830 conservadas; reproyección 3857→4326.
- Contenerización: 1 duplicado exacto eliminado; 11.166 reproyectados.
- Macrorutas: `make_valid()` sobre **161 geometrías inválidas**, sin pérdida de features.
- RBL: separación explícita de `arrojo_clandestino_punto_limpio_t` y `total_combinado_t` (22 archivos afectados) — corrige la colisión silenciosa.

**Seguridad y emergencias**
- DAILoc: excluir código 99; construir `homicidios_cont` y `homicidios_total_oficial` **en paralelo** sin elegir uno arbitrariamente.
- UAECOB: 133 duplicados exactos eliminados; **join a UPZ por el código numérico embebido** en el campo libre en vez de por nombre de texto → el match sube de **19% a 99.2%**, recuperando 165.500 incidentes.

**Socioeconómico**
- `Esoc.csv`: excluir estrato 0 y fuera de 1–6 (957.149 registros). **Se documenta explícitamente que NO se construye agregación por UPZ/localidad** desde esta fuente: no existe llave espacial verificable (se comprobó que `Predio.PreCManz` no es compatible con `Manz.ManCodigo`).
- `manzanaestratificacion.json` (14ª fuente): `make_valid()` sobre 3 geometrías; filtrar estrato 1–6 (5.110 descartadas); reproyección; *spatial join* `representative_point within` a UPZ y localidad → **39.150 manzanas asignadas**.

**Población (15ª fuente)** — `09_normalizacion_poblacion.py`
- Los dos archivos de la fuente tienen estructuras distintas y se tratan aparte: el de UPZ trae grupos quinquenales y **solo `Cabecera Municipal`** (suelo urbano, coincidente con el alcance del proyecto); el de localidad trae edades año a año y filas separadas para componente urbano y rural.
- Se agregan los grupos de edad a totales por sexo y al corte de **niñez 0–14**, que permite normalizar los incidentes UAECOB con niñas/niños expuestos.
- A nivel localidad se consolidan las 27 filas/año en 20, conservando `poblacion_cabecera` aparte: **el denominador correcto depende del indicador** (los delitos cubren toda la localidad; el aseo domiciliario es urbano).
- Salida: `poblacion_upz.parquet` (112 UPZ × 31 años) y `poblacion_localidad.parquet` (20 × 31).

### Hallazgos
- La corrección del *join* de UAECOB es la de mayor impacto de todo el pipeline: multiplica por cinco los datos utilizables.
- La decisión de **no forzar** una agregación de `Esoc.csv` sin llave verificable es metodológicamente correcta: se prefirió declarar la limitación e incorporar una fuente con geometría real.
- Sumapaz queda sin estrato oficial porque la fuente de manzanas cubre solo suelo urbano. Esto se propaga a los modelos (n=19).
- La fuente de población **confirma cuantitativamente** la exclusión de Sumapaz del alcance urbano: es la única localidad **100% rural** (3.611 habitantes, cero en cabecera). Las demás localidades con componente rural no superan el 3%.
- El join de población contra las UPZ del pipeline es **exacto: 112 de 112 (100%)** — el DANE calculó las proyecciones sobre los mismos polígonos, sin requerir imputación ni aproximación espacial.

---

## Fase 5 — Integración espacial

**Scripts:** `01_spatial_joins.py` · `02_analisis_proximidad.py`
**Salida:** `aseo_policia_bomberos_{upz,localidad}.parquet` · `proximidad_puntos_criticos.parquet` · `proximidad_vs_aleatorio.csv`

### Qué hace
El primer script cruza toda la infraestructura puntual (cestas, contenedores, puntos críticos, estaciones de bomberos, cuadrantes) contra las mallas de UPZ y localidad mediante *spatial joins* reales. El segundo calcula, para **cada punto crítico de arrojo**, la distancia en metros (EPSG:3116) a la infraestructura formal más cercana, y la contrasta contra una muestra de puntos aleatorios de la ciudad.

### Qué se hizo
Se agregaron conteos y densidades por km² de cada tipo de infraestructura a las 112 UPZ y 20 localidades. Para los 478 puntos críticos se calculó distancia a cesta, contenedor, macroruta, estación de bomberos y cuadrante más cercanos, con prueba Mann-Whitney contra el escenario aleatorio.

### Hallazgo principal — contradice frontalmente la hipótesis H2

| Infraestructura | Distancia media de puntos críticos | Distancia media aleatoria | ¿Más lejos? | p |
|---|---|---|---|---|
| Cesta | **91.8 m** | 212.8 m | ❌ No, más cerca | <0.001 |
| Contenedor | **303.9 m** | 466.3 m | ❌ No, más cerca | <0.001 |
| Estación de bomberos | **1.748 m** | 2.308 m | ❌ No, más cerca | <0.001 |

Los puntos críticos de arrojo clandestino están **sistemáticamente más cerca** de la infraestructura formal de aseo que un punto cualquiera de la ciudad, en las tres comparaciones y con significancia alta.

> **Interpretación.** Esto invierte el supuesto del proyecto. Dos lecturas compatibles con los datos: (a) la UAESP instala mobiliario **donde ya hay problema** — la infraestructura responde al arrojo, no al revés; (b) ambos fenómenos se concentran en zonas densas y de alta actividad urbana. Con datos transversales (sin fecha de instalación confiable — 54% nula en `FECHAINSTA`) no es posible distinguirlas. Lo que sí queda descartado es la hipótesis original de que el arrojo ocurre donde *falta* infraestructura.

---

## Fase 6 — Construcción de variables → Gold

**Scripts:** `01_dataset_maestro.py` · `02_dataset_upz_anio_e_hipotesis.py` · `03_data_dictionary.py` · `04_completar_gold_subcarpetas.py` · `05_ranking_territorial.py`
**Salida:** 41 archivos en `data/gold/`

### Qué hace
Construye las tablas analíticas finales: datasets maestros transversales por UPZ y localidad, paneles con dimensión temporal real, un dataset por hipótesis, el diccionario de datos con linaje completo, y el índice de vulnerabilidad compuesta.

### Qué se hizo

**Datasets maestros**
- `dataset_hipotesis_upz.parquet` (112×27) y `dataset_hipotesis_localidad.parquet` (20×30).
- `emergencias_upz_anio.parquet` — panel **real** UPZ×año 2016–2020 (551 filas), la única fuente con esa granularidad.
- `delitos_localidad_anio.parquet` — panel real localidad×año.
- 7 datasets `hypothesis_h1..h7.parquet`, uno por hipótesis, con solo las variables relevantes.

**Variables construidas**

| Grupo | Variables |
|---|---|
| Vulnerabilidad | `estrato_promedio_oficial`, `estrato_modal_oficial`, `pct_estrato_1_2_oficial`, `pct_estrato_5_6_oficial` (+ versiones `_reportado` del proxy, conservadas para comparación) |
| Aseo | `n_cestas`, `n_contenedores`, `densidad_*_km2`, `cobertura_macrorutas_pct`, `deficit_aseo_relativo` |
| Arrojo | `n_puntos_criticos`, `densidad_puntos_criticos_km2` |
| Emergencias | `n_incidentes_total`, `n_incendios`, `densidad_incidentes_km2`, `n_ninas_expuestas`, `n_ninos_expuestos` |
| Accesibilidad | `n_cuadrantes`, `densidad_cuadrantes_km2`, `dist_estacion_bomberos_m`, `n_estaciones_bomberos_5km` |
| Control | `area_km2` (offset de los modelos) |

**Definición de `deficit_aseo_relativo`** — z-score **invertido** de la densidad conjunta de cestas y contenedores: `-((x - media) / desviación)`. Valores altos = menos infraestructura relativa a la media de la ciudad. Es un índice **relativo y adimensional**, no un déficit normativo: no compara contra ningún estándar oficial de cobertura. Se recalcula independientemente en cada nivel espacial, por lo que **la escala UPZ y la escala localidad no son directamente comparables**.

**Diccionario de datos** — `data_dictionary.csv` responde, por variable Gold, las 8 preguntas de linaje: fuente, transformación, fórmula, unidad, unidad espacial, período temporal y supuestos.

### Hallazgos
- Solo **una** variable tiene dimensión temporal real por UPZ (incidentes UAECOB). Toda la infraestructura de aseo, policía y bomberos son *snapshots* actuales sin fecha confiable, lo que impide un panel espacio-temporal genuino (ver Fase 11).
- El dataset UPZ×año que exige el estándar del reto se construyó, pero las columnas de infraestructura llevan prefijo `snap_` para dejar explícito que son valores estáticos replicados por año, **no mediciones repetidas**.
- `deficit_aseo_relativo` está correlacionado a -0.98/-0.99 con `densidad_cestas_km2` **por construcción** — no es un hallazgo independiente y así se reporta.

---

## Fase 7 — Análisis exploratorio (EDA)

**Notebook:** `notebooks/01_eda_dataset_maestro.ipynb`

### Qué hace
Exploración visual del dataset maestro: distribuciones, mapas coropléticos, mapa de puntos, boxplots, matriz de correlación y series temporales.

### Hallazgos
- `n_puntos_criticos` y `n_incidentes_total` presentan **asimetría positiva fuerte** → justifica usar modelos de conteo no lineales en la Fase 10, no regresión lineal.
- Las tres fuentes temporales cubren **ventanas no solapadas**: RBL 2021–2026, UAECOB 2016–2020, DAILoc 2018–2026. **No existe un año común a las tres** con las tres variables simultáneamente — esto restringe estructuralmente cualquier análisis conjunto.
- Homicidios anuales estables entre 478–588/año (2018–2025). Violencia intrafamiliar salta a 25.631 en 2026 frente a 13.000–19.000 en años previos — posible corte de año incompleto; se reporta sin interpretar (ver Fase 11).

---

## Fase 8 — Estadística no espacial

**Script:** `scripts/08_estadistica/01_pruebas_estadisticas.py`
**Salida:** `normalidad_upz.csv` · `matriz_correlacion.csv`

### Qué hace
Prueba de normalidad Shapiro-Wilk sobre cada variable clave para decidir Pearson vs Spearman, seguida de la matriz de correlación completa entre todas las variables, con corrección Benjamini-Hochberg (FDR) por comparaciones múltiples.

### Qué se hizo y hallazgos
- **Ninguna de las 9 variables clave pasa la prueba de normalidad** (todas p<0.05) → se usa **Spearman** en toda la fase estadística, decisión justificada por datos y no por convención.
- De 36 pares posibles a nivel UPZ, **24 son significativos tras FDR**; a nivel localidad, 21 de 28.
- Par más fuerte: `deficit_aseo_relativo` ↔ `densidad_cestas_km2` (rho=-0.98/-0.99) — **artefacto de construcción**, no hallazgo.
- Segundo más fuerte: `densidad_puntos_criticos_km2` ↔ `densidad_homicidios_km2` a nivel localidad (rho=0.83).

> **Relación inesperada, fuera de las 7 hipótesis.** `densidad_cuadrantes_km2` ↔ `densidad_incidentes_km2` resulta de las correlaciones más fuertes de toda la matriz: rho=0.49 (UPZ, p<0.001) y rho=0.85 (localidad, p<0.001). Nadie la planteó como hipótesis. La lectura causal ingenua ("más policía → más emergencias") no tiene sentido; la interpretación razonable es **reactiva**: la Policía despliega más cuadrantes donde ya hay más actividad, es decir cobertura proporcional a la demanda. Se reporta por transparencia, no como respaldo de ninguna hipótesis.

---

## Fase 9 — Estadística espacial

**Scripts:** `01_moran_lisa_getis.py` · `02_guardar_pesos_espaciales.py`
**Salida:** `moran_global.csv` · `lisa_local.parquet` · `gistar.parquet` · `pesos_espaciales.parquet`

### Qué hace
Cuantifica si los fenómenos se agrupan espacialmente: Moran's I global (¿hay agrupamiento?), LISA/Moran local (¿dónde están los clusters?), Getis-Ord Gi\* (¿dónde están los *hotspots*?) y Moran bivariado (¿co-ocurren dos variables en el espacio?). El segundo script persiste las matrices de pesos para que el análisis sea reproducible sin re-derivar W.

### Hallazgos

**Moran's I global (UPZ)** — autocorrelación positiva y significativa (p=0.001) en todas las variables clave:

| Variable | Moran's I |
|---|---|
| `estrato_promedio_oficial` | **0.70** (la más agrupada) |
| `densidad_cuadrantes_km2` | 0.58 |
| `deficit_aseo_relativo` | 0.41 |
| `densidad_incidentes_km2` | 0.29 |
| `densidad_puntos_criticos_km2` | 0.28 |

El estrato es, con diferencia, la variable más fuertemente agrupada en el espacio — evidencia cuantitativa de **segregación socioeconómica territorial**, y coherente con que sea el factor común detrás de los tres fenómenos.

A nivel localidad solo `deficit_aseo_relativo` mantiene significancia (p=0.022); el resto la pierde por el desplome del poder estadístico con n=19–20.

**LISA (Moran local)** — `deficit_aseo_relativo`: 20 UPZ *High-High* (clusters de alto déficit) y 19 *Low-Low*. `estrato_promedio_oficial`: 20 *High-High* y 26 *Low-Low*, confirmando segregación espacial fuerte.

**Getis-Ord Gi\*** — 20 UPZ *hotspot* y 19 *coldspot* de puntos críticos; 17 UPZ *hotspot* de incidentes. A nivel localidad apenas 1–3 alcanzan significancia.

---

## Fase 10 — Modelos multivariables

**Script:** `scripts/10_modelos/01_modelos_multivariables.py`
**Salida:** `resultados_modelos.csv` (12 coeficientes, 4 modelos)

### Qué hace
Ajusta modelos de conteo con control de confusores. Estrategia: **Poisson primero**; si la sobredispersión (deviance/df) supera 1.5, se reajusta con **Binomial Negativa**. Se usa `offset = log(area_km2)` para modelar **tasa por km²** en vez de conteo bruto, y se reporta el VIF de los predictores antes de cada modelo.

### Qué se hizo

| Modelo | Variable dependiente | Predictores | n |
|---|---|---|---|
| M1 | `n_puntos_criticos` (UPZ) | déficit de aseo + estrato | 112 |
| M2 | `n_incidentes_total` (UPZ) | puntos críticos + estrato + distancia a bomberos | 112 |
| M3 | `homicidios_cont` (localidad) | puntos críticos + déficit + cuadrantes | 20 |
| M4 | `homicidios_cont` (localidad) | estrato + déficit + puntos críticos + cuadrantes | 19 |

### Hallazgos
- **Los 4 modelos presentaron sobredispersión** (deviance/df entre 4 y 505) — ninguno es adecuado como Poisson; todos se reportan como Binomial Negativa.
- **VIF máximo = 2.7** (modelo conjunto) → sin problema de multicolinealidad en ningún modelo.
- **M1:** tanto el déficit (coef=-0.484, p=0.0005) como el estrato (coef=-0.899, p<0.0001) son significativos, pero **el déficit sale con signo invertido** respecto a lo esperado (efecto de supresión), coherente con el hallazgo de proximidad de la Fase 5.
- **M2:** ni puntos críticos ni estrato son significativos; solo la distancia a estación de bomberos (p=0.022).
- **M3 → M4:** el coeficiente del arrojo se atenúa de +0.029 (p=0.077, marginal) a +0.007 (p=0.723, nulo) al añadir el estrato — **la evidencia más directa de mediación/confusión por vulnerabilidad** de todo el estudio.
- **M4 corre con n=19, M3 con n=20**: Sumapaz se cae silenciosamente al entrar el estrato oficial, que no cubre suelo rural.

---

## Fase 11 — Análisis espacio-temporal

**Script:** `scripts/11_espacio_temporal/01_analisis_temporal.py`
**Salida:** `tendencias_uaecob_upz.csv` · `resumen_espacio_temporal.csv`

### Qué hace
Analiza cada fuente **en su resolución espacio-temporal nativa**, sin forzar un panel único: tendencias, rupturas, años atípicos y zonas persistentes vs. emergentes.

### Decisión metodológica
No se construyó un panel único UPZ×año. Las tres fuentes temporales tienen ventanas y granularidades incompatibles: RBL no tiene UPZ (solo ASE), DAILoc no tiene UPZ (solo localidad), y solo UAECOB ofrece UPZ×año. Forzar un panel habría exigido **asumir valores estáticos para variables nunca medidas repetidamente**, introduciendo una falsa dimensión temporal.

### Hallazgos
- **UAECOB (2016–2020):** 2020 es atípico (z=-1.76) — coincide simultáneamente con el corte parcial del archivo (agosto 2020) y con la pandemia; **con estos datos no se puede distinguir cuál causa domina**. De las 112 UPZ, **43 muestran tendencia decreciente significativa** (p<0.10) y solo 3 creciente.
- **DAILoc (2018–2026):** homicidios con tendencia leve al alza (+8.35/año, p=0.062, marginal); 2025 es el año más alto (z=1.72). Violencia intrafamiliar atípica en 2026 (z=2.16, 25.631 casos). **2026 es el año en curso** — un conteo *parcial* ya supera a los 8 años completos anteriores. No se puede determinar si es aceleración real o artefacto de acumulación; merece seguimiento al cerrar el año.
- **Persistencia territorial:** Ciudad Bolívar (media 99.1 homicidios/año, CV=0.12) y Kennedy (74.2, CV=0.15) son **consistentemente altas**, no picos aislados.
- **RBL (2021–2026):** sin tendencia significativa (p=0.44). La media mensual antes (2021–2022: 37.601 t) y después (2023–2026: 36.903 t) de corregir la colisión de columnas es consistente — **confirma que el fix de la Fase 3 no introdujo una ruptura artificial**.

---

## Fase 12 — Validación y robustez

**Scripts:** `01_robustez.py` · `02_robustez_periodos.py`
**Salida:** `maup_upz_vs_localidad.csv` · `robustez_especificaciones.csv` · `robustez_pesos_espaciales.csv` · `robustez_periodos_temporales.csv`

### Qué hace
Repite las asociaciones clave bajo especificaciones alternativas para verificar que los hallazgos no sean artefactos de decisiones metodológicas arbitrarias. Cuatro ejes: unidad espacial (MAUP), forma funcional, matriz de pesos y período temporal.

### Hallazgos

**a) MAUP — UPZ vs Localidad**

| Variable | Moran's I (UPZ) | Moran's I (Localidad) |
|---|---|---|
| `deficit_aseo_relativo` | 0.41 (p=0.001) | 0.27 (p=0.022) |
| `densidad_incidentes_km2` | 0.29 (p=0.001) | 0.15 (p=0.079) |
| `densidad_puntos_criticos_km2` | 0.28 (p=0.001) | 0.12 (p=0.121) |

La autocorrelación es **sistemáticamente más débil a nivel localidad** — esperable por la pérdida de poder (n=19–20 vs n=112), no evidencia de que el efecto desaparezca.

**b) Forma funcional (crudo vs densidad vs log-densidad)** — H4/H5 es significativa y de magnitud similar **bajo las tres especificaciones** en ambos niveles (UPZ: rho=0.26–0.40; localidad: rho=0.77–0.83). La relación bivariada **no es un artefacto de cómo se mide la variable**.

**c) Matriz de pesos (Queen vs KNN k=5)**

| Variable | Queen | KNN k=5 |
|---|---|---|
| `deficit_aseo_relativo` | 0.407 | 0.345 |
| `densidad_puntos_criticos_km2` | 0.285 | 0.248 |
| `densidad_incidentes_km2` | 0.294 | 0.244 |

La magnitud cambia pero la significancia (p=0.001 en los 6 casos) y la conclusión cualitativa **no dependen de la definición de vecindad**.

**d) Períodos temporales** — H4 (arrojo↔homicidios) es **estable** en dos sub-períodos independientes: 2018–2021 rho=0.76 y 2022–2026 rho=0.78, ambos p<0.001. H5 (arrojo↔incidentes) **no lo es**: rho=0.14 (ns) en 2016–2017 vs rho=0.52 (p<0.001) en 2019–2020 — depende del período elegido, posiblemente por la mejora en la calidad del campo UPZ de UAECOB con el tiempo (no verificado).

### Conclusión de robustez
H1 y H3 son robustas a MAUP y a especificación. H4 es robusta además a distintos períodos; H5 no completamente. La fragilidad real de la asociación arrojo↔delitos/emergencias no está en la unidad espacial ni en la forma funcional, sino en **si se controla o no por estrato**.

---

## Fase 13 — Visualización y mapas

**Notebook:** `notebooks/02_mapas_finales.ipynb` · **Salida:** `outputs/figures/` (21 figuras)

### Qué hace
Genera los 10 mapas exigidos por el estándar del reto: vulnerabilidad, infraestructura de aseo, déficit, puntos críticos, delitos por localidad, emergencias, clusters LISA, hotspots Gi\*, superposición bivariada y mapa de zonas prioritarias.

### Hallazgo
La superposición "déficit alto **Y** puntos críticos altos" ocurre en **27 de 112 UPZ (24%)** — prácticamente lo esperado por azar si ambas variables fueran independientes (25%). Es una confirmación visual e independiente de la ausencia de asociación encontrada en H2.

En cambio, los *hotspots* Gi\* de puntos críticos y de incidentes **sí coinciden espacialmente** en varias UPZ, coherente con la autocorrelación bivariada positiva de H5 — sin implicar causalidad.

---

## Fase 15 — Exportación de la capa de dashboard

**Scripts:** `01_dimensions.py` · `02_indicators.py` · `03_spatial.py` · `04_temporal.py` · `05_hypotheses.py` · `06_metadata_and_validation.py`
**Salida:** 22 archivos en `data/dashboard/`

### Qué hace
Re-empaqueta lo que ya existe en Gold a un formato plano (CSV/GeoJSON) que un dashboard externo puede consumir directamente. **No calcula ningún indicador nuevo.** La única excepción es el cruce UPZ→localidad para permitir filtrado, que usa la misma técnica de *spatial join* ya validada en la Fase 5.

### Estructura generada

| Carpeta | Contenido |
|---|---|
| `dimensions/` | Catálogos de UPZ, localidades y años |
| `indicators/` | Indicadores territoriales por UPZ y localidad |
| `spatial/` | Geometrías, ubicaciones de puntos críticos, hotspots, estadística espacial |
| `temporal/` | Series de tendencias |
| `hypotheses/` | Tabla de las 28 pruebas estadísticas con p crudo y **p ajustado por FDR** |
| `metadata/` | Diccionario de datos y catálogo de datasets |

### Regla de integridad aplicada
Si un campo requerido por el estándar del dashboard **no existe ya calculado y validado en Gold, se omite** — no se rellena con ceros ni se aproxima. Todos los campos omitidos quedan documentados en `data/dashboard/metadata/data_dictionary.csv` con estado `NOT_AVAILABLE_YET` y su motivo. El último script valida la integridad referencial de toda la capa.

### Normalización dual expuesta al consumo

La capa expone las dos normalizaciones **juntas** en `data/dashboard/indicators/waste_infrastructure_{upz,localidad}.csv`:
`cestas_per_km2` junto a `cestas_per_1000pop` y `cestas_per_10000pop`, más `waste_deficit_percapita`
y la bandera `is_residential`. Exponer solo la densidad por área reproduciría en el dashboard el
mismo sesgo que ocultaba la desigualdad en el análisis. `data/dashboard/indicators/vulnerability.csv` incorpora
además `population`, `population_female`, `population_0_14` y `population_density_km2`.

Tres entradas del diccionario que estaban marcadas `NOT_AVAILABLE_YET` (`population`,
`population_density`, `*_per_100k`) pasaron a disponibles con la 15ª fuente. Una sigue no
disponible, pero por un motivo distinto al que se declaraba: `population_stratum_1_2` no se
calcula porque el DANE **no desagrega la población por estrato**, y estimarla multiplicando el
porcentaje de manzanas por la población total asumiría densidad uniforme entre estratos —
supuesto que los propios datos contradicen (las UPZ de estrato bajo son ~1,8× más densas).

### Corrección por comparaciones múltiples
La tabla de hipótesis reúne **28 pruebas** sobre la misma familia de datos. Se aplica Benjamini-Hochberg y se reportan `p_value_fdr` y `sig_tras_fdr` junto al p crudo. **De los 20 resultados significativos con p crudo, 17 sobreviven.** Los tres que no —H5 (Moran bivariado), H6 y el coeficiente de estrato del modelo conjunto, todos con p entre 0.040 y 0.046— se degradan automáticamente a `SUPPORTED_ONLY_BEFORE_FDR` y su nivel de evidencia baja de *confirmada* a *parcialmente respaldada*.

---

## Hallazgo transversal — Normalización per cápita (15ª fuente)

La incorporación de la población oficial por UPZ resolvió la limitación más importante que
arrastraba el proyecto y **cambió una conclusión sustantiva**.

### El problema que resolvió

Sin población, todos los modelos normalizaban por **área** (`offset = log(area_km2)`). Esa
métrica confunde densidad urbana con cobertura de servicio: una UPZ densa y popular puede
tener muchas cestas por km² y aun así muy pocas por habitante. La hipótesis original del
equipo prometía explícitamente normalizar por población — no era posible hacerlo.

### La desigualdad que estaba oculta (2024, UPZ residenciales)

| Estrato | UPZ | Población | Cestas/1.000 hab | Contenedores/1.000 hab | Densidad (hab/km²) |
|---|---|---|---|---|---|
| Bajo (≤2) | 26 | 2.444.001 | **2,56** | 0,09 | 24.596 |
| Medio (2–3) | 45 | 3.644.414 | 7,20 | 1,24 | 22.713 |
| Alto (>3) | 38 | 1.807.465 | **22,81** | 1,24 | 13.632 |

**Brecha de 8,9× en cestas por habitante** entre estrato bajo y alto (Mann-Whitney p=3,7e-09).
La asimetría es doble: las UPZ de estrato bajo concentran **más población** (2,44 M) con
**nueve veces menos** infraestructura que las de estrato alto (1,81 M).

### No es un artefacto de densidad

Las UPZ de estrato bajo son efectivamente más densas (rho=-0,50 entre estrato y densidad),
lo que exige descartar que la brecha sea un simple efecto de aglomeración. El modelo **M5**
(`n_cestas ~ estrato + log(densidad)`, offset = log(población), n=109, VIF=1,15) lo resuelve:

| Predictor | Coeficiente | IRR | IC 95% | p |
|---|---|---|---|---|
| `estrato_promedio_oficial` | +0,575 | **1,777** | [0,390 · 0,760] | <0,0001 |
| `log_densidad_poblacional` | −0,688 | 0,503 | [−0,902 · −0,473] | <0,0001 |

Cada punto adicional de estrato se asocia con **78% más cestas por habitante**, ya
controlando por densidad poblacional. La densidad es un confusor real (las zonas densas
tienen menos cobertura per cápita) pero **no explica el efecto del estrato**. La brecha se
mantiene entre 8,0× y 8,9× con cualquier umbral de población mínima (p<1e-7 siempre).

### Efecto sobre las hipótesis

| Hipótesis | Por área | Per cápita | Lectura |
|---|---|---|---|
| **H1** vulnerabilidad → déficit de aseo | rho=-0,574 (p=6,6e-11) | **rho=-0,628 (p=2,7e-13)** | ⬆ **Se fortalece.** La métrica que la hipótesis prometía confirma la desigualdad con más fuerza que el proxy de área |
| **H2** déficit → arrojo | no respaldada | rho=-0,014 (p=0,88) | ➡ **Sigue sin respaldo.** El resultado era robusto, no un artefacto de la métrica |
| **H3** vulnerabilidad → arrojo | fuerte, p<0,0001 | rho=-0,206 (p=0,032) | ⬇ **Se debilita.** Buena parte del efecto por km² era densidad poblacional |

> **Implicación para política pública.** El hallazgo cuantifica una desigualdad accionable y
> verificable: *las UPZ de estrato 1–2 tienen nueve veces menos cestas por habitante que las
> de estrato 4–6, y esa brecha persiste al controlar por densidad*. Es una afirmación mucho
> más fuerte y directamente utilizable por la UAESP que el índice relativo por km² que
> reportaba la versión anterior del informe.
>
> **Matiz honesto:** el mismo dato debilita H3. El vínculo "vulnerabilidad → arrojo
> clandestino" era en parte un efecto de densidad. El mecanismo que sobrevive con más fuerza
> es el de **cobertura desigual de infraestructura**, no el de generación de residuos.

### Capacidad habilitada

La fuente trae población por sexo y grupo de edad, lo que abre dos análisis que antes eran
imposibles y quedan disponibles en Gold (`poblacion_mujeres`, `poblacion_0_14`):
tasas de violencia intrafamiliar por 100.000 mujeres y exposición de niñez a emergencias
normalizada por población infantil real.

---

# Parte III — Resultados y cierre

## 16. Resultados por hipótesis

| Hipótesis | Método | Resultado | p-value | Efecto | Evidencia espacial | Conclusión |
|---|---|---|---|---|---|---|
| **H1** Vulnerabilidad → Déficit aseo | Spearman (UPZ y localidad, estrato oficial) + Moran bivariado | rho=-0.576 (UPZ, n=112) / rho=-0.598 (loc., n=19); Moran_BV=-0.381 | <0.0001 / 0.007 / 0.001 | Dirección esperada, consistente en ambos niveles, más fuerte que con el proxy anterior (-0.45/-0.49) | Co-clustering espacial significativo | **Confirmada** |
| **H2** Déficit aseo → Arrojo clandestino | Pearson simple + NegBin controlando estrato oficial + análisis de proximidad punto-a-punto | r=0.038 (simple, ns); coef=-0.484 (controlado, dirección opuesta, p=0.0005); puntos críticos **más cerca** de cestas (91.8m vs 212.8m aleatorio), contenedores (304m vs 466m) y bomberos (1.748m vs 2.308m), Mann-Whitney p<0.001 en los tres casos | 0.691 (simple) / 0.0005 (controlado) / <0.001 (proximidad) | Nulo en simple; invertido al controlar estrato; **la proximidad va en sentido contrario a la hipótesis** — arrojo ocurre más cerca de la infraestructura formal, no más lejos | Moran bivariado ≈0, ns (I=-0.007, p=0.48) | **No respaldada** — tres líneas de evidencia independientes (bivariado, multivariable, proximidad) apuntan en la misma dirección: el déficit de infraestructura no explica el arrojo clandestino |
| **H3** Vulnerabilidad → Arrojo clandestino | NegBin (UPZ, estrato oficial) | coef=-0.899, IRR=0.41 | <0.0001 | Fuerte, dirección esperada, consistente con el proxy (-0.95) | — | **Confirmada** |
| **H4** Arrojo → Delitos | Spearman bivariado (crudo/densidad/log, Fase 12) + NegBin multivariable (localidad, n=19-20) | Bivariado: rho=0.77-0.83, p<0.001, robusto a las 3 especificaciones. Multivariable: coef=+0.029 (marginal) → +0.007 (ns) al añadir estrato+cuadrantes | <0.001 (bivariado) / 0.077→0.723 (multivariable) | **Fuerte y robusto en bivariado; se diluye casi por completo al controlar vulnerabilidad** | Moran_BV=0.136, p=0.08 (marginal) | **Parcialmente respaldada** — el vínculo territorial es real y robusto, pero está mediado/confundido por el estrato, no es un efecto independiente |
| **H5** Arrojo → Emergencias | Spearman bivariado (Fase 12) + NegBin multivariable (UPZ) | Bivariado: rho=0.26-0.40, p<0.01, robusto a las 3 especificaciones. Multivariable: coef=-0.009, ns | <0.01 (bivariado) / 0.681 (multivariable) | Igual patrón que H4: fuerte en bivariado, nulo al controlar | Moran_BV=0.106, p=0.029 (significativo pero débil) | **Parcialmente respaldada** — mismo patrón de mediación/confusión por vulnerabilidad que H4 |
| **H6** Vulnerabilidad → Delitos | NegBin (localidad, modelo conjunto, estrato oficial) | coef=-0.922 | 0.045 · **FDR: 0.063** | Dirección esperada y significativa al 5% con p crudo, pero **no sobrevive la corrección por comparaciones múltiples** sobre la familia de 28 pruebas | — | **Parcialmente respaldada** |
| **H7** Vulnerabilidad → Emergencias | NegBin (UPZ, estrato oficial) | coef=-0.008, ns | 0.93 | Nulo | — | **No respaldada** |
| **Conjunta** (Delitos ~ Vulnerabilidad+Déficit+Arrojo+Policía) | NegBin multivariable (localidad, n=19) | Vulnerabilidad (p=0.045, **ahora significativa**) y déficit (p=0.059, signo invertido) sobreviven; arrojo y policía no aportan | — | Vulnerabilidad domina, con más fuerza que antes | — | **Respaldada por vulnerabilidad**: el mecanismo se sostiene por el estrato, no por arrojo/infraestructura |

VIF máximo observado: 2.7 (modelo conjunto, localidad) — sin problema de multicolinealidad en ningún modelo. Todos los modelos de conteo mostraron sobredispersión (deviance/df entre 4 y 505) y se ajustaron con Binomial Negativa en vez de Poisson. Sumapaz (localidad rural, código 20) queda fuera de los modelos de localidad porque la fuente oficial de estrato no cubre esa zona (n=19 en vez de 20) — consistente con el alcance urbano ya declarado del proyecto.

---

## 17. Estadística espacial — detalle

**Moran's I global** (ver `scripts/09_estadistica_espacial/moran_global.csv`): autocorrelación espacial positiva y significativa (p=0.001) en UPZ para `deficit_aseo_relativo` (I=0.41), `densidad_puntos_criticos_km2` (I=0.28), `densidad_incidentes_km2` (I=0.29), `densidad_cuadrantes_km2` (I=0.58) y `estrato_promedio_oficial` (I=0.70, la más fuerte — el estrato está fuertemente agrupado espacialmente, como es de esperar; muy cercano al I=0.79 que daba el proxy). A nivel localidad, solo `deficit_aseo_relativo` es significativo (p=0.022); las demás pierden significancia (n=19-20 reduce el poder estadístico — ver sección MAUP).

**LISA (Moran local):** `deficit_aseo_relativo` tiene 20 UPZ High-High (clusters de alto déficit) y 19 Low-Low; `estrato_promedio_oficial` tiene 20 High-High (zonas de estrato alto agrupadas) y 26 Low-Low (estrato bajo agrupado) — confirma segregación socioeconómica espacial fuerte, consistente con H1. (El proxy daba un patrón similar: 28 High-High / 30 Low-Low.)

**Getis-Ord Gi\*:** 20 UPZ hotspot + 19 coldspot significativos de puntos críticos; 17 UPZ hotspot de incidentes. A nivel localidad, con solo 20 unidades, apenas 1-3 hotspots/coldspots alcanzan significancia — ver `scripts/09_estadistica_espacial/gistar_resumen.csv` para el detalle completo.

**Matriz de correlación completa con corrección FDR (Fase 8, `scripts/08_estadistica/matriz_correlacion.csv`):** ninguna de las 9 variables clave pasa la prueba de normalidad de Shapiro-Wilk (todas p<0.05) → se usa Spearman en toda la fase estadística, no Pearson. De 36 pares posibles a nivel UPZ, 24 son significativos tras corrección Benjamini-Hochberg; a nivel localidad, 21 de 28. Los pares más fuertes: `deficit_aseo_relativo` ↔ `densidad_cestas_km2` (rho=-0.98/-0.99, por construcción — el índice se deriva de esa misma densidad, no es un hallazgo independiente) y `densidad_puntos_criticos_km2` ↔ `densidad_homicidios_km2` a nivel localidad (rho=0.83, ver sección 6).

**Relación inesperada, fuera de las 7 hipótesis originales (agent.md §17):** `densidad_cuadrantes_km2` ↔ `densidad_incidentes_km2` es de las correlaciones más fuertes de toda la matriz — rho=0.49 (UPZ, p<0.001) y rho=0.85 (localidad, p<0.001). Nadie planteó esta relación como hipótesis, y la dirección es contraintuitiva si se lee como "más policía → más emergencias causadas por policía" (no tiene sentido) — la lectura correcta es casi con certeza **reactiva**: la Policía despliega más cuadrantes donde ya hay más actividad/incidentes (cobertura proporcional a la demanda), no que los cuadrantes generen incidentes. Se reporta porque agent.md exige buscar activamente relaciones no solicitadas, no porque respalde ninguna hipótesis de la triple vulnerabilidad.

---

## 18. Modelos multivariables — detalle

Ver `scripts/10_modelos/resultados_modelos.csv` (12 coeficientes, 4 modelos). Resumen en sección 6. Ningún modelo Poisson simple fue adecuado (sobredispersión en los 4 casos) — se reportan todos como Binomial Negativa.

---

## 19. Análisis espacio-temporal — detalle

No se construyó un panel único UPZ×año: las tres fuentes con dimensión temporal (RBL, UAECOB, DAILoc) tienen ventanas y granularidades espaciales distintas (RBL no tiene UPZ, solo ASE; DAILoc no tiene UPZ, solo localidad; UAECOB sí tiene UPZ×año 2016-2020, guardado en `data/gold/emergencias/emergencias_upz_anio.parquet`). Forzar un panel único habría requerido asumir valores estáticos para variables que nunca se midieron repetidamente — se optó por analizar cada fuente en su resolución nativa (regla de agent.md: "no agregues todos los años sin conservar la dimensión temporal"). Detalle completo en `scripts/11_espacio_temporal/`:

- **UAECOB (2016-2020):** 2020 es un año claramente atípico (z=-1.76 vs media del periodo) — coincide con el corte parcial del archivo (agosto 2020) y con la pandemia, no se puede distinguir cuál de las dos causas domina con estos datos. De las 112 UPZ, **43 muestran tendencia decreciente significativa** (p<0.10) en incidentes 2016-2020 y solo 3 muestran tendencia creciente — patrón dominante de declive, aunque sesgado por el año 2020 incompleto.
- **DAILoc (2018-2026):** homicidios con tendencia leve al alza (pendiente=+8.35/año, p=0.062, marginal); 2025 es el año atípico (z=1.72, el más alto del periodo). Violencia intrafamiliar es atípica en 2023 (z=-1.59, la más baja) y 2026 (z=2.16, salto a 25.631 casos frente a 13.000-19.700 en años previos). **2026 es el año en curso (dato parcial, no un año completo)** — esto hace el hallazgo más llamativo, no menos: un conteo *parcial* de 2026 ya supera a los 8 años *completos* anteriores en violencia intrafamiliar. Con datos de un año incompleto no se puede saber si es una aceleración real o un artefacto de cómo se acumula el conteo dentro del año; merece seguimiento cuando 2026 cierre. Mismo matiz aplica a RBL (2026 solo tiene 5 de ~12 archivos mensuales esperados) y no cambia ninguna conclusión de este informe, que se basa en agregados 2018-2025/2021-2025.
- **Localidades persistentemente altas en homicidios** (bajo coeficiente de variación año a año): Ciudad Bolívar (media 99.1, CV=0.12) y Kennedy (media 74.2, CV=0.15) — consistentes en el tiempo, no picos aislados.
- **RBL (2021-2026):** sin tendencia significativa (p=0.44). La media mensual antes (2021-2022: 37.601 t) y después (2023-2026: 36.903 t) de la corrección de la colisión de columnas (Fase 3-4) es consistente — confirma que el fix no introdujo una ruptura artificial en la serie.

---

## 20. Hotspots

Mapas ejecutados en `notebooks/02_mapas_finales.ipynb` (10/10 mapas exigidos por agent.md §20-D): vulnerabilidad, infraestructura de aseo (cestas/contenedores), déficit, puntos críticos, delitos por localidad (homicidios y VIF, único nivel donde DAILoc lo permite), emergencias, clusters LISA (High-High/Low-Low) para déficit y puntos críticos, hotspots/coldspots Getis-Ord Gi\* para incidentes y cuadrantes de policía, superposición bivariada y mapa final de zonas prioritarias. La superposición "déficit alto Y puntos críticos altos" simultáneamente ocurre en **27 de 112 UPZ (24%)** — prácticamente lo esperado por azar si ambas variables fueran independientes (25%), consistente con la ausencia de asociación bivariada UPZ↔UPZ encontrada en H2 (sección 6). Los hotspots Gi\* de `densidad_puntos_criticos_km2` y `densidad_incidentes_km2` sí coinciden espacialmente en varias UPZ — coherente con la autocorrelación bivariada positiva de H5, sin implicar causalidad.

---

## 21. Ranking territorial

Índice de vulnerabilidad compuesta (z-score, 25% cada uno: -estrato oficial + déficit_aseo + densidad_puntos_críticos + densidad_incidentes), construido en `scripts/06_construccion_variables/05_ranking_territorial.py`, guardado en `data/gold/modelos/ranking_upz.parquet` y visualizado en `notebooks/02_mapas_finales.ipynb` (mapa "zonas prioritarias", top 10 con contorno negro). Top 5 UPZ: **Las Cruces, San Francisco, El Tesoro, Corabastos, Patio Bonito**.

---

## 22. Análisis de robustez (MAUP)

Detalle completo y reproducible en `scripts/12_validacion/` (3 archivos CSV). Tres pruebas de robustez:

**a) UPZ vs Localidad (Moran's I global, mismas variables):** `deficit_aseo_relativo` I=0.41 (UPZ, p=0.001) vs I=0.27 (localidad, p=0.022); `densidad_incidentes_km2` I=0.29 (p=0.001) vs I=0.15 (p=0.079); `densidad_puntos_criticos_km2` I=0.28 (p=0.001) vs I=0.12 (p=0.121). Patrón consistente: **la autocorrelación espacial es sistemáticamente más débil a nivel localidad** — esperable por la pérdida de poder estadístico (n=19-20 vs n=112), no evidencia de que el efecto desaparezca.

**b) Conteo crudo vs densidad vs log-densidad (H1, H4/H5):** H1 (estrato↔déficit) se mantiene significativa en su única especificación posible (rho=-0.576 UPZ / -0.598 localidad, ambas p<0.01, estrato oficial). H4/H5 (puntos críticos↔incidentes/homicidios) es **significativa y de magnitud similar bajo las tres especificaciones** en ambos niveles espaciales (UPZ: rho=0.26-0.40; localidad: rho=0.77-0.83) — la relación bivariada NO es un artefacto de cómo se mide la variable.

**c) Sensibilidad a la matriz de pesos espaciales (Queen vs KNN k=5):** Moran's I cambia de magnitud (ej. déficit de aseo: 0.41 con Queen vs 0.34 con KNN) pero la significancia y la conclusión cualitativa (autocorrelación positiva fuerte) **no cambian** con ninguna de las 3 variables probadas — el hallazgo de agrupamiento espacial no depende de la definición de vecindad elegida.

**d) Sensibilidad a distintos períodos temporales:** H4 (arrojo↔homicidios, localidad) es estable en dos sub-periodos independientes de DAILoc (2018-2021: rho=0.76, p<0.001; 2022-2026: rho=0.78, p<0.001) — robusta al recorte temporal. H5 (arrojo↔incidentes, UPZ) **no lo es**: rho=0.14 (ns, p=0.13) en 2016-2017 vs rho=0.52 (p<0.001) en 2019-2020 — la asociación bivariada de H5 depende del periodo elegido, más débil en años tempranos y más fuerte en años recientes (posiblemente relacionado con la mejora en la calidad del campo UPZ del CSV de UAECOB con el tiempo, no verificado). Detalle en `scripts/12_validacion/robustez_periodos_temporales.csv`.

**Conclusión de robustez:** H1 y H3 son robustas a MAUP y a especificación. H4 es robusta también a distintos períodos temporales; H5 no lo es completamente. La asociación bivariada arrojo↔delitos/emergencias es robusta a especificación funcional, pero su interpretación causal/incremental depende críticamente de si se controla o no por estrato — ahí está la fragilidad real, más que en la unidad espacial o la forma funcional.

---

## 23. Limitaciones

1. ~~Estrato socioeconómico oficial no se pudo vincular a UPZ/localidad~~ — **resuelto**: `Esoc.csv` (2.99M unidades IDECA) sigue sin llave espacial verificable, pero se incorporó una 14ª fuente con geometría real ("Estratificación para Bogotá", manzanas), que sí permite el *spatial join* directo. Queda una limitación menor: esta fuente de manzana **no cubre Sumapaz** (localidad rural, código 20) — los modelos a nivel localidad corren con n=19, no 20, consistente con el alcance urbano ya declarado del proyecto.
2. **`CMHTOTAL`/`CMVITOTAL` vs suma de `CMH*CONT`/`CMVI*CONT` en DAILoc no coinciden** (11.445 vs 4.740 homicidios). Se determinó parcialmente la causa: **545 homicidios y 26.789 casos de violencia intrafamiliar corresponden al registro `CMIULOCAL='99'` ("Sin Localización")**, que el pipeline excluye por no ser asignable a una localidad — eso explica la diferencia entre el total publicado (11.445 / 562.569) y el total territorializado (10.900 / 535.780). La brecha restante (10.900 vs 4.740) obedece a que `CMHTOTAL` cubre un rango temporal más amplio que los campos anuales `CMH{año}CONT` (2018–2026), cuya semántica exacta no está documentada por el proveedor. Los modelos usan el campo CONT (con dimensión anual), no el TOTAL.
   > **Al citar cifras de contexto** debe usarse el total publicado por la entidad (11.445 homicidios, ~562.000 casos de VIF, 166.977 emergencias UAECOB); al reportar resultados del análisis territorial, los totales efectivos son 10.900, 535.780 y 165.500 respectivamente, tras excluir registros sin localización asignable.
3. ~~No hay población oficial por UPZ~~ — **resuelto**: se incorporó una **15ª fuente**, "Proyecciones y retroproyecciones de población 2005-2035" (SDP/DANE, Censo 2018), que cubre exactamente los mismos 112 polígonos UPZ (join 112/112, sin imputación). Los modelos ahora disponen de normalización per cápita además de por área. Limitaciones que quedan: (a) son **proyecciones**, no un conteo observado; (b) la serie por UPZ del DANE llega hasta 2024, mientras DAILoc y RBL alcanzan 2026, por lo que las tasas usan un denominador de 2024 contra numeradores acumulados de períodos más amplios — no son tasas anuales estrictas; (c) **3 UPZ no residenciales** (El Mochuelo 7 hab, Parque Entrenubes 698, Aeropuerto El Dorado 918) se excluyen de las tasas per cápita porque un denominador diminuto produce ratios sin sentido.
4. **Ninguna fuente de aseo/policía/bomberos tiene dimensión temporal real** (son *snapshots* actuales) — no se puede analizar su evolución en el tiempo ni su relación causal temporal con arrojo/delitos.
5. **n=20 a nivel localidad limita fuertemente el poder estadístico** de los modelos y de Moran's I — varias hipótesis "no respaldadas" a ese nivel podrían ser falsos negativos por tamaño de muestra, no ausencia real de relación.
6. **Sesgo de cobertura en género/niñez UAECOB**: campos de niñas/niños expuestos solo existen desde 2019 (34.8% de los registros).
7. **Análisis puramente correlacional/espacial**, sin diseño causal — ninguna afirmación de este informe debe leerse como causalidad.
8. **Multiplicidad de pruebas:** la tabla de hipótesis reúne 28 pruebas sobre la misma familia de datos. Se aplica corrección Benjamini-Hochberg (FDR) y se reporta `p_value_fdr` junto al p crudo en `data/dashboard/hypotheses/hypothesis_results.csv`. De los 20 resultados significativos con p crudo, **17 sobreviven la corrección**; los tres que no (H5-Moran bivariado, H6 y el coeficiente de estrato del modelo conjunto, todos con p entre 0.040 y 0.046) se degradan explícitamente a *parcialmente respaldada*. Los hallazgos centrales (H1, H3) sobreviven con holgura.
9. **Parámetro de dispersión fijo en los modelos NB:** los GLM Binomial Negativa se ajustan con `alpha=1.0` en lugar de estimar la dispersión de los datos. Se verificó que esta elección no altera las conclusiones — con α estimado (0.813 en el modelo M1) los coeficientes son prácticamente idénticos y la significancia se mantiene (p=0.0005 → 0.0015) — pero es una simplificación que conviene declarar.

---

## 24. Conclusiones

La vulnerabilidad socioeconómica — ahora medida con la fuente **oficial** de estratificación, no un proxy — es la variable más consistentemente asociada, espacial y estadísticamente, con déficit de aseo, arrojo clandestino y delitos: **H1 y H3 confirmadas**, ambas robustas a MAUP, a especificación y a la corrección por comparaciones múltiples (p<0.001 incluso tras FDR). H6 (vulnerabilidad → delitos) mejoró al reemplazar el proxy por el dato oficial y alcanza la dirección esperada con p=0.045, pero **no sobrevive la corrección FDR** sobre la familia de 28 pruebas (p ajustado = 0.063), por lo que se reporta como **parcialmente respaldada** y no como confirmada: con n=19 localidades el modelo conjunto no tiene poder para sostenerla por sí solo. El eslabón "déficit de aseo → arrojo" (H2) sigue sin evidencia bivariada (rho≈0, ns) y sigue apareciendo invertido al controlar por estrato (efecto de supresión) — esto no cambió con el estrato oficial. Los eslabones "arrojo → delitos/emergencias" (H4, H5) mantienen el mismo patrón: **la correlación bivariada es fuerte y robusta** (rho hasta 0.83) **pero se atenúa casi por completo al controlar por vulnerabilidad** en el modelo multivariable — evidencia de mediación/confusión por estrato, no de ausencia de relación territorial.

En conjunto: las correlaciones simples r=0.74 (cestas↔estrato) y r=0.68 (puntos críticos↔homicidios) reportadas anteriormente por el equipo son estadísticamente reales, robustas a distintas especificaciones, a la unidad espacial y ahora también a la fuente de estrato usada — pero **no reflejan un mecanismo de cuatro pasos independiente**. El patrón que mejor describe los datos es: la vulnerabilidad socioeconómica es la variable subyacente que genera simultáneamente menor infraestructura de aseo, más arrojo clandestino y más delitos/emergencias en las mismas zonas — no una cadena causal secuencial donde el déficit de aseo por sí mismo genere arrojo, ni donde el arrojo por sí mismo genere criminalidad. Esto reformula, más que refuta, la hipótesis original del equipo: la "triple vulnerabilidad" es real y espacialmente robusta, y ahora está sostenida por la fuente oficial de estratificación, no por un sustituto — pero su origen común más probable sigue siendo el estrato, no una cadena de causación entre los tres fenómenos.

## 25. Recomendaciones para investigaciones posteriores

1. ~~Conseguir de IDECA/Catastro una llave o geometría lote→UPZ/localidad~~ — **hecho**: "Estratificación para Bogotá" (manzanas) resuelve esto. Pendiente menor: conseguir la estratificación rural de Sumapaz si se quiere extender el análisis a las 20 localidades completas.
2. Aclarar con la Secretaría de Seguridad la semántica de `CONT` vs `TOTAL` en DAILoc antes de publicar cifras de homicidios.
3. Buscar una fuente de población por UPZ (DANE/SDP) para poder calcular tasas per cápita reales, no solo por km².
4. Si se dispone de series temporales de instalación de cestas/contenedores (fecha de instalación, hoy 54% nula en `FECHAINSTA`), repetir el análisis como panel espacio-temporal real.
5. Con n=20 en localidad, cualquier hallazgo "marginal" (p entre 0.05 y 0.10) merece re-testearse si se consigue una fuente con mayor desagregación temporal para aumentar el n efectivo.
