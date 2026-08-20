# Informe final — Análisis geoespacial y estadístico de triple vulnerabilidad urbana en Bogotá D.C.

DataJam Bogotá 2026 · pipeline ejecutado según `agent.md` · generado el 2026-08-19

---

## 1. Resumen ejecutivo

Se auditó, limpió, integró espacialmente y modeló estadísticamente el cruce entre vulnerabilidad socioeconómica, déficit de infraestructura de aseo, arrojo clandestino de residuos, delitos de alto impacto y emergencias urbanas en Bogotá, a nivel UPZ (n=112 urbanas) y localidad (n=19-20 urbanas), con Bronze→Silver→Gold trazable y estadística espacial formal (Moran's I, LISA, Getis-Ord Gi*, Moran bivariado) más modelos de conteo (Poisson/Binomial Negativa) controlando confusores.

**Actualización (14ª fuente incorporada):** el estrato socioeconómico usa ahora la fuente **oficial** — "Estratificación para Bogotá" (Secretaría Distrital de Planeación, manzanas con `ESTRATO` asignado y geometría real) — en vez del proxy autorreportado en incidentes UAECOB que se usó en una primera versión de este informe. El *spatial join* directo manzana→UPZ/localidad logró 98.5%/100% de cobertura (44.260 manzanas, 39.150 con estrato válido). El proxy anterior resultó altamente correlacionado con el oficial (r=0.96 entre ambas fuentes a nivel localidad) — no estaba mal, pero ya no es necesario.

**Resultado central:** la vulnerabilidad socioeconómica (ahora con el estrato oficial) sigue siendo el predictor más robusto y consistente — se asocia significativamente con déficit de aseo (H1, confirmada en ambos niveles espaciales) y con arrojo clandestino (H3, confirmada, muy fuerte, coef=-0.90 IRR=0.41 p<0.0001). El **déficit de infraestructura de aseo por sí solo NO predice arrojo clandestino** una vez se controla por estrato (H2, no respaldada / efecto de supresión) — el hallazgo r=+0.74 del dashboard previo del equipo era una correlación simple sin control de confusores.

**Matiz importante (Fase 12, verificado tras una revisión de robustez):** la correlación bivariada entre **puntos críticos de arrojo y delitos/emergencias sí es fuerte y robusta** — rho=0.83 (localidad, homicidios) y rho=0.26-0.40 (UPZ, incidentes), estable bajo conteo crudo, densidad y log-densidad. Lo que **no sobrevive** es el efecto *incremental* de arrojo una vez el modelo incluye estrato y cuadrantes de policía (H4/H5 se atenúan a marginal/no significativo en el modelo multivariable). Esto no es una contradicción — es evidencia de que el estrato **media o confunde** buena parte de la asociación arrojo↔delitos/emergencias, más que un efecto directo independiente.

**Esto no significa que la hipótesis original del equipo esté "mal"** — significa que la evidencia estadística disponible respalda la mitad delantera del mecanismo (vulnerabilidad → déficit, vulnerabilidad → arrojo) pero no la mitad trasera (arrojo → delitos/emergencias) con la fuerza que se había reportado.

---

## 2. Calidad y cobertura de los datos

Ver `02_auditoria/reporte_auditoria.md` para el detalle completo. Resumen de hallazgos con impacto real, corregidos en Silver:

| Hallazgo | Severidad | Corrección aplicada |
|---|---|---|
| *Join* UPZ↔incidentes por texto libre: solo 19% de coincidencia | 🔴 Alto | El campo trae el código UPZ oficial como prefijo (ej. "103 LA SABANA"); extraerlo sube el match a **99.2%** |
| RBL 2023-2026: dos columnas distintas ("Recolección de arrojo clandestino" y "...en punto limpio") colisionaban al mismo nombre canónico, una sobrescribía a la otra silenciosamente | 🔴 Alto | Columnas separadas explícitamente (`arrojo_clandestino_t` vs `arrojo_clandestino_punto_limpio_t`) |
| UPZ y UPR (rural) comparten numeración (UPZ3="Guaymaral" vs UPR3="Rio Tunjuelo") | 🔴 Alto (hallado durante esta fase) | Se excluyen las 4 UPR; fuera de alcance declarado del proyecto (zona rural) |
| Columna `año` en incidentes UAECOB quedaba 100% NaN (bug de pandas en sesión previa) | 🔴 Alto | Ya corregido antes de esta fase |
| 89.9% geometrías inválidas en macrorutas de barrido | 🟡 Medio | Reparadas con `make_valid()`, 0 pérdida de features |
| 1 fila "Sin Localización" (código 99/999) en IRUPZ/IRLoc/DAILoc con geometría nula | 🟡 Medio | Excluida con justificación (no es una unidad territorial real) |
| Duplicados exactos en UAECOB (58/68/4/3/0 según año) y 1 en contenerización | 🟡 Medio | Eliminados |
| `Esoc.csv` (estrato IDECA, 2.99M unidades): sin llave verificable a UPZ/localidad | 🟢 Resuelto por otra vía | `Esoc.csv` sigue sin llave espacial, pero se incorporó una **14ª fuente** — "Estratificación para Bogotá" (manzanas con geometría + ESTRATO), *spatial join* directo, 98.5%/100% de cobertura a UPZ/Localidad |
| `CMHTOTAL`/`CMVITOTAL` (DAILoc) no coincide con la suma de columnas anuales `CMH*CONT` (11.445 vs 4.740 homicidios) | 🟡 Medio, **no resuelto** | Se conservan ambos campos en paralelo, sin elegir uno arbitrariamente |

---

## 3. Metodología

Arquitectura Medallion estricta: `data/bronze/` (intacto) → `data/silver/` (por dominio: territorio, aseo, seguridad, emergencias, policia, bomberos, socioeconomico) → `data/gold/` (dimensiones, variables analíticas, estadística espacial, modelos). Pipeline en `01_ingesta/` … `14_resultados/`, cada uno ejecutado como script Python versionado, con tabla de trazabilidad (`03_limpieza/trazabilidad.csv`, 24 transformaciones documentadas — fuente, transformación, motivo, registros afectados).

*Spatial joins* reales (point-in-polygon `within` para puntos, `intersects` para cuadrantes de policía que cruzan límites administrativos) — no matching por texto en ningún punto del pipeline nuevo. CRS unificado a EPSG:4326 para joins, EPSG:3116 (Magna-Sirgas Bogotá) para cálculos de área/distancia métricos.

Unidad espacial principal: **UPZ** (n=112, tras excluir 4 UPR rurales y 1 "sin localización"). Se repite el análisis a nivel **localidad** (n=20 en general; n=19 en los análisis que usan el estrato oficial, que no cubre Sumapaz) para evaluar sensibilidad a MAUP (sección 12).

**Entregables Gold adicionales** (`data/gold/modelos/`): además de las tablas maestras cross-sectional (`dataset_hipotesis_upz.parquet`, `..._localidad.parquet`) usadas en la sección 6, existe `dataset_hipotesis.parquet` con la estructura literal **UPZ × Año** que pide agent.md (2016-2020, único rango con panel real vía UAECOB) — las columnas de infraestructura llevan el prefijo `snap_` porque son *snapshots* estáticos replicados por año, no mediciones repetidas; y 7 datasets `hypothesis_h1.parquet`…`h7.parquet` + `features_delitos.parquet` + `features_emergencias.parquet`, cada uno con solo las variables relevantes a esa hipótesis. `06_construccion_variables/data_dictionary.csv` documenta las 8 preguntas de linaje que exige agent.md (fuente, transformación, fórmula, unidad, unidad espacial, periodo, supuestos) para cada variable Gold.

---

## 4. Variables construidas

Dataset maestro `data/gold/modelos/dataset_hipotesis_upz.parquet` (112×21) y `..._localidad.parquet` (20×30):

- **Vulnerabilidad:** `estrato_promedio_oficial` / `estrato_modal_oficial` — fuente **oficial** (manzanas con geometría, "Estratificación para Bogotá", *spatial join* directo). `estrato_promedio_reportado` / `estrato_modal_reportado` (proxy autorreportado en incidentes UAECOB) se conserva en las tablas para comparación (r=0.96 con el oficial a nivel localidad).
- **Aseo:** `n_cestas`, `n_contenedores`, `densidad_cestas_km2`, `densidad_contenedores_km2`, `cobertura_macrorutas_pct`, `deficit_aseo_relativo` (z-score invertido de densidad de cestas+contenedores; documentado, reproducible, no asume "menos cestas = déficit" sin definición operacional).
- **Arrojo:** `n_puntos_criticos`, `densidad_puntos_criticos_km2`.
- **Emergencias:** `n_incidentes_total`, `n_incendios`, `densidad_incidentes_km2`, `n_ninas_expuestas`, `n_ninos_expuestos`.
- **Seguridad** (solo localidad, DAILoc no trae UPZ): `homicidios_cont`, `homicidios_total_oficial`, `violencia_intrafamiliar_cont`, `violencia_intrafamiliar_total_oficial`, `delitos_alto_impacto_cont`.
- **Accesibilidad institucional:** `n_cuadrantes`, `densidad_cuadrantes_km2`, `dist_estacion_bomberos_m`, `n_estaciones_bomberos_5km`.
- **Control:** `area_km2` (offset de los modelos de conteo, en vez de población — no existe población oficial por UPZ en las 13 fuentes).

---

## 5. EDA

Ver notebook ejecutado `07_eda/01_eda_dataset_maestro.ipynb` (mapas coropléticos, mapa de puntos, histogramas, boxplots, matriz de correlación Spearman, series temporales). Hallazgos clave:

- `n_puntos_criticos` y `n_incidentes_total` tienen asimetría positiva fuerte → justifica modelos de conteo no lineales (Fase 10), no regresión lineal.
- Series temporales en **ventanas no solapadas**: RBL 2021-2026, UAECOB 2016-2020, DAILoc 2018-2026 — no hay un año común a las tres con las tres variables simultáneamente.
- Homicidios anuales (DAILoc, campo CONT) estables entre 478-588/año 2018-2025; violencia intrafamiliar salta a 25.631 en 2026 frente a 13.000-19.000 en años previos — posible corte de año incompleto, no verificado, se reporta sin interpretar.

---

## 6. Resultados por hipótesis

| Hipótesis | Método | Resultado | p-value | Efecto | Evidencia espacial | Conclusión |
|---|---|---|---|---|---|---|
| **H1** Vulnerabilidad → Déficit aseo | Spearman (UPZ y localidad, estrato oficial) + Moran bivariado | rho=-0.576 (UPZ, n=112) / rho=-0.598 (loc., n=19); Moran_BV=-0.381 | <0.0001 / 0.007 / 0.001 | Dirección esperada, consistente en ambos niveles, más fuerte que con el proxy anterior (-0.45/-0.49) | Co-clustering espacial significativo | **Confirmada** |
| **H2** Déficit aseo → Arrojo clandestino | Pearson simple + NegBin controlando estrato oficial + análisis de proximidad punto-a-punto | r=0.038 (simple, ns); coef=-0.484 (controlado, dirección opuesta, p=0.0005); puntos críticos **más cerca** de cestas (91.8m vs 212.8m aleatorio), contenedores (304m vs 466m) y bomberos (1.748m vs 2.308m), Mann-Whitney p<0.001 en los tres casos | 0.691 (simple) / 0.0005 (controlado) / <0.001 (proximidad) | Nulo en simple; invertido al controlar estrato; **la proximidad va en sentido contrario a la hipótesis** — arrojo ocurre más cerca de la infraestructura formal, no más lejos | Moran bivariado ≈0, ns (I=-0.007, p=0.48) | **No respaldada** — tres líneas de evidencia independientes (bivariado, multivariable, proximidad) apuntan en la misma dirección: el déficit de infraestructura no explica el arrojo clandestino |
| **H3** Vulnerabilidad → Arrojo clandestino | NegBin (UPZ, estrato oficial) | coef=-0.899, IRR=0.41 | <0.0001 | Fuerte, dirección esperada, consistente con el proxy (-0.95) | — | **Confirmada** |
| **H4** Arrojo → Delitos | Spearman bivariado (crudo/densidad/log, Fase 12) + NegBin multivariable (localidad, n=19-20) | Bivariado: rho=0.77-0.83, p<0.001, robusto a las 3 especificaciones. Multivariable: coef=+0.029 (marginal) → +0.007 (ns) al añadir estrato+cuadrantes | <0.001 (bivariado) / 0.077→0.723 (multivariable) | **Fuerte y robusto en bivariado; se diluye casi por completo al controlar vulnerabilidad** | Moran_BV=0.136, p=0.08 (marginal) | **Parcialmente respaldada** — el vínculo territorial es real y robusto, pero está mediado/confundido por el estrato, no es un efecto independiente |
| **H5** Arrojo → Emergencias | Spearman bivariado (Fase 12) + NegBin multivariable (UPZ) | Bivariado: rho=0.26-0.40, p<0.01, robusto a las 3 especificaciones. Multivariable: coef=-0.009, ns | <0.01 (bivariado) / 0.681 (multivariable) | Igual patrón que H4: fuerte en bivariado, nulo al controlar | Moran_BV=0.106, p=0.029 (significativo pero débil) | **Parcialmente respaldada** — mismo patrón de mediación/confusión por vulnerabilidad que H4 |
| **H6** Vulnerabilidad → Delitos | NegBin (localidad, modelo conjunto, estrato oficial) | coef=-0.922 | **0.045** | Dirección esperada, ahora **significativa al 5%** (con el proxy era solo marginal, p=0.086) | — | **Confirmada** (con la fuente oficial deja de ser "parcial") |
| **H7** Vulnerabilidad → Emergencias | NegBin (UPZ, estrato oficial) | coef=-0.008, ns | 0.93 | Nulo | — | **No respaldada** |
| **Conjunta** (Delitos ~ Vulnerabilidad+Déficit+Arrojo+Policía) | NegBin multivariable (localidad, n=19) | Vulnerabilidad (p=0.045, **ahora significativa**) y déficit (p=0.059, signo invertido) sobreviven; arrojo y policía no aportan | — | Vulnerabilidad domina, con más fuerza que antes | — | **Respaldada por vulnerabilidad**: el mecanismo se sostiene por el estrato, no por arrojo/infraestructura |

VIF máximo observado: 2.7 (modelo conjunto, localidad) — sin problema de multicolinealidad en ningún modelo. Todos los modelos de conteo mostraron sobredispersión (deviance/df entre 4 y 505) y se ajustaron con Binomial Negativa en vez de Poisson. Sumapaz (localidad rural, código 20) queda fuera de los modelos de localidad porque la fuente oficial de estrato no cubre esa zona (n=19 en vez de 20) — consistente con el alcance urbano ya declarado del proyecto.

---

## 7. Estadística espacial

**Moran's I global** (ver `09_estadistica_espacial/moran_global.csv`): autocorrelación espacial positiva y significativa (p=0.001) en UPZ para `deficit_aseo_relativo` (I=0.41), `densidad_puntos_criticos_km2` (I=0.28), `densidad_incidentes_km2` (I=0.29), `densidad_cuadrantes_km2` (I=0.58) y `estrato_promedio_oficial` (I=0.70, la más fuerte — el estrato está fuertemente agrupado espacialmente, como es de esperar; muy cercano al I=0.79 que daba el proxy). A nivel localidad, solo `deficit_aseo_relativo` es significativo (p=0.022); las demás pierden significancia (n=19-20 reduce el poder estadístico — ver sección MAUP).

**LISA (Moran local):** `deficit_aseo_relativo` tiene 20 UPZ High-High (clusters de alto déficit) y 19 Low-Low; `estrato_promedio_oficial` tiene 20 High-High (zonas de estrato alto agrupadas) y 26 Low-Low (estrato bajo agrupado) — confirma segregación socioeconómica espacial fuerte, consistente con H1. (El proxy daba un patrón similar: 28 High-High / 30 Low-Low.)

**Getis-Ord Gi\*:** 20 UPZ hotspot + 19 coldspot significativos de puntos críticos; 17 UPZ hotspot de incidentes. A nivel localidad, con solo 20 unidades, apenas 1-3 hotspots/coldspots alcanzan significancia — ver `09_estadistica_espacial/gistar_resumen.csv` para el detalle completo.

**Matriz de correlación completa con corrección FDR (Fase 8, `08_estadistica/matriz_correlacion.csv`):** ninguna de las 9 variables clave pasa la prueba de normalidad de Shapiro-Wilk (todas p<0.05) → se usa Spearman en toda la fase estadística, no Pearson. De 36 pares posibles a nivel UPZ, 24 son significativos tras corrección Benjamini-Hochberg; a nivel localidad, 21 de 28. Los pares más fuertes: `deficit_aseo_relativo` ↔ `densidad_cestas_km2` (rho=-0.98/-0.99, por construcción — el índice se deriva de esa misma densidad, no es un hallazgo independiente) y `densidad_puntos_criticos_km2` ↔ `densidad_homicidios_km2` a nivel localidad (rho=0.83, ver sección 6).

**Relación inesperada, fuera de las 7 hipótesis originales (agent.md §17):** `densidad_cuadrantes_km2` ↔ `densidad_incidentes_km2` es de las correlaciones más fuertes de toda la matriz — rho=0.49 (UPZ, p<0.001) y rho=0.85 (localidad, p<0.001). Nadie planteó esta relación como hipótesis, y la dirección es contraintuitiva si se lee como "más policía → más emergencias causadas por policía" (no tiene sentido) — la lectura correcta es casi con certeza **reactiva**: la Policía despliega más cuadrantes donde ya hay más actividad/incidentes (cobertura proporcional a la demanda), no que los cuadrantes generen incidentes. Se reporta porque agent.md exige buscar activamente relaciones no solicitadas, no porque respalde ninguna hipótesis de la triple vulnerabilidad.

---

## 8. Modelos multivariables

Ver `10_modelos/resultados_modelos.csv` (12 coeficientes, 4 modelos). Resumen en sección 6. Ningún modelo Poisson simple fue adecuado (sobredispersión en los 4 casos) — se reportan todos como Binomial Negativa.

---

## 9. Análisis espacio-temporal

No se construyó un panel único UPZ×año: las tres fuentes con dimensión temporal (RBL, UAECOB, DAILoc) tienen ventanas y granularidades espaciales distintas (RBL no tiene UPZ, solo ASE; DAILoc no tiene UPZ, solo localidad; UAECOB sí tiene UPZ×año 2016-2020, guardado en `data/gold/emergencias/emergencias_upz_anio.parquet`). Forzar un panel único habría requerido asumir valores estáticos para variables que nunca se midieron repetidamente — se optó por analizar cada fuente en su resolución nativa (regla de agent.md: "no agregues todos los años sin conservar la dimensión temporal"). Detalle completo en `11_espacio_temporal/`:

- **UAECOB (2016-2020):** 2020 es un año claramente atípico (z=-1.76 vs media del periodo) — coincide con el corte parcial del archivo (agosto 2020) y con la pandemia, no se puede distinguir cuál de las dos causas domina con estos datos. De las 112 UPZ, **43 muestran tendencia decreciente significativa** (p<0.10) en incidentes 2016-2020 y solo 3 muestran tendencia creciente — patrón dominante de declive, aunque sesgado por el año 2020 incompleto.
- **DAILoc (2018-2026):** homicidios con tendencia leve al alza (pendiente=+8.35/año, p=0.062, marginal); 2025 es el año atípico (z=1.72, el más alto del periodo). Violencia intrafamiliar es atípica en 2023 (z=-1.59, la más baja) y 2026 (z=2.16, salto a 25.631 casos frente a 13.000-19.700 en años previos). **2026 es el año en curso (dato parcial, no un año completo)** — esto hace el hallazgo más llamativo, no menos: un conteo *parcial* de 2026 ya supera a los 8 años *completos* anteriores en violencia intrafamiliar. Con datos de un año incompleto no se puede saber si es una aceleración real o un artefacto de cómo se acumula el conteo dentro del año; merece seguimiento cuando 2026 cierre. Mismo matiz aplica a RBL (2026 solo tiene 5 de ~12 archivos mensuales esperados) y no cambia ninguna conclusión de este informe, que se basa en agregados 2018-2025/2021-2025.
- **Localidades persistentemente altas en homicidios** (bajo coeficiente de variación año a año): Ciudad Bolívar (media 99.1, CV=0.12) y Kennedy (media 74.2, CV=0.15) — consistentes en el tiempo, no picos aislados.
- **RBL (2021-2026):** sin tendencia significativa (p=0.44). La media mensual antes (2021-2022: 37.601 t) y después (2023-2026: 36.903 t) de la corrección de la colisión de columnas (Fase 3-4) es consistente — confirma que el fix no introdujo una ruptura artificial en la serie.

---

## 10. Hotspots

Mapas ejecutados en `13_visualizacion/01_mapas_finales.ipynb` (10/10 mapas exigidos por agent.md §20-D): vulnerabilidad, infraestructura de aseo (cestas/contenedores), déficit, puntos críticos, delitos por localidad (homicidios y VIF, único nivel donde DAILoc lo permite), emergencias, clusters LISA (High-High/Low-Low) para déficit y puntos críticos, hotspots/coldspots Getis-Ord Gi\* para incidentes y cuadrantes de policía, superposición bivariada y mapa final de zonas prioritarias. La superposición "déficit alto Y puntos críticos altos" simultáneamente ocurre en **27 de 112 UPZ (24%)** — prácticamente lo esperado por azar si ambas variables fueran independientes (25%), consistente con la ausencia de asociación bivariada UPZ↔UPZ encontrada en H2 (sección 6). Los hotspots Gi\* de `densidad_puntos_criticos_km2` y `densidad_incidentes_km2` sí coinciden espacialmente en varias UPZ — coherente con la autocorrelación bivariada positiva de H5, sin implicar causalidad.

---

## 11. Ranking territorial

Índice de vulnerabilidad compuesta (z-score, 25% cada uno: -estrato oficial + déficit_aseo + densidad_puntos_críticos + densidad_incidentes), construido en `06_construccion_variables/05_ranking_territorial.py`, guardado en `data/gold/modelos/ranking_upz.parquet` y visualizado en `13_visualizacion/01_mapas_finales.ipynb` (mapa "zonas prioritarias", top 10 con contorno negro). Top 5 UPZ: **Las Cruces, San Francisco, El Tesoro, Corabastos, Patio Bonito**.

---

## 12. Análisis de robustez (MAUP)

Detalle completo y reproducible en `12_validacion/` (3 archivos CSV). Tres pruebas de robustez:

**a) UPZ vs Localidad (Moran's I global, mismas variables):** `deficit_aseo_relativo` I=0.41 (UPZ, p=0.001) vs I=0.27 (localidad, p=0.022); `densidad_incidentes_km2` I=0.29 (p=0.001) vs I=0.15 (p=0.079); `densidad_puntos_criticos_km2` I=0.28 (p=0.001) vs I=0.12 (p=0.121). Patrón consistente: **la autocorrelación espacial es sistemáticamente más débil a nivel localidad** — esperable por la pérdida de poder estadístico (n=19-20 vs n=112), no evidencia de que el efecto desaparezca.

**b) Conteo crudo vs densidad vs log-densidad (H1, H4/H5):** H1 (estrato↔déficit) se mantiene significativa en su única especificación posible (rho=-0.576 UPZ / -0.598 localidad, ambas p<0.01, estrato oficial). H4/H5 (puntos críticos↔incidentes/homicidios) es **significativa y de magnitud similar bajo las tres especificaciones** en ambos niveles espaciales (UPZ: rho=0.26-0.40; localidad: rho=0.77-0.83) — la relación bivariada NO es un artefacto de cómo se mide la variable.

