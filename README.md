# 🏙️ DataJam Bogotá 2026 — Observatorio Territorial de Residuos, Seguridad Ciudadana y Emergencias

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GeoPandas](https://img.shields.io/badge/GeoPandas-1.1-green.svg)](https://geopandas.org/)
[![Architecture: Medallion](https://img.shields.io/badge/Architecture-Bronze%20%E2%9E%94%20Silver%20%E2%9E%94%20Gold-amber.svg)]()
[![Dashboard: Local HTML](https://img.shields.io/badge/Deliverable-Interactive%20HTML%20Dashboard-purple.svg)]()

> Repositorio oficial y pipeline analítico reproducible para el **DataJam Bogotá 2026**.
> Estudio integrado de la **triple vulnerabilidad urbana**: inequidad en infraestructura de aseo (UAESP), emergencias urbanas e incendios (UAECOB) y delitos de alto impacto (Secretaría de Seguridad — DAILoc) en Bogotá D.C. (2016–2026), cruzados con el estrato socioeconómico oficial.

Este repositorio contiene **dos pipelines**:

1. **Pipeline original** (`notebooks/`, 2 notebooks) — primera versión del análisis, con hallazgos por correlación simple.
2. **Pipeline riguroso ampliado** (`scripts/01_ingesta/` … `scripts/15_dashboard_export/`) — auditoría formal de datos, estadística espacial (Moran's I, LISA, Getis-Ord Gi*), modelos multivariables (Binomial Negativa) con control de confusores, análisis de robustez/MAUP, y una capa de datos exportada para un dashboard externo.

👉 **El pipeline riguroso matiza los hallazgos del original**: las correlaciones simples (r=0.74, r=0.68) son reales pero están mediadas por el estrato socioeconómico una vez se controla estadísticamente por vulnerabilidad — no son un mecanismo de causación directo entre déficit de aseo → arrojo → delitos. Ver conclusiones actualizadas en [`docs/informe_final.md`](docs/informe_final.md).

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
3. Contrastar estadísticamente la hipótesis principal — *las zonas con mayor vulnerabilidad socioeconómica y menor disponibilidad relativa de infraestructura formal de aseo concentran más puntos críticos de arrojo clandestino* — y sus derivaciones hacia delitos y emergencias, con estadística espacial formal y modelos multivariables, no solo correlación simple.
4. Producir un dashboard interactivo y una capa de datos reutilizable para visualización externa.

### Fuera de alcance (esta fase)

Modelos predictivos, machine learning, índices de priorización de intervención o recomendaciones automáticas de política pública. El proyecto actual es **descriptivo, espacial y estadístico** — responde "¿qué está pasando y dónde?", no "¿qué deberíamos hacer?".

---

## 📊 2. Fuentes de datos utilizadas

Se integraron **15 fuentes** del Portal de Datos Abiertos de Bogotá y de la Infraestructura de Datos Espaciales del Distrito Capital (IDECA). Los datos crudos (`Bronze/`) **no se versionan en este repositorio** por su peso (~295 MB, con archivos individuales de hasta 79 MB) — se descargan desde el enlace al final de este documento.

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
| 15 | Proyecciones y retroproyecciones de población (2005–2035) | Secretaría Distrital de Planeación / DANE | ODS | población por UPZ y localidad, desagregada por sexo y grupo de edad |

**Consideraciones sobre la obtención de los datos:**

- Todas las fuentes son de acceso público (`datosabiertos.bogota.gov.co`, `ideca.gov.co`), no requieren credenciales ni autenticación.
- La fuente #5 (estratificación por manzana) se incorporó en una segunda etapa del proyecto: la fuente #6 (Esoc) no tiene una llave espacial verificable a UPZ/localidad, así que se reemplazó como variable principal de vulnerabilidad — ver `02_auditoria/reporte_auditoria.md` sección 4.1.
- La **población oficial por UPZ y localidad** proviene de las proyecciones SDP/DANE (15ª fuente), que cubren exactamente los mismos 112 polígonos UPZ del pipeline (join 112/112, sin imputación). Los indicadores se reportan normalizados **por área y por población**, porque comparar ambas es lo que separa densidad urbana de cobertura real de servicio.
- Descarga de `Bronze/`: ver [enlace de datos](#-enlace-de-datos-crudos) al final de este documento.

---

## 🧭 3. Metodología general

### Arquitectura de datos (Medallion)

```mermaid
flowchart TD
    subgraph Bronze ["🥉 Bronze — datos crudos, sin modificar"]
        B["15 fuentes: XLSX, CSV, ODS, GeoJSON"]
    end
    subgraph Silver ["🥈 Silver — limpio, estandarizado, por dominio"]
        S["territorio · aseo · seguridad · emergencias · policia · bomberos · socioeconomico · poblacion"]
    end
    subgraph Gold ["🥇 Gold — variables analíticas"]
        G["dimensiones · indicadores · modelos · estadística espacial"]
    end
    subgraph Consumo ["🚀 Capas de consumo"]
        D1["Atlas territorial — outputs/dashboard_prototipo_atlas.html"]
        D2["Informe final + notebooks (pipeline riguroso)"]
        D3["data/dashboard/ — CSV para app externa"]
    end
    Bronze --> Silver --> Gold --> D1 & D2 & D3
```

### Pipeline riguroso — 15 fases

| Fase | Carpeta | Qué hace |
|---|---|---|
| 1 | `scripts/01_ingesta/` | Catálogo de las 15 fuentes en Bronze (formato, tamaño, columnas) |
| 2 | `scripts/02_auditoria/` | Auditoría de calidad: geometrías inválidas, duplicados, nulos, CRS, cobertura temporal — **antes** de transformar nada |
| 3–4 | `scripts/03_limpieza/` | Normalización por dominio, con tabla de trazabilidad (fuente → transformación → motivo → registros afectados) |
| 5 | `scripts/05_integracion_espacial/` | *Spatial joins* reales (point-in-polygon, `within`/`intersects`) — no *matching* por texto |
| 6 | `scripts/06_construccion_variables/` | Dataset maestro UPZ/localidad, panel UPZ×año, datasets por hipótesis, diccionario de datos |
| 7 | `notebooks/01_eda_dataset_maestro.ipynb` | Análisis exploratorio (distribuciones, mapas, correlaciones) |
| 8 | `scripts/08_estadistica/` | Matriz de correlación con corrección por comparaciones múltiples (FDR) |
| 9 | `scripts/09_estadistica_espacial/` | Moran's I global, LISA (Moran local), Getis-Ord Gi*, Moran bivariado |
| 10 | `scripts/10_modelos/` | Modelos de conteo (Poisson/Binomial Negativa) con control de confusores y VIF |
| 11 | `scripts/11_espacio_temporal/` | Tendencias, años atípicos, zonas persistentes vs. emergentes |
| 12 | `scripts/12_validacion/` | Robustez: UPZ vs. localidad (MAUP), distintas especificaciones, distintos períodos |
| 13 | `notebooks/02_mapas_finales.ipynb` | Mapas finales (LISA, hotspots, superposición, zonas prioritarias) |
| 14 | `docs/informe_final.md` | Informe final consolidado |
| 15 | `scripts/15_dashboard_export/` | Exporta `data/dashboard/` — capa de consumo para una app externa, sin modelos predictivos |

### Técnicas estadísticas empleadas

- **Espaciales:** Moran's I global y local (LISA), Getis-Ord Gi\*, Moran bivariado, matrices de pesos espaciales Queen y KNN.
- **Multivariables:** GLM Poisson y Binomial Negativa (según sobredispersión), con *offset* de área para modelar tasas.
- **Robustez:** comparación UPZ vs. localidad (MAUP), conteo crudo vs. densidad vs. log-densidad, distintos períodos temporales, distintas matrices de pesos.
- **Validación:** corrección de p-values por comparaciones múltiples (Benjamini-Hochberg), pruebas de normalidad (Shapiro-Wilk) para elegir Pearson vs. Spearman.

---

## 📁 4. Estructura del repositorio

El repositorio sigue estrictamente el estándar de entregables del **DataJam Bogotá 2026**:

```text
├── main.py                             # Orquestador integral ejecutable de todo el pipeline (29 tareas)
├── README.md                           # Documentación completa del proyecto y metodología
├── requirements.txt                    # Dependencias fijadas y verificadas
├── .gitignore
│
├── data/                               # Arquitectura Medallion y capas de consumo
│   ├── bronze/                         # 15 fuentes crudas sin modificar (NO versionado — ver sección 5)
│   ├── silver/                         # Capa limpia y estandarizada por dominio (territorio, aseo, etc.)
│   ├── gold/                           # Capa analítica: modelos, variables consolidadas y rankings
│   └── dashboard/                      # Capa de consumo estructurada para visualización externa (CSV/GeoJSON)
│       ├── dimensions/  indicators/  spatial/  temporal/  hypotheses/  metadata/
│
├── notebooks/                          # Jupyter Notebooks analíticos y reproducibles
│   ├── 01_eda_dataset_maestro.ipynb    # EDA visual del dataset maestro, distribuciones y correlaciones
│   └── 02_mapas_finales.ipynb          # Análisis espacial final: mapas LISA, Getis-Ord Gi* y clusters
│
├── scripts/                            # Pipeline modular por fases de ingeniería y analítica
│   ├── 01_ingesta/                     # Catálogo automático de fuentes Bronze
│   ├── 02_auditoria/                   # 16 chequeos de calidad de datos y auditoría de estrato oficial
│   ├── 03_limpieza/                    # Normalización Silver y tabla de trazabilidad
│   ├── 05_integracion_espacial/        # Spatial joins (point-in-polygon) y análisis de proximidad
│   ├── 06_construccion_variables/      # Datasets maestros (UPZ y localidad), panel UPZ×año y diccionario
│   ├── 08_estadistica/                 # Pruebas de normalidad y correlación de Spearman con FDR
│   ├── 09_estadistica_espacial/        # Moran's I global/local (LISA), Getis-Ord Gi* y pesos espaciales
│   ├── 10_modelos/                     # Modelos multivariables Poisson y Binomial Negativa
│   ├── 11_espacio_temporal/            # Análisis de series temporales y persistencia territorial
│   ├── 12_validacion/                  # Análisis de robustez territorial (MAUP) y períodos
│   └── 15_dashboard_export/            # Exportación y validación de la capa para dashboard
│
├── outputs/                            # Entregables visuales y mapas exportados
│   ├── figures/                        # Gráficos de alta resolución (distribuciones, LISA, hotspots)
│   └── dashboard_prototipo_atlas.html  # Atlas territorial: dashboard interactivo autónomo (SVG propio, sin librerías externas)
│
└── docs/                               # Informes analíticos y notas técnicas
    ├── informe_final.md                # Informe final consolidado con modelos multivariables
```

---

## 🔧 5. Instrucciones de despliegue

### Requisitos previos

- Python 3.10 o superior (verificado hasta Python 3.14)
- ~2.5 GB de espacio en disco para los datos crudos (`data/bronze/`)
- No se requieren credenciales ni tokens — todas las fuentes provienen de datos abiertos distritales (`datosabiertos.bogota.gov.co` e IDECA)

### Preparar el entorno

```bash
# 1. Clonar el repositorio
git clone <url-del-repositorio>
cd DataJamBlackStar

# 2. Crear y activar entorno virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

# 3. Instalar dependencias
pip install -r requirements.txt
```

### Obtener los datos crudos

`data/bronze/` no se versiona en git por su peso (~295 MB). Descárgalo del enlace de Drive al final de este documento y colócalo en:

```text
DataJamBlackStar/data/bronze/
```

### Verificar la instalación

```bash
python -c "import pandas, geopandas, scipy, statsmodels, libpysal, esda; print('Ambiente configurado correctamente ✅')"
```

---

## 🏃 6. Instrucciones de ejecución

El pipeline completo se ejecuta de forma 100% reproducible con un solo comando mediante el orquestador principal:

### Ejecución de todo el pipeline (29 tareas)

```bash
python main.py
```

### Opciones avanzadas de ejecución:

```bash
# Ejecutar solo scripts ETL y estadísticos omitiendo notebooks (rápido, ~30s)
python main.py --skip-notebooks

# Ejecutar fases específicas (ejemplo: solo ingesta, auditoría y limpieza)
python main.py --phases 1 2 3

# Visualizar el dashboard interactivo
xdg-open outputs/dashboard_prototipo_atlas.html   # Linux
open outputs/dashboard_prototipo_atlas.html       # macOS
start outputs/dashboard_prototipo_atlas.html      # Windows
```

Resultado principal: **[`docs/informe_final.md`](docs/informe_final.md)**.

---

## 💡 7. Hallazgos principales

### La hipótesis principal

> **Las zonas de Bogotá D.C. con mayor vulnerabilidad socioeconómica y menor disponibilidad relativa de infraestructura formal de aseo presentan una mayor concentración espacial de puntos críticos de arrojo clandestino de residuos.**

**Veredicto: se confirma por la vía socioeconómica y se refuta por la vía de la infraestructura.** El arrojo clandestino sí se concentra donde vive la población más vulnerable, pero no donde falta el mobiliario de aseo — de hecho ocurre justo al lado de él.

**1. La concentración espacial existe y no es azar.** Los puntos críticos de arrojo se agrupan en el territorio (I de Moran = 0,284, p = 0,001, 112 UPZ): 13 UPZ forman conglomerados de alta concentración rodeados de alta concentración, frente a 20 UPZ en el extremo opuesto.

**2. La vulnerabilidad socioeconómica explica esa concentración.** En el modelo Binomial Negativa multivariable por UPZ, por cada punto que sube el estrato promedio de la zona el conteo de puntos críticos cae cerca de un 59% (coeficiente −0,899; IRR 0,407; IC 95% [−1,18; −0,62]; p corregido por FDR < 0,001; n = 112). El efecto se mantiene al controlar por el déficit de aseo y por el área de la zona.

**3. La desigualdad en la infraestructura de aseo también es real — y es el hallazgo más contundente del estudio.** Al normalizar por población oficial, las UPZ de **estrato 1–2 tienen 8,9 veces menos cestas por habitante** que las de estrato 4–6 (2,56 vs. 22,81 por cada 1.000 habitantes). La brecha **persiste al controlar por densidad poblacional** (IRR = 1,78 por punto de estrato, p < 0,0001), así que no es un efecto de aglomeración urbana. La asociación entre estrato y déficit de aseo aguanta todas las pruebas: Spearman ρ = −0,576 por UPZ y −0,598 por localidad, Moran bivariado = −0,381 (p = 0,001), y se fortalece al medir per cápita en vez de por área (ρ −0,574 → −0,628).

**4. Pero el déficit de infraestructura no es lo que produce el arrojo.** Cuando el modelo incluye el estrato, el déficit de aseo deja de predecir los puntos críticos y su coeficiente apunta en dirección contraria a la esperada (−0,484; p corregido = 0,001). El análisis de proximidad lo confirma: un punto crítico está en promedio a **91,8 m de una cesta pública**, mientras que un punto aleatorio de la ciudad está a **212,8 m** (Mann-Whitney, p < 0,001); con contenedores, 303,9 m frente a 466,3 m. Y la correlación espacial entre déficit y arrojo es prácticamente nula (Moran bivariado = −0,007, p = 0,48). La basura no se acumula donde no hay canecas: se acumula donde ya hay infraestructura, en las zonas de mayor vulnerabilidad.

**Lectura conjunta.** El estrato socioeconómico es el factor común detrás de los dos fenómenos, no un eslabón de una cadena. La mitad socioeconómica de la hipótesis se sostiene con evidencia sólida; la mitad de infraestructura no, y sostenerla llevaría a una intervención equivocada — instalar mobiliario donde ya lo hay.

### Lo que ocurre con delitos y emergencias

Donde hay más arrojo clandestino hay más homicidios (ρ = 0,83) y más emergencias urbanas (ρ = 0,40), y esas correlaciones aguantan los cambios de unidad territorial, de normalización y de período. Pero al meter el estrato en el modelo el arrojo deja de aportar información (coeficiente 0,007, p = 0,777 con homicidios; −0,009, p = 0,759 con emergencias). Es mediación por vulnerabilidad, no un efecto directo: la misma condición de fondo produce los dos fenómenos.

> El registro completo de las pruebas estadísticas — las 29, incluidas las que fallaron, con su p corregido por comparaciones múltiples — está en [`docs/informe_final.md`](docs/informe_final.md) sección 6, en [`data/dashboard/hypotheses/hypothesis_results.csv`](data/dashboard/hypotheses/hypothesis_results.csv) y en el tablero de hipótesis del dashboard.

---

## 📦 8. Entregables

| Entregable | Ubicación |
|---|---|
| Orquestador Maestro de Ejecución | [`main.py`](main.py) |
| Atlas territorial — dashboard HTML interactivo | [`outputs/dashboard_prototipo_atlas.html`](outputs/dashboard_prototipo_atlas.html) |
| Informe final riguroso | [`docs/informe_final.md`](docs/informe_final.md) |
| Nota Técnica de Integración de Datos | [`docs/nota_tecnica_integracion_datos.md`](docs/nota_tecnica_integracion_datos.md) |
| Reporte de auditoría de datos | [`scripts/02_auditoria/reporte_auditoria.md`](scripts/02_auditoria/reporte_auditoria.md) |
| Diccionario de datos (Gold) | [`scripts/06_construccion_variables/data_dictionary.csv`](scripts/06_construccion_variables/data_dictionary.csv) |
| Capa de datos para dashboard externo | [`data/dashboard/`](data/dashboard/) |
| Notebooks analíticos ejecutados | [`notebooks/`](notebooks/) |

### 🗺️ Dónde está el dashboard y qué hace

**Ubicación:** [`outputs/dashboard_prototipo_atlas.html`](outputs/dashboard_prototipo_atlas.html) — un archivo HTML único de ~220 KB. Se abre con doble clic o con `xdg-open outputs/dashboard_prototipo_atlas.html`: no necesita servidor, ni conexión a internet, ni librerías de terceros. El mapa, los sparklines y las barras son SVG generado por el propio archivo, y todas las cifras vienen embebidas desde `data/dashboard/` y `data/gold/`. Se adapta a tema claro y oscuro y es navegable con teclado.

| Sección | Qué permite |
|---|---|
| **Atlas territorial** | Mapa coroplético de las 112 UPZ / 19 localidades con 8 indicadores conmutables (vulnerabilidad compuesta, estrato, déficit de aseo, arrojo clandestino, emergencias, cestas, homicidios, densidad poblacional), interruptor **por km² / por habitante**, leyenda dinámica, I de Moran del indicador activo, panel de detalle por zona con sus clusters LISA/Gi\*, y ranking de las 12 UPZ prioritarias |
| **El hallazgo que reordena la historia** | La misma asociación medida sola y medida con el estrato dentro del modelo: el efecto del arrojo clandestino se desvanece al controlar por vulnerabilidad |
| **Tablero de hipótesis** | Las hipótesis declaradas antes de correr los modelos, con sus 29 pruebas, estadístico y p corregido por comparaciones múltiples (FDR), clasificadas en confirmada / parcial / no respaldada |
| **Series en el tiempo** | 7 series de UAECOB, DAILoc y UAESP, cada una en su ventana temporal nativa y con los cortes parciales advertidos |

### 🏛️ Recomendaciones de política pública (pipeline original — sujetas a los matices de la sección 7)

1. **Rebalanceo de mobiliario (UAESP):** instalar cestas y contenedores adicionales en las UPZ con mayor índice de vulnerabilidad compuesta (ver ranking territorial en el informe final).
2. **Estrategia interinstitucional en puntos críticos** (Secretaría de Seguridad + MEBOG + UAESP): dado que el arrojo clandestino no se explica por déficit de infraestructura, cualquier intervención debería considerar el estrato como variable subyacente compartida.
3. **Prevención comunitaria con enfoque de género** (UAECOB + Secretaría de la Mujer) en zonas de alta vulnerabilidad.

---

## 🔗 Enlace de datos crudos

`data/bronze/` (15 fuentes, ~295 MB) no está versionado en git — descárgalo aquí:

> **Nota:** la carpeta de Drive incluye además el geodatabase catastral de IDECA (`gdb_mr_v06_26.gdb`, ~1.7 GB) y otras capas exploratorias que **no** consume ninguna fase del pipeline. No es necesario descargarlas para reproducir el análisis.

[Google Drive — Datos crudos del proyecto](https://drive.google.com/drive/folders/1jQZh3PLFPnMqk9hLOA2zVPJMGfBdlYMB?usp=drive_link)
