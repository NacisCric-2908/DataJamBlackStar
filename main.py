#!/usr/bin/env python3
"""
==============================================================================
🏙️ DataJam Bogotá 2026 — Orquestador Principal del Pipeline de Datos
==============================================================================
Ejecuta de manera secuencial y reproducible todas las fases del pipeline analítico:
  01. Ingesta (Catálogo de fuentes Bronze)
  02. Auditoría de Calidad de Datos (16 chequeos + estrato oficial)
  03. Normalización y Limpieza -> Silver (Territorio, Aseo, Bomberos, Policía, Delitos, RBL, Estratos, Población)
  05. Integración Espacial (Spatial Joins & Análisis de Proximidad)
  06. Construcción de Variables -> Gold (Dataset Maestro, Panel UPZ-Año, Diccionario, Ranking)
  07. Análisis Exploratorio de Datos (EDA Notebook)
  08. Pruebas Estadísticas (Normalidad & Correlación FDR)
  09. Estadística Espacial (Moran's I, LISA, Getis-Ord Gi*, Pesos Espaciales)
  10. Modelos Multivariables (GLM Binomial Negativa con control de confusores)
  11. Análisis Espacio-Temporal (Tendencias y persistencia)
  12. Validación y Robustez (MAUP, Especificaciones, Períodos temporales)
  13. Visualización y Mapas Finales (Notebook de mapas espaciales)
  15. Exportación de Capa de Consumo para Dashboard

Uso:
  python main.py                  # Ejecuta todo el pipeline completo
  python main.py --skip-notebooks # Ejecuta solo scripts ETL y estadísticos (rápido)
  python main.py --phases 1 2 3   # Ejecuta fases específicas
==============================================================================
"""

import sys
import os
import time
import argparse
import subprocess
from pathlib import Path

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Definición de todas las tareas del pipeline en orden estricto de precedencia
PIPELINE_STEPS = [
    # (Fase_id, Nombre descriptivo, tipo, ruta_relativa)
    (1, "Ingesta — Catálogo de Fuentes Bronze", "script", "scripts/01_ingesta/01_catalogo_fuentes.py"),
    (2, "Auditoría — Chequeos de Calidad de Datos", "script", "scripts/02_auditoria/01_auditoria_datos.py"),
    (2, "Auditoría — Estratificación Oficial SDP", "script", "scripts/02_auditoria/02_auditoria_estrato_oficial.py"),
    (3, "Limpieza Silver — Territorio, Aseo, Bomberos, Policía, Delitos", "script", "scripts/03_limpieza/04_normalizacion_silver.py"),
    (3, "Limpieza Silver — Emergencias UAECOB", "script", "scripts/03_limpieza/05_normalizacion_emergencias.py"),
    (3, "Limpieza Silver — Residuos RBL (2021-2026)", "script", "scripts/03_limpieza/06_normalizacion_rbl.py"),
    (3, "Limpieza Silver — Estratificación Catastral (Esoc)", "script", "scripts/03_limpieza/07_normalizacion_socioeconomico.py"),
    (3, "Limpieza Silver — Estratificación Oficial Manzanas SDP", "script", "scripts/03_limpieza/08_normalizacion_estrato_oficial.py"),
    (3, "Limpieza Silver — Población oficial por UPZ y localidad (DANE/SDP)", "script", "scripts/03_limpieza/09_normalizacion_poblacion.py"),
    (5, "Integración Espacial — Spatial Joins UPZ & Localidades", "script", "scripts/05_integracion_espacial/01_spatial_joins.py"),
    (5, "Integración Espacial — Análisis de Proximidad a Infraestructura", "script", "scripts/05_integracion_espacial/02_analisis_proximidad.py"),
    (6, "Construcción Variables — Dataset Maestro Gold", "script", "scripts/06_construccion_variables/01_dataset_maestro.py"),
    (6, "Construcción Variables — Panel UPZ×Año & Datasets de Hipótesis", "script", "scripts/06_construccion_variables/02_dataset_upz_anio_e_hipotesis.py"),
    (6, "Construcción Variables — Diccionario de Datos Gold", "script", "scripts/06_construccion_variables/03_data_dictionary.py"),
    (6, "Construcción Variables — Subcarpetas Temáticas Gold", "script", "scripts/06_construccion_variables/04_completar_gold_subcarpetas.py"),
    (6, "Construcción Variables — Ranking Territorial de Vulnerabilidad", "script", "scripts/06_construccion_variables/05_ranking_territorial.py"),
    (7, "EDA — Análisis Exploratorio (Notebook)", "notebook", "notebooks/01_eda_dataset_maestro.ipynb"),
    (8, "Estadística — Pruebas de Normalidad & Correlación con FDR", "script", "scripts/08_estadistica/01_pruebas_estadisticas.py"),
    (9, "Estadística Espacial — Moran's I, LISA & Getis-Ord Gi*", "script", "scripts/09_estadistica_espacial/01_moran_lisa_getis.py"),
    (9, "Estadística Espacial — Matrices de Pesos Espaciales (Queen/KNN)", "script", "scripts/09_estadistica_espacial/02_guardar_pesos_espaciales.py"),
    (10, "Modelado — Modelos Multivariables Poisson & Binomial Negativa", "script", "scripts/10_modelos/01_modelos_multivariables.py"),
    (11, "Espacio-Temporal — Análisis de Series & Persistencia Territorial", "script", "scripts/11_espacio_temporal/01_analisis_temporal.py"),
    (12, "Validación — Robustez Territorial (MAUP) & Especificaciones", "script", "scripts/12_validacion/01_robustez.py"),
    (12, "Validación — Robustez por Períodos Temporales", "script", "scripts/12_validacion/02_robustez_periodos.py"),
    (13, "Visualización — Mapas Espaciales Finales (Notebook)", "notebook", "notebooks/02_mapas_finales.ipynb"),
    (15, "Dashboard Export — Dimensiones", "script", "scripts/15_dashboard_export/01_dimensions.py"),
    (15, "Dashboard Export — Indicadores Territoriales", "script", "scripts/15_dashboard_export/02_indicators.py"),
    (15, "Dashboard Export — Capas Geoespaciales", "script", "scripts/15_dashboard_export/03_spatial.py"),
    (15, "Dashboard Export — Series Temporales", "script", "scripts/15_dashboard_export/04_temporal.py"),
    (15, "Dashboard Export — Resultados de Hipótesis", "script", "scripts/15_dashboard_export/05_hypotheses.py"),
    (15, "Dashboard Export — Validación de Integridad de la Capa", "script", "scripts/15_dashboard_export/06_metadata_and_validation.py"),
]