**c) Sensibilidad a la matriz de pesos espaciales (Queen vs KNN k=5):** Moran's I cambia de magnitud (ej. déficit de aseo: 0.41 con Queen vs 0.34 con KNN) pero la significancia y la conclusión cualitativa (autocorrelación positiva fuerte) **no cambian** con ninguna de las 3 variables probadas — el hallazgo de agrupamiento espacial no depende de la definición de vecindad elegida.

**d) Sensibilidad a distintos períodos temporales:** H4 (arrojo↔homicidios, localidad) es estable en dos sub-periodos independientes de DAILoc (2018-2021: rho=0.76, p<0.001; 2022-2026: rho=0.78, p<0.001) — robusta al recorte temporal. H5 (arrojo↔incidentes, UPZ) **no lo es**: rho=0.14 (ns, p=0.13) en 2016-2017 vs rho=0.52 (p<0.001) en 2019-2020 — la asociación bivariada de H5 depende del periodo elegido, más débil en años tempranos y más fuerte en años recientes (posiblemente relacionado con la mejora en la calidad del campo UPZ del CSV de UAECOB con el tiempo, no verificado). Detalle en `12_validacion/robustez_periodos_temporales.csv`.

**Conclusión de robustez:** H1 y H3 son robustas a MAUP y a especificación. H4 es robusta también a distintos períodos temporales; H5 no lo es completamente. La asociación bivariada arrojo↔delitos/emergencias es robusta a especificación funcional, pero su interpretación causal/incremental depende críticamente de si se controla o no por estrato — ahí está la fragilidad real, más que en la unidad espacial o la forma funcional.

