"""
agent2.md — Fase 8-14: indicators/
DataJam Bogotá 2026

Regla seguida estrictamente: si un campo pedido por agent2.md no existe ya
calculado y validado, se OMITE del CSV (no se rellena con 0 ni se aproxima).
Todos los campos omitidos quedan documentados en metadata/data_dictionary.csv
como NOT_AVAILABLE_YET, con el motivo.

Campos pedidos por agent2.md que NO existen en el proyecto (omitidos aquí,
documentados en 06_metadata_and_validation.py):
- population, population_density, population_stratum_1_2 -> ninguna de las
  14 fuentes trae población oficial por UPZ/localidad.
- *_per_100k (cestas, containers, critical_points, crimes, emergencies) ->
  requieren población, no disponible.
- pct_stratum_1 / pct_stratum_2 por separado -> solo existe la combinada
  pct_estrato_1_2_oficial (agregada así desde el spatial join de manzanas).
- high_impact_crimes / crimes_per_km2 A NIVEL UPZ -> DAILoc (la única fuente
  de delitos) NUNCA trae UPZ, solo localidad. No se puede calcular sin
  inventar un supuesto de reparto espacial.
- critical_points.persistence -> nunca se calculó una métrica de persistencia
  temporal de puntos críticos (la fuente es un snapshot sin fecha).
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.join(BASE, 'data', 'dashboard')

dim_upz = pd.read_csv(os.path.join(OUT, 'dimensions', 'upz.csv'), dtype={'localidad_id': str})
dim_loc = pd.read_csv(os.path.join(OUT, 'dimensions', 'localidades.csv'), dtype={'localidad_id': str})

aseo_upz = pd.read_parquet(os.path.join(GOLD, 'aseo', 'aseo_arrojo_upz.parquet'))
aseo_loc = pd.read_parquet(os.path.join(GOLD, 'aseo', 'aseo_arrojo_localidad.parquet'))
estrato_upz = pd.read_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_oficial_upz.parquet'))
estrato_loc = pd.read_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_oficial_localidad.parquet'))
emerg_upz_anio = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))
delitos_loc = pd.read_parquet(os.path.join(BASE, 'data', 'silver', 'seguridad', 'delitos_localidad.parquet')).drop(columns='geometry', errors='ignore')
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

# ══════════════════════════════════════════════════════════════════
# indicators/upz_year.csv — UNA FILA = UPZ x AÑO
# Solo 2016-2020 tiene panel UPZ x año real (emergencias, vía UAECOB).
# Las columnas de infraestructura/arrojo/estrato son snapshot (repetidas por
# año) -- documentado explícitamente en data_dictionary.csv (temporal_granularity).
# ══════════════════════════════════════════════════════════════════
anios_upz = sorted(emerg_upz_anio['anio'].unique())
snap_upz = dim_upz.merge(aseo_upz, left_on='upz_id', right_on='cod_upz', how='left') \
                   .merge(estrato_upz[['cod_upz', 'pct_estrato_1_2_oficial']], on='cod_upz', how='left')

filas_upz_year = []
for anio in anios_upz:
    base = snap_upz.copy()
    base['year'] = anio
    filas_upz_year.append(base)
upz_year = pd.concat(filas_upz_year, ignore_index=True)
upz_year = upz_year.merge(emerg_upz_anio, left_on=['upz_id', 'year'], right_on=['cod_upz', 'anio'], how='left')

upz_year['emergencies'] = upz_year['n_incidentes'].fillna(0)
upz_year['emergencies_per_km2'] = (upz_year['emergencies'] / upz_year['area_km2']).round(2)

upz_year_out = upz_year.rename(columns={
    'n_cestas': 'cestas', 'densidad_cestas_km2': 'cestas_per_km2',
    'n_contenedores': 'containers', 'densidad_contenedores_km2': 'containers_per_km2',
    'cobertura_macrorutas_pct': 'sweeping_route_coverage',
    'n_puntos_criticos': 'critical_points', 'densidad_puntos_criticos_km2': 'critical_points_per_km2',
    'pct_estrato_1_2_oficial': 'pct_stratum_1_2',
})[['year', 'upz_id', 'upz_nombre', 'localidad_id', 'localidad_nombre',
    'pct_stratum_1_2', 'cestas', 'cestas_per_km2', 'containers', 'containers_per_km2',
    'sweeping_route_coverage', 'critical_points', 'critical_points_per_km2',
    'emergencies', 'emergencies_per_km2']]
upz_year_out.to_csv(os.path.join(OUT, 'indicators', 'upz_year.csv'), index=False)
print(f"indicators/upz_year.csv: {upz_year_out.shape} (años {anios_upz}, infra=snapshot repetido)")

# ══════════════════════════════════════════════════════════════════
# indicators/vulnerability.csv — snapshot (sin year, fecha de captura documentada)
# ══════════════════════════════════════════════════════════════════
vuln_upz = dim_upz[['upz_id', 'upz_nombre', 'localidad_id', 'localidad_nombre']].merge(
    estrato_upz.rename(columns={'cod_upz': 'upz_id', 'estrato_promedio_oficial': 'stratum_avg',
                                  'estrato_modal_oficial': 'stratum_mode',
                                  'pct_estrato_1_2_oficial': 'pct_stratum_1_2',
                                  'pct_estrato_5_6_oficial': 'pct_stratum_5_6'})[
        ['upz_id', 'stratum_avg', 'stratum_mode', 'pct_stratum_1_2', 'pct_stratum_5_6']],
    on='upz_id', how='left')
vuln_upz.to_csv(os.path.join(OUT, 'indicators', 'vulnerability.csv'), index=False)
print(f"indicators/vulnerability.csv: {vuln_upz.shape} (snapshot, sin dimensión temporal)")

# ══════════════════════════════════════════════════════════════════
# indicators/waste_infrastructure.csv — UPZ y Localidad, snapshot
# ══════════════════════════════════════════════════════════════════
waste_upz = dim_upz.merge(aseo_upz.rename(columns={
    'cod_upz': 'upz_id', 'n_cestas': 'cestas', 'densidad_cestas_km2': 'cestas_per_km2',
    'n_contenedores': 'containers', 'densidad_contenedores_km2': 'containers_per_km2',
    'cobertura_macrorutas_pct': 'sweeping_route_coverage'}),
    on='upz_id', how='left')[['upz_id', 'upz_nombre', 'localidad_id', 'localidad_nombre',
                                'cestas', 'cestas_per_km2', 'containers', 'containers_per_km2',
                                'sweeping_route_coverage']]
waste_upz.to_csv(os.path.join(OUT, 'indicators', 'waste_infrastructure_upz.csv'), index=False)

waste_loc = dim_loc.merge(aseo_loc.rename(columns={
    'cod_localidad': 'localidad_id', 'n_cestas': 'cestas', 'densidad_cestas_km2': 'cestas_per_km2',
    'n_contenedores': 'containers', 'densidad_contenedores_km2': 'containers_per_km2'}),
    on='localidad_id', how='left')[['localidad_id', 'localidad_nombre', 'cestas', 'cestas_per_km2',
                                      'containers', 'containers_per_km2']]
waste_loc.to_csv(os.path.join(OUT, 'indicators', 'waste_infrastructure_localidad.csv'), index=False)
print(f"indicators/waste_infrastructure_{{upz,localidad}}.csv: {waste_upz.shape}, {waste_loc.shape} (snapshot)")

# ══════════════════════════════════════════════════════════════════
# indicators/critical_points.csv — UPZ y Localidad, snapshot (sin persistence)
# ══════════════════════════════════════════════════════════════════
cp_upz = dim_upz.merge(aseo_upz.rename(columns={'cod_upz': 'upz_id', 'n_puntos_criticos': 'critical_points',
                                                  'densidad_puntos_criticos_km2': 'critical_points_per_km2'}),
                        on='upz_id', how='left')[['upz_id', 'upz_nombre', 'localidad_id', 'localidad_nombre',
                                                    'critical_points', 'critical_points_per_km2']]
cp_upz.to_csv(os.path.join(OUT, 'indicators', 'critical_points_upz.csv'), index=False)

cp_loc = dim_loc.merge(aseo_loc.rename(columns={'cod_localidad': 'localidad_id', 'n_puntos_criticos': 'critical_points',
                                                  'densidad_puntos_criticos_km2': 'critical_points_per_km2'}),
                        on='localidad_id', how='left')[['localidad_id', 'localidad_nombre',
                                                          'critical_points', 'critical_points_per_km2']]
cp_loc.to_csv(os.path.join(OUT, 'indicators', 'critical_points_localidad.csv'), index=False)
print(f"indicators/critical_points_{{upz,localidad}}.csv: {cp_upz.shape}, {cp_loc.shape} (snapshot, sin persistence)")

# ══════════════════════════════════════════════════════════════════
# indicators/crime.csv — SOLO Localidad (DAILoc nunca trae UPZ)
# ══════════════════════════════════════════════════════════════════
crime_wide = dim_loc.merge(delitos_loc.rename(columns={'cod_localidad': 'localidad_id'}), on='localidad_id', how='left')
crime_wide = crime_wide.rename(columns={
    'delitos_alto_impacto_cont': 'high_impact_crimes'})
crime_wide['crimes_per_km2'] = (crime_wide['high_impact_crimes'] / crime_wide['area_km2']).round(2)
crime_wide[['localidad_id', 'localidad_nombre', 'high_impact_crimes', 'crimes_per_km2']].to_csv(
    os.path.join(OUT, 'indicators', 'crime_localidad.csv'), index=False)

# categorías (cross-sectional, 2018-2026 combinado -- CONT del propio DAILoc)
cats = ['homicidios_cont', 'hurto_personas_cont', 'hurto_residencias_cont', 'hurto_comercio_cont',
        'lesiones_personales_cont', 'delitos_sexuales_cont', 'violencia_intrafamiliar_cont']
crime_long = crime_wide[['localidad_id', 'localidad_nombre'] + cats].melt(
    id_vars=['localidad_id', 'localidad_nombre'], var_name='crime_category', value_name='crime_count')
crime_long['crime_category'] = crime_long['crime_category'].str.replace('_cont', '')
crime_long.to_csv(os.path.join(OUT, 'indicators', 'crime_categories_localidad.csv'), index=False)
print(f"indicators/crime_localidad.csv + crime_categories_localidad.csv: solo nivel localidad, cross-sectional 2018-2026")

# ══════════════════════════════════════════════════════════════════
# indicators/emergencies.csv — UPZ x año (real, 2016-2020) + Localidad (snapshot total)
# ══════════════════════════════════════════════════════════════════
emerg_upz_out = dim_upz.merge(emerg_upz_anio, left_on='upz_id', right_on='cod_upz', how='inner')
emerg_upz_out['emergencies_per_km2'] = (emerg_upz_out['n_incidentes'] / emerg_upz_out['area_km2']).round(2)
emerg_upz_out = emerg_upz_out.rename(columns={'anio': 'year', 'n_incidentes': 'emergencies',
                                                'n_incendios': 'fires', 'n_rescates': 'rescues',
                                                'n_emerg_ambiental': 'environmental_emergencies'})
emerg_upz_out[['year', 'upz_id', 'upz_nombre', 'localidad_id', 'localidad_nombre',
               'emergencies', 'emergencies_per_km2', 'fires', 'rescues', 'environmental_emergencies']].to_csv(
    os.path.join(OUT, 'indicators', 'emergencies_upz_year.csv'), index=False)

emerg_loc_out = dim_loc.merge(master_loc.drop(columns=['area_km2']).rename(columns={'cod_localidad': 'localidad_id',
                                                            'n_incidentes_total': 'emergencies', 'n_incendios': 'fires'}),
                               on='localidad_id', how='left')
emerg_loc_out['emergencies_per_km2'] = (emerg_loc_out['emergencies'] / emerg_loc_out['area_km2']).round(2)
emerg_loc_out[['localidad_id', 'localidad_nombre', 'emergencies', 'emergencies_per_km2', 'fires']].to_csv(
    os.path.join(OUT, 'indicators', 'emergencies_localidad_snapshot.csv'), index=False)
print(f"indicators/emergencies_upz_year.csv (real, 2016-2020) + emergencies_localidad_snapshot.csv (total, sin year)")

print("\n✅ indicators/ completo.")