def ensure_directories():
    """Garantiza que todas las carpetas del pipeline existan antes de ejecutar."""
    dirs = [
        BASE_DIR / 'data' / 'bronze',
        BASE_DIR / 'data' / 'silver' / 'territorio',
        BASE_DIR / 'data' / 'silver' / 'aseo',
        BASE_DIR / 'data' / 'silver' / 'policia',
        BASE_DIR / 'data' / 'silver' / 'bomberos',
        BASE_DIR / 'data' / 'silver' / 'seguridad',
        BASE_DIR / 'data' / 'silver' / 'emergencias',
        BASE_DIR / 'data' / 'silver' / 'socioeconomico',
        BASE_DIR / 'data' / 'silver' / 'poblacion',
        BASE_DIR / 'data' / 'gold' / 'dimensiones',
        BASE_DIR / 'data' / 'gold' / 'aseo',
        BASE_DIR / 'data' / 'gold' / 'emergencias',
        BASE_DIR / 'data' / 'gold' / 'seguridad',
        BASE_DIR / 'data' / 'gold' / 'socioeconomico',
        BASE_DIR / 'data' / 'gold' / 'accesibilidad',
        BASE_DIR / 'data' / 'gold' / 'espacio_temporal',
        BASE_DIR / 'data' / 'gold' / 'estadistica_espacial' / 'moran_local',
        BASE_DIR / 'data' / 'gold' / 'estadistica_espacial' / 'hotspots_gistar',
        BASE_DIR / 'data' / 'gold' / 'estadistica_espacial' / 'pesos',
        BASE_DIR / 'data' / 'gold' / 'modelos',
        BASE_DIR / 'data' / 'dashboard' / 'dimensions',
        BASE_DIR / 'data' / 'dashboard' / 'indicators',
        BASE_DIR / 'data' / 'dashboard' / 'spatial',
        BASE_DIR / 'data' / 'dashboard' / 'temporal',
        BASE_DIR / 'data' / 'dashboard' / 'hypotheses',
        BASE_DIR / 'data' / 'dashboard' / 'metadata',
        BASE_DIR / 'outputs' / 'figures',
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def run_script(rel_path: str) -> bool:
    """Ejecuta un script Python en un subproceso usando el intérprete actual."""
    full_path = BASE_DIR / rel_path
    if not full_path.exists():
        print(f"❌ Error: Archivo no encontrado: {full_path}")
        return False
    
    cmd = [sys.executable, str(full_path)]
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    return result.returncode == 0


def run_notebook(rel_path: str) -> bool:
    """Ejecuta un Jupyter Notebook in-place usando nbconvert."""
    full_path = BASE_DIR / rel_path
    if not full_path.exists():
        print(f"❌ Error: Notebook no encontrado: {full_path}")
        return False
    
    cmd = [
        sys.executable, "-m", "jupyter", "nbconvert",
        "--to", "notebook",
        "--execute",
        "--inplace",
        "--ExecutePreprocessor.timeout=600",
        "--ExecutePreprocessor.kernel_name=python3",
        str(full_path)
    ]
    result = subprocess.run(cmd, cwd=str(BASE_DIR))
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="🏙️ Orquestador del Pipeline Reproducible — DataJam Bogotá 2026"
    )
    parser.add_argument(
        "--phases", nargs="+", type=int, default=None,
        help="Fases específicas a ejecutar (ej. --phases 1 2 3)"
    )
    parser.add_argument(
        "--skip-notebooks", action="store_true",
        help="Omitir la ejecución de Jupyter Notebooks (EDA y Mapas Finales)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 INICIANDO PIPELINE DE CIENCIA DE DATOS — DATAJAM BOGOTÁ 2026")
    print(f"📁 Directorio base: {BASE_DIR}")
    print(f"🐍 Intérprete Python: {sys.executable}")
    ensure_directories()
    print("=" * 80)

    # Filtrar pasos según argumentos
    steps_to_run = []
    for phase_id, name, stype, rel_path in PIPELINE_STEPS:
        if args.phases and phase_id not in args.phases:
            continue
        if args.skip_notebooks and stype == "notebook":
            continue
        steps_to_run.append((phase_id, name, stype, rel_path))

    if not steps_to_run:
        print("⚠️ No hay tareas seleccionadas para ejecutar.")
        sys.exit(0)

    start_total = time.time()
    successful = 0

    for idx, (phase_id, name, stype, rel_path) in enumerate(steps_to_run, 1):
        print(f"\n[{idx}/{len(steps_to_run)}] ⏳ Fase {phase_id:02d} — {name} ({stype.upper()})")
        print(f"      Ruta: {rel_path}")
        t0 = time.time()

        if stype == "script":
            ok = run_script(rel_path)
        elif stype == "notebook":
            ok = run_notebook(rel_path)
        else:
            print(f"❌ Tipo desconocido: {stype}")
            ok = False

        elapsed = time.time() - t0
        if ok:
            print(f"      ✅ Completado exitosamente en {elapsed:.2f}s")
            successful += 1
        else:
            print(f"      ❌ ERROR en Fase {phase_id:02d} ({rel_path}) tras {elapsed:.2f}s")
            print("\n❌ Pipeline interrumpido debido a un error.")
            sys.exit(1)

    total_time = time.time() - start_total
    print("\n" + "=" * 80)
    print(f"🎉 PIPELINE COMPLETADO EXITOSAMENTE — {successful}/{len(steps_to_run)} tareas")
    print(f"⏱️ Tiempo total de ejecución: {total_time:.2f} segundos ({total_time/60:.2f} minutos)")
    print("=" * 80)
    print("📂 Entregables generados:")
    print("  - Tablas Maestras y Modelos: data/gold/")
    print("  - Capa de Consumo Dashboard: data/dashboard/")
    print("  - Figuras y Mapas:          outputs/figures/")
    print("  - Informes Técnicos:         docs/informe_final.md")
    print("=" * 80)


if __name__ == "__main__":
    main()