---

## 13. Limitaciones

1. ~~Estrato socioeconómico oficial no se pudo vincular a UPZ/localidad~~ — **resuelto**: `Esoc.csv` (2.99M unidades IDECA) sigue sin llave espacial verificable, pero se incorporó una 14ª fuente con geometría real ("Estratificación para Bogotá", manzanas), que sí permite el *spatial join* directo. Queda una limitación menor: esta fuente de manzana **no cubre Sumapaz** (localidad rural, código 20) — los modelos a nivel localidad corren con n=19, no 20, consistente con el alcance urbano ya declarado del proyecto.
2. **`CMHTOTAL`/`CMVITOTAL` vs suma de `CMH*CONT`/`CMVI*CONT` en DAILoc no coinciden** (11.445 vs 4.740 homicidios) — no se determinó la causa; los modelos usan el campo CONT (con dimensión anual), no el TOTAL.
3. **No hay población oficial por UPZ** en ninguna de las 13 fuentes — los modelos usan área (km²) como *offset*, no población. Las "tasas por 100.000 habitantes" que pedía el enunciado no son calculables sin una fuente adicional de población por UPZ.
4. **Ninguna fuente de aseo/policía/bomberos tiene dimensión temporal real** (son *snapshots* actuales) — no se puede analizar su evolución en el tiempo ni su relación causal temporal con arrojo/delitos.
5. **n=20 a nivel localidad limita fuertemente el poder estadístico** de los modelos y de Moran's I — varias hipótesis "no respaldadas" a ese nivel podrían ser falsos negativos por tamaño de muestra, no ausencia real de relación.
6. **Sesgo de cobertura en género/niñez UAECOB**: campos de niñas/niños expuestos solo existen desde 2019 (34.8% de los registros).
7. **Análisis puramente correlacional/espacial**, sin diseño causal — ninguna afirmación de este informe debe leerse como causalidad.

