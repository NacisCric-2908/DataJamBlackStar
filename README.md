# 🏙️ DataJam Bogotá 2026 — Observatorio Territorial de Residuos, Seguridad Ciudadana y Emergencias

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-1.1-green.svg)](https://geopandas.org/)
[![Architecture: Medallion](https://img.shields.io/badge/Architecture-Bronze%20%E2%9E%94%20Silver%20%E2%9E%94%20Gold-amber.svg)]()
[![Dashboard: Local HTML](https://img.shields.io/badge/Deliverable-Interactive%20HTML%20Dashboard-purple.svg)]()

> Repositorio oficial y pipeline analítico reproducible para el **DataJam Bogotá 2026**.
> Estudio integrado de la **triple vulnerabilidad urbana**: inequidad en infraestructura de aseo (UAESP), emergencias urbanas e incendios (UAECOB) y delitos de alto impacto (Secretaría de Seguridad — DAILoc) en Bogotá D.C. (2016–2026), cruzados con el estrato socioeconómico oficial.

Este repositorio contiene **dos pipelines**:

1. **Pipeline original** (`notebooks/`, 6 scripts) — primera versión del análisis, con hallazgos por correlación simple.
2. **Pipeline riguroso ampliado** (`01_ingesta/` … `15_dashboard_export/`) — auditoría formal de datos, estadística espacial (Moran's I, LISA, Getis-Ord Gi*), modelos multivariables (Binomial Negativa) con control de confusores, análisis de robustez/MAUP, y una capa de datos exportada para un dashboard externo.

👉 **El pipeline riguroso matiza los hallazgos del original**: las correlaciones simples (r=0.74, r=0.68) son reales pero están mediadas por el estrato socioeconómico una vez se controla estadísticamente por vulnerabilidad — no son un mecanismo de causación directo entre déficit de aseo → arrojo → delitos. Ver conclusiones actualizadas en [`14_resultados/informe_final.md`](14_resultados/informe_final.md).

---

## 📌 Tabla de Contenidos

1. [Descripción del problema](#-1-descripción-del-problema)
2. [Fuentes de datos utilizadas](#-2-fuentes-de-datos-utilizadas)
3. [Metodología general](#-3-metodología-general)
4. [Estructura del repositorio](#-4-estructura-del-repositorio)
5. [Instrucciones de despliegue](#-5-instrucciones-de-despliegue)
6. [Instrucciones de ejecución](#-6-instrucciones-de-ejecución)
7. [Hallazgos principales](#-7-hallazgos-principales)
8. [Entregables](#-8-entregables)

---

## 🎯 1. Descripción del problema

### Contexto

Bogotá presenta una distribución territorial heterogénea de tres fenómenos urbanos que, hasta ahora, se analizaban por separado desde entidades distintas: la Unidad Administrativa Especial de Servicios Públicos (aseo), la Unidad Administrativa Especial Cuerpo Oficial de Bomberos (emergencias) y la Secretaría Distrital de Seguridad, Convivencia y Justicia (delitos de alto impacto). Esta fragmentación institucional impide identificar si los tres fenómenos se concentran en las mismas zonas de la ciudad y si esa concentración está asociada al estrato socioeconómico.

### Pregunta central

> ¿Existe una relación espacial y estadísticamente significativa entre la vulnerabilidad socioeconómica, el déficit de infraestructura de aseo formal, la proliferación de puntos críticos de arrojo clandestino y la ocurrencia de delitos de alto impacto y emergencias urbanas en Bogotá?

### Objetivos

1. Integrar en una sola arquitectura de datos (Medallion: Bronze → Silver → Gold) las fuentes abiertas de aseo, seguridad, emergencias y estratificación de Bogotá.
2. Construir indicadores territoriales comparables a nivel UPZ y localidad.
3. Contrastar estadísticamente 7 hipótesis (H1–H7) sobre la relación entre vulnerabilidad, déficit de aseo, arrojo clandestino, delitos y emergencias — con estadística espacial formal, no solo correlación simple.
4. Producir un dashboard interactivo y una capa de datos reutilizable para visualización externa.

### Fuera de alcance (esta fase)

Modelos predictivos, machine learning, índices de priorización de intervención o recomendaciones automáticas de política pública. El proyecto actual es **descriptivo, espacial y estadístico** — responde "¿qué está pasando y dónde?", no "¿qué deberíamos hacer?".

---

## 📊 2. Fuentes de datos utilizadas

Se integraron **14 fuentes** del Portal de Datos Abiertos de Bogotá y de la Infraestructura de Datos Espaciales del Distrito Capital (IDECA). Los datos crudos (`Bronze/`) **no se versionan en este repositorio** por su peso (>2 GB, con archivos individuales de hasta 1.1 GB) — se descargan desde el enlace al final de este documento.

| # | Fuente | Entidad | Formato | Variables clave |
|---|---|---|---|---|
| 1 | Datos de residuos recogidos (RBL) | UAESP | XLSX/CSV | toneladas recogidas por tipo, ASE, mes |
| 2 | Incidente atendido por bomberos | UAECOB | CSV | tipo de incidente, localidad, UPZ, estrato autorreportado, género/niñez expuesta |
| 3 | Delito de alto impacto (DAILoc) | Secretaría Distrital de Seguridad | GeoJSON | homicidios, hurtos, violencia intrafamiliar por localidad y año |
| 4 | Cuadrantes de policía | MEBOG | GeoJSON | polígonos de cobertura policial |
| 5 | Estratificación para Bogotá (manzana) | Secretaría Distrital de Planeación | GeoJSON | estrato 1–6 por manzana con geometría real |
| 6 | Estrato socioeconómico (Esoc) | IDECA / Catastro | CSV (vía GDB) | estrato por unidad catastral (CHIP) — sin llave espacial directa a UPZ |
| 7 | Mapa de Referencia — UPZ | IDECA | GeoJSON | polígonos de las 112 UPZ urbanas |
| 8 | Mapa de Referencia — localidades | IDECA | GeoJSON | polígonos de las 20 localidades |
| 9 | Cestas | UAESP | GeoJSON | ubicación y estado de cestas públicas |
| 10 | Contenerización | UAESP | GeoJSON | ubicación de contenedores |
| 11 | Puntos críticos de arrojo clandestino | UAESP | GeoJSON | ubicación, frecuencia, observación |
| 12 | Macrorutas de barrido | UAESP | GeoJSON | cobertura de barrido mecánico/manual |
| 13 | Estación de bomberos | UAECOB | GeoJSON | ubicación de las 17 estaciones |
| 14 | Hábitat en cifras — indicadores urbanos | Secretaría Distrital del Hábitat | XLSX | parques, uso del suelo, % predios por estrato |

**Consideraciones sobre la obtención de los datos:**

- Todas las fuentes son de acceso público (`datosabiertos.bogota.gov.co`, `ideca.gov.co`), no requieren credenciales ni autenticación.
- La fuente #5 (estratificación por manzana) se incorporó en una segunda etapa del proyecto: la fuente #6 (Esoc) no tiene una llave espacial verificable a UPZ/localidad, así que se reemplazó como variable principal de vulnerabilidad — ver `02_auditoria/reporte_auditoria.md` sección 4.1.
- No existe en ninguna de las 14 fuentes un dato oficial de **población por UPZ o localidad** — esto está documentado como limitación explícita en todo el pipeline (no se aproxima ni se inventa).
- Descarga de `Bronze/`: ver [enlace de datos](#-enlace-de-datos-crudos) al final de este documento.

---

## 🧭 3. Metodología general

### Arquitectura de datos (Medallion)

```mermaid
flowchart TD
    subgraph Bronze ["🥉 Bronze — datos crudos, sin modificar"]
        B["14 fuentes: XLSX, CSV, GeoJSON, GDB"]
    end
    subgraph Silver ["🥈 Silver — limpio, estandarizado, por dominio"]
        S["territorio · aseo · seguridad · emergencias · policia · bomberos · socioeconomico"]
    end
    subgraph Gold ["🥇 Gold — variables analíticas"]
        G["dimensiones · indicadores · modelos · estadística espacial"]
    end
    subgraph Consumo ["🚀 Capas de consumo"]
        D1["Dashboard HTML (pipeline original)"]
        D2["Informe final + notebooks (pipeline riguroso)"]
        D3["data/dashboard/ — CSV para app externa"]
    end
    Bronze --> Silver --> Gold --> D1 & D2 & D3
```

### Pipeline riguroso — 15 fases

| Fase | Carpeta | Qué hace |
|---|---|---|
| 1 | `01_ingesta/` | Catálogo de las 14 fuentes en Bronze (formato, tamaño, columnas) |
| 2 | `02_auditoria/` | Auditoría de calidad: geometrías inválidas, duplicados, nulos, CRS, cobertura temporal — **antes** de transformar nada |
| 3–4 | `03_limpieza/` | Normalización por dominio, con tabla de trazabilidad (fuente → transformación → motivo → registros afectados) |
| 5 | `05_integracion_espacial/` | *Spatial joins* reales (point-in-polygon, `within`/`intersects`) — no *matching* por texto |
| 6 | `06_construccion_variables/` | Dataset maestro UPZ/localidad, panel UPZ×año, datasets por hipótesis, diccionario de datos |
| 7 | `07_eda/` | Análisis exploratorio (distribuciones, mapas, correlaciones) |
| 8 | `08_estadistica/` | Matriz de correlación con corrección por comparaciones múltiples (FDR) |
| 9 | `09_estadistica_espacial/` | Moran's I global, LISA (Moran local), Getis-Ord Gi*, Moran bivariado |
| 10 | `10_modelos/` | Modelos de conteo (Poisson/Binomial Negativa) con control de confusores y VIF |
| 11 | `11_espacio_temporal/` | Tendencias, años atípicos, zonas persistentes vs. emergentes |
| 12 | `12_validacion/` | Robustez: UPZ vs. localidad (MAUP), distintas especificaciones, distintos períodos |
| 13 | `13_visualizacion/` | Mapas finales (LISA, hotspots, superposición, zonas prioritarias) |
| 14 | `14_resultados/` | Informe final consolidado |
| 15 | `15_dashboard_export/` | Exporta `data/dashboard/` — capa de consumo para una app externa, sin modelos predictivos |

### Técnicas estadísticas empleadas

- **Espaciales:** Moran's I global y local (LISA), Getis-Ord Gi\*, Moran bivariado, matrices de pesos espaciales Queen y KNN.
- **Multivariables:** GLM Poisson y Binomial Negativa (según sobredispersión), con *offset* de área para modelar tasas.
- **Robustez:** comparación UPZ vs. localidad (MAUP), conteo crudo vs. densidad vs. log-densidad, distintos períodos temporales, distintas matrices de pesos.
- **Validación:** corrección de p-values por comparaciones múltiples (Benjamini-Hochberg), pruebas de normalidad (Shapiro-Wilk) para elegir Pearson vs. Spearman.

---

## 📁 4. Estructura del repositorio

```text
datajam/
├── README.md                          # Este documento
├── requirements.txt                    # Dependencias fijadas
├── .gitignore
│
├── data/                                # Capa de datos del pipeline riguroso
│   ├── bronze/                          # Datos crudos (NO versionado — ver sección 5)
│   ├── silver/                          # Limpio/estandarizado por dominio (NO versionado)
│   ├── gold/                            # Variables analíticas (versionado, liviano)
│   └── dashboard/                       # Capa de consumo para app externa (versionado)
│       ├── dimensions/  indicators/  spatial/  temporal/  hypotheses/  metadata/
│
├── 01_ingesta/ … 15_dashboard_export/    # Pipeline riguroso — ver tabla de la sección 3
│
├── notebooks/                           # Pipeline original
│   ├── 01_eda_rbl_series_temporales.ipynb
│   ├── 02_eda_capas_geoespaciales.ipynb
│   ├── 03_eda_incidentes_uaecob.ipynb
│   ├── 04_eda_estratificacion_indicadores.ipynb
│   └── scripts/
│       ├── 01_build_silver_rbl.py
│       ├── 02_build_silver_geo.py
│       ├── 03_build_silver_incidentes.py
│       ├── 04_build_silver_estratos.py
│       ├── 05_build_gold_analisis.py
│       └── 06_build_dashboard.py
│
├── outputs/                             # Gráficos y dashboard HTML del pipeline original
│   └── dashboard_datajam_bogota_2026.html
│
└── docs/                                # Documentación e informes del equipo
    ├── informe_exhaustivo_datajam_2026.md
    └── nota_tecnica_datajam_2026.md
```

**Nota sobre `Bronze/`, `Silver/`, `Gold/` (mayúscula) en la raíz:** son artefactos regenerables del pipeline original si se vuelve a correr `notebooks/scripts/*.py`; están en `.gitignore`, igual que `data/bronze/` y `data/silver/`.

---

## 🔧 5. Instrucciones de despliegue

### Requisitos previos

- Python 3.10 o superior
- ~2.5 GB de espacio en disco para los datos crudos (`data/bronze/`)
- No se requieren credenciales, tokens ni conexión a bases de datos — todas las fuentes son de datos abiertos públicos

### Preparar el entorno

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd datajam

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Obtener los datos crudos

`data/bronze/` no está versionado por su peso (>2 GB). Descárgalo del enlace de Drive al final de este documento y colócalo en:

```text
datajam/data/bronze/
```

Debe quedar con esta estructura mínima: los 14 archivos/carpetas de fuentes (ver sección 2) más el geodatabase `gdb_mr_v06_26.gdb/`.

### Verificar la instalación

```bash
python -c "import pandas, geopandas, esda, libpysal, statsmodels; print('OK')"
```

---

## 🏃 6. Instrucciones de ejecución

### Opción A — Pipeline original (rápido, genera el dashboard HTML)

```bash
python notebooks/scripts/01_build_silver_rbl.py
python notebooks/scripts/02_build_silver_geo.py
python notebooks/scripts/03_build_silver_incidentes.py
python notebooks/scripts/04_build_silver_estratos.py
python notebooks/scripts/05_build_gold_analisis.py
python notebooks/scripts/06_build_dashboard.py

# Abrir el resultado
xdg-open outputs/dashboard_datajam_bogota_2026.html   # Linux
open outputs/dashboard_datajam_bogota_2026.html       # macOS
start outputs/dashboard_datajam_bogota_2026.html      # Windows
```

### Opción B — Pipeline riguroso completo (auditoría + estadística + informe)

Ejecutar **en este orden** (cada fase depende de la anterior):

```bash
python 01_ingesta/01_catalogo_fuentes.py
python 02_auditoria/01_auditoria_datos.py
python 02_auditoria/02_auditoria_estrato_oficial.py
python 03_limpieza/04_normalizacion_silver.py
python 03_limpieza/05_normalizacion_emergencias.py
python 03_limpieza/06_normalizacion_rbl.py
python 03_limpieza/07_normalizacion_socioeconomico.py
python 03_limpieza/08_normalizacion_estrato_oficial.py
python 05_integracion_espacial/01_spatial_joins.py
python 05_integracion_espacial/02_analisis_proximidad.py
python 06_construccion_variables/01_dataset_maestro.py
python 06_construccion_variables/02_dataset_upz_anio_e_hipotesis.py
python 06_construccion_variables/03_data_dictionary.py
python 06_construccion_variables/04_completar_gold_subcarpetas.py
python 06_construccion_variables/05_ranking_territorial.py
jupyter nbconvert --to notebook --execute --inplace 07_eda/01_eda_dataset_maestro.ipynb
python 08_estadistica/01_pruebas_estadisticas.py
python 09_estadistica_espacial/01_moran_lisa_getis.py
python 09_estadistica_espacial/02_guardar_pesos_espaciales.py
python 10_modelos/01_modelos_multivariables.py
python 11_espacio_temporal/01_analisis_temporal.py
python 12_validacion/01_robustez.py
python 12_validacion/02_robustez_periodos.py
jupyter nbconvert --to notebook --execute --inplace 13_visualizacion/01_mapas_finales.ipynb
```

Resultado principal: **[`14_resultados/informe_final.md`](14_resultados/informe_final.md)**.

### Opción C — Generar la capa de datos para el dashboard externo

Requiere haber corrido la Opción B primero (usa `data/gold/`):

```bash
python 15_dashboard_export/01_dimensions.py
python 15_dashboard_export/02_indicators.py
python 15_dashboard_export/03_spatial.py
python 15_dashboard_export/04_temporal.py
python 15_dashboard_export/05_hypotheses.py
python 15_dashboard_export/06_metadata_and_validation.py   # valida integridad al final
```

Resultado: `data/dashboard/` (21 CSV/GeoJSON + diccionario de datos), lista para que una app externa la consuma.

### Verificación / pruebas

No hay suite de tests automatizada (proyecto de análisis de datos, no de software de producción). La validación se hace por:

```bash
# Sintaxis de todos los scripts
find . -name "*.py" -not -path "./.venv/*" -exec python -m py_compile {} \;

# Validación de integridad de la capa dashboard (incluida en el script 06 de esa fase)
python 15_dashboard_export/06_metadata_and_validation.py
```

---

## 💡 7. Hallazgos principales

> Ver la tabla completa de 8 hipótesis (28 pruebas estadísticas) en [`14_resultados/informe_final.md`](14_resultados/informe_final.md) sección 6, o en formato de datos en [`data/dashboard/hypotheses/hypothesis_results.csv`](data/dashboard/hypotheses/hypothesis_results.csv).

- **Confirmado:** la vulnerabilidad socioeconómica se asocia significativamente con el déficit de aseo (H1) y con la concentración de puntos críticos de arrojo clandestino (H3), de forma robusta a la unidad espacial (UPZ/localidad) y a la fuente de estrato (oficial vs. proxy).
- **No respaldado:** el déficit de aseo por sí solo no predice el arrojo clandestino una vez se controla por estrato (H2) — de hecho, los puntos críticos están más cerca de la infraestructura formal que un punto aleatorio de la ciudad.
- **Parcialmente respaldado:** arrojo↔delitos y arrojo↔emergencias tienen correlación bivariada fuerte (rho hasta 0.83) pero se atenúan al controlar por vulnerabilidad — evidencia de mediación por estrato, no de un efecto directo.

---

## 📦 8. Entregables

| Entregable | Ubicación |
|---|---|
| Dashboard HTML interactivo (pipeline original) | [`outputs/dashboard_datajam_bogota_2026.html`](outputs/dashboard_datajam_bogota_2026.html) |
| Informe final riguroso | [`14_resultados/informe_final.md`](14_resultados/informe_final.md) |
| Reporte de auditoría de datos | [`02_auditoria/reporte_auditoria.md`](02_auditoria/reporte_auditoria.md) |
| Diccionario de datos (Gold) | [`06_construccion_variables/data_dictionary.csv`](06_construccion_variables/data_dictionary.csv) |
| Capa de datos para dashboard externo | [`data/dashboard/`](data/dashboard/) |
| Nota técnica oficial del equipo | [`docs/nota_tecnica_datajam_2026.md`](docs/nota_tecnica_datajam_2026.md) |

### 🏛️ Recomendaciones de política pública (pipeline original — sujetas a los matices de la sección 7)

1. **Rebalanceo de mobiliario (UAESP):** instalar cestas y contenedores adicionales en las UPZ con mayor índice de vulnerabilidad compuesta (ver ranking territorial en el informe final).
2. **Estrategia interinstitucional en puntos críticos** (Secretaría de Seguridad + MEBOG + UAESP): dado que el arrojo clandestino no se explica por déficit de infraestructura, cualquier intervención debería considerar el estrato como variable subyacente compartida.
3. **Prevención comunitaria con enfoque de género** (UAECOB + Secretaría de la Mujer) en zonas de alta vulnerabilidad.

---

## 🔗 Enlace de datos crudos

`data/bronze/` (14 fuentes + geodatabase, ~2 GB) no está versionado en git — descárgalo aquí:

[Google Drive — Datos crudos del proyecto](https://drive.google.com/drive/folders/1jQZh3PLFPnMqk9hLOA2zVPJMGfBdlYMB?usp=drive_link)
