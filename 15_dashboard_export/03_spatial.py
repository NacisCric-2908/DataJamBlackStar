"""
agent2.md — Fase 12, 17-19: spatial/
DataJam Bogotá 2026
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.join(BASE, 'data', 'dashboard')

dim_upz_geo = gpd.read_parquet(os.path.join(GOLD, 'dimensiones', 'dim_upz.parquet'))
dim_loc_geo = gpd.read_parquet(os.path.join(GOLD, 'dimensiones', 'dim_localidad.parquet'))

# ══════════════════════════════════════════════════════════════════
# spatial/critical_points_locations.csv — coordenadas reales, sin fecha
# (la fuente no trae fecha por punto -> "year" NOT_AVAILABLE, se omite).
# UPZ/localidad asignadas con la misma técnica de spatial join ya validada
# (05_integracion_espacial/01_spatial_joins.py), no una técnica nueva.
# ══════════════════════════════════════════════════════════════════
gdf_pc = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'puntos_criticos.parquet')).drop(columns=['cod_localidad'])
sj_upz = gpd.sjoin(gdf_pc, dim_upz_geo[['cod_upz', 'nombre_upz', 'geometry']], how='left', predicate='within')
sj_loc = gpd.sjoin(gdf_pc, dim_loc_geo[['cod_localidad', 'nombre_localidad', 'geometry']], how='left', predicate='within')

pc_out = pd.DataFrame({
    'point_id': gdf_pc['OBJECTID'],
    'latitude': gdf_pc.geometry.y,
    'longitude': gdf_pc.geometry.x,
    'upz_id': sj_upz['cod_upz'].values,
    'upz_nombre': sj_upz['nombre_upz'].values,
    'localidad_id': sj_loc['cod_localidad'].values,
    'localidad_nombre': sj_loc['nombre_localidad'].values,
})
pc_out.to_csv(os.path.join(OUT, 'spatial', 'critical_points_locations.csv'), index=False)
print(f"spatial/critical_points_locations.csv: {pc_out.shape} (sin 'year' -- la fuente no trae fecha por punto)")

# ══════════════════════════════════════════════════════════════════
# spatial/spatial_statistics.csv — Moran global + bivariado + LISA (local)
# Todo cross-sectional (snapshot), sin dimensión "year" real -> se omite.
# ══════════════════════════════════════════════════════════════════
moran_global = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_global', 'moran_global.parquet'))
moran_biv = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_bivariado', 'moran_bivariado.parquet'))
lisa = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_local', 'lisa_local.parquet'))

filas = []
for _, r in moran_global.iterrows():
    filas.append({'geography_level': r['unidad'], 'geography_id': None, 'variable': r['variable'],
                   'method': 'Moran Global', 'statistic': r['moran_I'], 'p_value': r['p_value_sim'],
                   'significant': r['p_value_sim'] < 0.05, 'cluster_type': None})
for _, r in moran_biv.iterrows():
    filas.append({'geography_level': r['unidad'], 'geography_id': None,
                   'variable': f"{r['var_x']} <-> {r['var_y']}", 'method': 'Moran Bivariado',
                   'statistic': r['moran_I_bivariado'], 'p_value': r['p_value_sim'],
                   'significant': r['p_value_sim'] < 0.05, 'cluster_type': None})

# LISA: geography_id es el id real de UPZ/localidad -- necesita el mapeo idx -> cod_upz/cod_localidad
gdf_upz_idx = dim_upz_geo.reset_index(drop=True)
gdf_loc_idx = dim_loc_geo.reset_index(drop=True)
for _, r in lisa.iterrows():
    if r['unidad'] == 'UPZ':
        geo_id = gdf_upz_idx.iloc[int(r['idx'])]['cod_upz']
    else:
        geo_id = gdf_loc_idx.iloc[int(r['idx'])]['cod_localidad']
    filas.append({'geography_level': r['unidad'], 'geography_id': geo_id, 'variable': r['variable'],
                   'method': 'Moran Local (LISA)', 'statistic': r['I_local'], 'p_value': r['p_sim'],
                   'significant': r['p_sim'] < 0.05, 'cluster_type': r['cluster']})

spatial_stats = pd.DataFrame(filas)
spatial_stats.to_csv(os.path.join(OUT, 'spatial', 'spatial_statistics.csv'), index=False)
print(f"spatial/spatial_statistics.csv: {spatial_stats.shape} (Moran global + bivariado + LISA)")

# ══════════════════════════════════════════════════════════════════
# spatial/hotspots.csv — Getis-Ord Gi*
# ══════════════════════════════════════════════════════════════════
gistar = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'hotspots_gistar', 'gistar.parquet'))
filas_gi = []
for _, r in gistar.iterrows():
    if r['unidad'] == 'UPZ':
        geo_id = gdf_upz_idx.iloc[int(r['idx'])]['cod_upz']
    else:
        geo_id = gdf_loc_idx.iloc[int(r['idx'])]['cod_localidad']
    filas_gi.append({'geography_level': r['unidad'], 'geography_id': geo_id, 'variable': r['variable'],
                      'cluster_type': r['tipo'], 'statistic': r['Gi_z'], 'p_value': r['p_sim'],
                      'significant': r['p_sim'] < 0.05})
hotspots = pd.DataFrame(filas_gi)
hotspots.to_csv(os.path.join(OUT, 'spatial', 'hotspots.csv'), index=False)
print(f"spatial/hotspots.csv: {hotspots.shape} (Getis-Ord Gi*)")

# ══════════════════════════════════════════════════════════════════
# spatial/upz_geometry.geojson + localidad_geometry.geojson
# ══════════════════════════════════════════════════════════════════
dim_upz_geo.rename(columns={'cod_upz': 'upz_id', 'nombre_upz': 'upz_nombre'})[
    ['upz_id', 'upz_nombre', 'geometry']].to_file(
    os.path.join(OUT, 'spatial', 'upz_geometry.geojson'), driver='GeoJSON')
dim_loc_geo.rename(columns={'cod_localidad': 'localidad_id', 'nombre_localidad': 'localidad_nombre'})[
    ['localidad_id', 'localidad_nombre', 'geometry']].to_file(
    os.path.join(OUT, 'spatial', 'localidad_geometry.geojson'), driver='GeoJSON')
print("spatial/upz_geometry.geojson + localidad_geometry.geojson guardados (solo id/nombre + geometría, sin repetir indicadores)")

print("\n✅ spatial/ completo.")
