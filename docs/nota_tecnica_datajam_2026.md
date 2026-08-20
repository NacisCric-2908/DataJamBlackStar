# 📑 NOTA TÉCNICA Y FORMULARIO DE CARACTERIZACIÓN
## DataJam Bogotá 2026 — Desafío de Analítica Pública y Territorial

**Nombre de la Propuesta:** *Observatorio Territorial de Residuos, Seguridad Ciudadana y Emergencias Urbanas en Bogotá D.C.*  
**Entidades Fuentes:** Secretaría Distrital de Seguridad (DAILoc), Policía Metropolitana de Bogotá (MEBOG), UAECOB (Bomberos), UAESP (Aseo), IDECA, SDP, Secretaría Distrital del Hábitat  
**Cobertura Territorial:** 20 Localidades, 117 Unidades de Planeamiento Zonal (UPZ) y 599 Cuadrantes de Policía de Bogotá D.C.  
**Horizonte Temporal:** 2016 – 2026  

---

> ⚠️ **Nota (análisis posterior):** un análisis estadístico más riguroso (Moran's I, LISA, Getis-Ord Gi*, modelos multivariables con control de confusores, estrato oficial por manzana) matiza la "Hipótesis Validada" de esta nota — ver [`../14_resultados/informe_final.md`](../14_resultados/informe_final.md).

---

### 1. Caracterización de la Problemática (Paso 1 y 2)
Bogotá D.C. enfrenta un desafío multidimensional donde confluyen el **mal manejo de residuos sólidos (2.24 millones ton/año y 478 puntos críticos de arrojo clandestino)**, el **riesgo de emergencias urbanas e incendios (166.977 incidentes atendidos por UAECOB)** y la **criminalidad de alto impacto (11.445 homicidios y 562.000 casos de violencia intrafamiliar registrados en DAILoc entre 2018 y 2026)**.

El fenómeno analizado demuestra la existencia de un **círculo de vulnerabilidad socio-espacial**, donde el deterioro físico del entorno (déficit de cestas y acumulación de basura en vía pública) se superpone con altas tasas de criminalidad violenta y emergencias en sectores de estratos socioeconómicos bajos.

---

### 2. Pregunta e Hipótesis Orientadora (Paso 3 y 4)
* **Pregunta de Investigación:** ¿Existe una relación espacial y estadística significativa entre la vulnerabilidad socioeconómica (estratos 1 y 2), el déficit de infraestructura de aseo formal, la proliferación de puntos críticos de basura y la ocurrencia simultánea de delitos violentos y emergencias urbanas en Bogotá?
* **Hipótesis Validada (Triple Vulnerabilidad):** Las localidades y UPZ de estratos 1 y 2 sufren un **déficit extremo de mobiliario de aseo** (hasta 10 veces menos cestas por habitante que estratos 4-6), concentran la **mayoría de los puntos críticos de arrojo clandestino** y presentan los **niveles más altos de homicidios, violencia intrafamiliar y emergencias por fuego**.

---

### 3. Variables y Conjuntos de Datos Utilizados (Paso 5)

| Dimensión | Variable(s) Clave | Dataset Fuente | Nivel Territorial |
|---|---|---|---|
| **Socioeconómica** | Estrato modal y distribución predial (2.98M lotes) | `Esoc.csv` (IDECA) | Lote / Localidad / UPZ |
| **Residuos** | Toneladas RBL mensuales, arrojo clandestino | Series XLSX 2021-2026 (UAESP) | Operador (ASE) |
| **Infraestructura Aseo** | 69.830 Cestas públicas activas, Contenedores | `cestas.geojson`, `contenerizacion.geojson` | Puntos / UPZ / Loc |
| **Pasivo Ambiental** | 478 Puntos Críticos de Arrojo Activos | `puntos_criticos_residuos.geojson` | Puntos / UPZ / Loc |
| **Seguridad Ciudadana** | 11.445 Homicidios, Violencia Intrafamiliar, Hurtos | `DAILoc.geojson` (Policía/SIEDCO 2018-2026) | 20 Localidades |
| **Vigilancia Territorial** | 599 Cuadrantes de Policía, CAIs y Estaciones | `cuadrantepolicia.geojson` (MEBOG) | Polígonos / UPZ / Loc |
| **Emergencias** | 166.977 incidentes (incendios, rescates, etc.) | Incidentes UAECOB 2016-2020 | Evento / Localidad / UPZ |
| **Poblacional / Género** | Hombres, mujeres, niñas y niños expuestos | UAECOB + Indicadores Hábitat | Evento / Localidad |

---

### 4. Principales Hallazgos Empíricos

1. **La Brecha de Cestas ($r = +0.74$):** Localidades consolidadas de estratos 4 y 5 como Teusaquillo y Chapinero disponen de **285 a 337 cestas por cada 10.000 habitantes**, mientras que localidades populares de estratos 1 y 2 como Bosa y Ciudad Bolívar cuentan con apenas **29 cestas por cada 10.000 habitantes** (una disparidad de más de 10 a 1).
2. **Correlación Directa Crimen vs Puntos de Basura ($r = +0.68$):** Las localidades con mayor número de puntos de arrojo clandestino son precisamente aquellas con mayor volumen de homicidios: **Ciudad Bolívar (892 homicidios, 37 puntos críticos)**, **Kennedy (668 homicidios, 71 puntos críticos)** y **Bosa (439 homicidios, 56 puntos críticos)**.
3. **Violencia Intrafamiliar y Entorno Deteriorado ($r = +0.87$):** Existe una correlación muy alta entre zonas con pasivos ambientales por basura y reportes de violencia intrafamiliar (Kennedy: 20.001 casos; Suba: 19.848 casos; Ciudad Bolívar: 19.372 casos).
4. **Concentración de Emergencias:** El **74.7% de los incidentes** de bomberos se concentran en estratos 2 y 3.
5. **Enfoque Diferencial de Género y Niñez:** El **82% de las niñas y niños expuestos** a situaciones de riesgo por incendios estructurales habitan en estratos 1, 2 y 3.

---

### 5. Recomendaciones de Política Pública Articulada

1. **Plan de Choque de Rebalanceo de Mobiliario (UAESP):** Redistribuir e instalar al menos **15.000 nuevas cestas públicas y 3.000 contenedores** en las 20 UPZ con mayor índice de vulnerabilidad territorial (Bosa Central, Corabastos, Patio Bonito, La Gloria, Las Cruces).
2. **Estrategia Mixta de Intervención en Puntos Críticos (Secretaría de Seguridad + MEBOG + UAESP):** Focalizar patrullajes de los 599 cuadrantes policiales y cámaras de seguridad en los 478 puntos de arrojo clandestino para desarticular focos de inseguridad, narcomenudeo y contaminación.
3. **Prevención Comunitaria de Incendios con Enfoque de Género (UAECOB + SDMujer):** Capacitación barrial en prevención de incendios estructurales liderada por mujeres cuidadoras en zonas de estrato 1 y 2 de alta densidad habitacional.

---

### 6. Estructura del Entregable y Reproducibilidad
* **Pipeline Medallion:** `Bronze/` $\rightarrow$ `Silver/` $\rightarrow$ `Gold/` automatizado en scripts modulares de Python.
* **Entregable Interactivo:** Dashboard web local autónomo (`outputs/dashboard_datajam_bogota_2026.html`) con visualizaciones Plotly, mapas Leaflet con capas de cuadrantes policiales y estaciones de bomberos, series históricas y matriz de priorización.