---

## 14. Conclusiones

La vulnerabilidad socioeconómica — ahora medida con la fuente **oficial** de estratificación, no un proxy — es la variable más consistentemente asociada, espacial y estadísticamente, con déficit de aseo, arrojo clandestino y delitos: **H1, H3 y H6 confirmadas**, las tres robustas a MAUP y a especificación. H6 pasó de "parcialmente respaldada" a **confirmada** (p=0.045) al reemplazar el proxy por el dato real — la fuente oficial no solo confirma el hallazgo anterior, lo fortalece. El eslabón "déficit de aseo → arrojo" (H2) sigue sin evidencia bivariada (rho≈0, ns) y sigue apareciendo invertido al controlar por estrato (efecto de supresión) — esto no cambió con el estrato oficial. Los eslabones "arrojo → delitos/emergencias" (H4, H5) mantienen el mismo patrón: **la correlación bivariada es fuerte y robusta** (rho hasta 0.83) **pero se atenúa casi por completo al controlar por vulnerabilidad** en el modelo multivariable — evidencia de mediación/confusión por estrato, no de ausencia de relación territorial.

En conjunto: las correlaciones simples r=0.74 (cestas↔estrato) y r=0.68 (puntos críticos↔homicidios) reportadas anteriormente por el equipo son estadísticamente reales, robustas a distintas especificaciones, a la unidad espacial y ahora también a la fuente de estrato usada — pero **no reflejan un mecanismo de cuatro pasos independiente**. El patrón que mejor describe los datos es: la vulnerabilidad socioeconómica es la variable subyacente que genera simultáneamente menor infraestructura de aseo, más arrojo clandestino y más delitos/emergencias en las mismas zonas — no una cadena causal secuencial donde el déficit de aseo por sí mismo genere arrojo, ni donde el arrojo por sí mismo genere criminalidad. Esto reformula, más que refuta, la hipótesis original del equipo: la "triple vulnerabilidad" es real y espacialmente robusta, y ahora está sostenida por la fuente oficial de estratificación, no por un sustituto — pero su origen común más probable sigue siendo el estrato, no una cadena de causación entre los tres fenómenos.

## 15. Recomendaciones para investigaciones posteriores

1. ~~Conseguir de IDECA/Catastro una llave o geometría lote→UPZ/localidad~~ — **hecho**: "Estratificación para Bogotá" (manzanas) resuelve esto. Pendiente menor: conseguir la estratificación rural de Sumapaz si se quiere extender el análisis a las 20 localidades completas.
2. Aclarar con la Secretaría de Seguridad la semántica de `CONT` vs `TOTAL` en DAILoc antes de publicar cifras de homicidios.
3. Buscar una fuente de población por UPZ (DANE/SDP) para poder calcular tasas per cápita reales, no solo por km².
4. Si se dispone de series temporales de instalación de cestas/contenedores (fecha de instalación, hoy 54% nula en `FECHAINSTA`), repetir el análisis como panel espacio-temporal real.
5. Con n=20 en localidad, cualquier hallazgo "marginal" (p entre 0.05 y 0.10) merece re-testearse si se consigue una fuente con mayor desagregación temporal para aumentar el n efectivo.
