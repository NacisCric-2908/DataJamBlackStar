"""
Fase 6 (complemento) — Completar subcarpetas Gold vacías
DataJam Bogotá 2026

agent.md pide explícitamente gold/{dimensiones,accesibilidad,espacio_temporal,
socioeconomico}/ como parte de la estructura Medallion. Estaban creadas pero
vacías -- se llenan aquí con contenido real (no archivos placeholder).
"""
import os
import pandas as pd
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)

# ══════════════════════════════════════════════════════════════════
# dimensiones/ — tablas de dimensión territorial (sin métricas, solo identificadores+geometría)
# ══════════════════════════════════════════════════════════════════
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet'))
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet'))
gdf_upz.to_parquet(os.path.join(GOLD, 'dimensiones', 'dim_upz.parquet'), index=False)
gdf_loc.to_parquet(os.path.join(GOLD, 'dimensiones', 'dim_localidad.parquet'), index=False)
print(f"dimensiones/: dim_upz ({len(gdf_upz)}), dim_localidad ({len(gdf_loc)})")

# ══════════════════════════════════════════════════════════════════
# accesibilidad/ — cuadrantes de policía + estaciones de bomberos consolidados
# ══════════════════════════════════════════════════════════════════
master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

acc_upz = master_upz[['cod_upz', 'nombre_upz', 'n_cuadrantes', 'densidad_cuadrantes_km2',
                       'dist_estacion_bomberos_m', 'n_estaciones_bomberos_5km']].copy()
acc_loc = master_loc[['cod_localidad', 'nombre_localidad', 'n_cuadrantes', 'densidad_cuadrantes_km2',
                       'dist_estacion_bomberos_m', 'n_estaciones_bomberos_5km']].copy()
acc_upz.to_parquet(os.path.join(GOLD, 'accesibilidad', 'accesibilidad_upz.parquet'), index=False)
acc_loc.to_parquet(os.path.join(GOLD, 'accesibilidad', 'accesibilidad_localidad.parquet'), index=False)
print(f"accesibilidad/: {acc_upz.shape}, {acc_loc.shape}")

# ══════════════════════════════════════════════════════════════════
# espacio_temporal/ — resúmenes de Fase 11
# ══════════════════════════════════════════════════════════════════
FASE11 = os.path.join(BASE, 'scripts', '11_espacio_temporal')
tend = pd.read_csv(os.path.join(FASE11, 'tendencias_uaecob_upz.csv'))
resumen = pd.read_csv(os.path.join(FASE11, 'resumen_espacio_temporal.csv'))
tend.to_parquet(os.path.join(GOLD, 'espacio_temporal', 'tendencias_uaecob_upz.parquet'), index=False)
resumen.to_parquet(os.path.join(GOLD, 'espacio_temporal', 'resumen_cobertura_temporal.parquet'), index=False)
print(f"espacio_temporal/: tendencias ({len(tend)} UPZ), resumen ({len(resumen)} fuentes)")

# ══════════════════════════════════════════════════════════════════
# socioeconomico/ — estrato OFICIAL (manzana) como variable principal + proxy para comparación
# ══════════════════════════════════════════════════════════════════
dist = pd.read_parquet(os.path.join(SILVER, 'socioeconomico', 'distribucion_estrato_citywide.parquet'))
dist.to_parquet(os.path.join(GOLD, 'socioeconomico', 'distribucion_estrato_citywide.parquet'), index=False)

oficial_upz = master_upz[['cod_upz', 'nombre_upz', 'estrato_promedio_oficial', 'estrato_modal_oficial',
                            'pct_estrato_1_2_oficial', 'pct_estrato_5_6_oficial', 'n_manzanas']].copy()
oficial_loc = master_loc[['cod_localidad', 'nombre_localidad', 'estrato_promedio_oficial', 'estrato_modal_oficial',
                            'pct_estrato_1_2_oficial', 'pct_estrato_5_6_oficial', 'n_manzanas']].copy()
oficial_upz.to_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_oficial_upz.parquet'), index=False)
oficial_loc.to_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_oficial_localidad.parquet'), index=False)

proxy_upz = master_upz[['cod_upz', 'nombre_upz', 'estrato_promedio_reportado', 'estrato_modal_reportado']].copy()
proxy_loc = master_loc[['cod_localidad', 'nombre_localidad', 'estrato_promedio_reportado', 'estrato_modal_reportado']].copy()
proxy_upz.to_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_proxy_upz.parquet'), index=False)
proxy_loc.to_parquet(os.path.join(GOLD, 'socioeconomico', 'estrato_proxy_localidad.parquet'), index=False)
print(f"socioeconomico/: distribución citywide ({len(dist)} estratos) + estrato OFICIAL (manzana, principal) "
      f"+ proxy UPZ/localidad (autorreportado UAECOB, solo para comparación, r=0.96 con el oficial)")

print("\n✅ Las 4 subcarpetas Gold quedaron completas: dimensiones, accesibilidad, espacio_temporal, socioeconomico.")

# ══════════════════════════════════════════════════════════════════
# aseo/ — infraestructura formal, déficit y arrojo clandestino (también vacía)
# ══════════════════════════════════════════════════════════════════
COLS_ASEO_UPZ = ['cod_upz', 'nombre_upz', 'n_cestas', 'n_contenedores', 'densidad_cestas_km2',
                  'densidad_contenedores_km2', 'cobertura_macrorutas_pct', 'deficit_aseo_relativo',
                  'n_puntos_criticos', 'densidad_puntos_criticos_km2']
COLS_ASEO_LOC = ['cod_localidad', 'nombre_localidad', 'n_cestas', 'n_contenedores', 'densidad_cestas_km2',
                  'densidad_contenedores_km2', 'deficit_aseo_relativo', 'n_puntos_criticos', 'densidad_puntos_criticos_km2']

master_upz[COLS_ASEO_UPZ].to_parquet(os.path.join(GOLD, 'aseo', 'aseo_arrojo_upz.parquet'), index=False)
master_loc[COLS_ASEO_LOC].to_parquet(os.path.join(GOLD, 'aseo', 'aseo_arrojo_localidad.parquet'), index=False)

rbl = pd.read_parquet(os.path.join(SILVER, 'aseo', 'rbl_series.parquet'))
rbl.to_parquet(os.path.join(GOLD, 'aseo', 'rbl_series_por_ase.parquet'), index=False)
print(f"aseo/: aseo_arrojo_upz {master_upz[COLS_ASEO_UPZ].shape}, aseo_arrojo_localidad {master_loc[COLS_ASEO_LOC].shape}, rbl_series_por_ase {rbl.shape}")
