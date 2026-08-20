"""
Fase 6 (complemento) — Dataset UPZ x Año literal + datasets por hipótesis
DataJam Bogotá 2026

agent.md pide explícitamente:
- gold/modelos/dataset_hipotesis.parquet con estructura UPZ x Año
- gold/modelos/hypothesis_h1..h5.parquet, features_delitos.parquet, features_emergencias.parquet

IMPORTANTE (ya documentado en 09_espacio_temporal y en el informe): de las variables
UPZ, SOLO n_incidentes/n_incendios/n_rescates/n_emerg_ambiental/estrato_promedio_reportado
se midieron realmente año a año (2016-2020, fuente UAECOB). El resto (aseo, arrojo,
policía, bomberos) son snapshots actuales sin historia -- aquí se REPLICAN por año
para cumplir la estructura pedida, marcadas explícitamente con el prefijo `snap_`
para que nadie las use como si variaran en el tiempo por error.
"""
import os
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)

master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))
emerg_upz_anio = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))

# ══════════════════════════════════════════════════════════════════
# dataset_hipotesis.parquet -- UPZ x Año (2016-2020, único rango con panel real)
# ══════════════════════════════════════════════════════════════════
COLS_ESTATICAS = ['area_km2', 'n_cestas', 'n_contenedores', 'densidad_cestas_km2',
                   'densidad_contenedores_km2', 'cobertura_macrorutas_pct',
                   'deficit_aseo_relativo', 'n_puntos_criticos', 'densidad_puntos_criticos_km2',
                   'estrato_promedio_oficial', 'estrato_modal_oficial',
                   'n_cuadrantes', 'densidad_cuadrantes_km2', 'dist_estacion_bomberos_m',
                   'n_estaciones_bomberos_5km']

anios = sorted(emerg_upz_anio['anio'].unique())
base_estatica = master_upz[['cod_upz', 'nombre_upz'] + COLS_ESTATICAS].copy()
base_estatica.columns = ['cod_upz', 'nombre_upz'] + [f'snap_{c}' for c in COLS_ESTATICAS]

panel = pd.concat([base_estatica.assign(anio=a) for a in anios], ignore_index=True)
panel = panel.merge(emerg_upz_anio, on=['cod_upz', 'anio'], how='left')
for c in ['n_incidentes', 'n_incendios', 'n_rescates', 'n_emerg_ambiental']:
    panel[c] = panel[c].fillna(0)
panel['densidad_incidentes_km2'] = (panel['n_incidentes'] / panel['snap_area_km2']).round(2)

panel.to_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis.parquet'), index=False)
print(f"dataset_hipotesis.parquet (UPZ x Año): {panel.shape} | años: {anios}")
print(f"Columnas 'snap_*' = infraestructura estática (sin serie temporal real), no varían por año.")

# ══════════════════════════════════════════════════════════════════
# Datasets por hipótesis (solo variables + controles relevantes de cada una)
# ══════════════════════════════════════════════════════════════════
h1 = master_upz[['cod_upz', 'nombre_upz', 'estrato_promedio_oficial', 'estrato_promedio_reportado', 'deficit_aseo_relativo', 'area_km2']].copy()
h1.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h1.parquet'), index=False)

h2 = master_upz[['cod_upz', 'nombre_upz', 'deficit_aseo_relativo', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                  'n_puntos_criticos', 'densidad_puntos_criticos_km2', 'area_km2']].copy()
h2.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h2.parquet'), index=False)

h3 = master_upz[['cod_upz', 'nombre_upz', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                  'n_puntos_criticos', 'densidad_puntos_criticos_km2', 'area_km2']].copy()
h3.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h3.parquet'), index=False)

h4 = master_loc[['cod_localidad', 'nombre_localidad', 'n_puntos_criticos', 'densidad_puntos_criticos_km2',
                  'homicidios_cont', 'homicidios_total_oficial', 'densidad_homicidios_km2',
                  'deficit_aseo_relativo', 'estrato_promedio_oficial', 'estrato_promedio_reportado', 'n_cuadrantes', 'area_km2']].copy()
h4.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h4.parquet'), index=False)

h5 = master_upz[['cod_upz', 'nombre_upz', 'n_puntos_criticos', 'densidad_puntos_criticos_km2',
                  'n_incidentes_total', 'densidad_incidentes_km2', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                  'dist_estacion_bomberos_m', 'area_km2']].copy()
h5.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h5.parquet'), index=False)

h6 = master_loc[['cod_localidad', 'nombre_localidad', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                  'homicidios_cont', 'densidad_homicidios_km2', 'delitos_alto_impacto_cont', 'area_km2']].copy()
h6.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h6.parquet'), index=False)

h7 = master_upz[['cod_upz', 'nombre_upz', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                  'n_incidentes_total', 'densidad_incidentes_km2', 'area_km2']].copy()
h7.to_parquet(os.path.join(GOLD, 'modelos', 'hypothesis_h7.parquet'), index=False)

features_delitos = master_loc[['cod_localidad', 'nombre_localidad', 'homicidios_cont', 'homicidios_total_oficial',
                                'violencia_intrafamiliar_cont', 'violencia_intrafamiliar_total_oficial',
                                'delitos_alto_impacto_cont', 'densidad_homicidios_km2', 'estrato_promedio_oficial', 'estrato_promedio_reportado',
                                'deficit_aseo_relativo', 'n_puntos_criticos', 'n_cuadrantes', 'area_km2']].copy()
features_delitos.to_parquet(os.path.join(GOLD, 'modelos', 'features_delitos.parquet'), index=False)

features_emergencias = master_upz[['cod_upz', 'nombre_upz', 'n_incidentes_total', 'n_incendios',
                                    'densidad_incidentes_km2', 'n_ninas_expuestas', 'n_ninos_expuestos',
                                    'estrato_promedio_oficial', 'estrato_promedio_reportado', 'n_puntos_criticos',
                                    'dist_estacion_bomberos_m', 'area_km2']].copy()
features_emergencias.to_parquet(os.path.join(GOLD, 'modelos', 'features_emergencias.parquet'), index=False)

print("\n✅ 7 datasets por hipótesis (h1-h7) + features_delitos + features_emergencias guardados en data/gold/modelos/")
