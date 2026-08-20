"""
agent2.md — Fase 5-7: dimensions/ (upz.csv, localidades.csv, years.csv)
DataJam Bogotá 2026

Capa de CONSUMO para dashboard: solo re-empaqueta lo que ya existe en Gold.
No calcula ningún indicador nuevo. La única excepción es el cruce
UPZ -> localidad_id (spatial "within" del punto representativo de cada UPZ
dentro del polígono de localidad): es la misma técnica ya usada y validada
en todo el pipeline (05_integracion_espacial), no un análisis nuevo -- es
plomería estructural para poder filtrar el dashboard por localidad.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.join(BASE, 'data', 'dashboard')

gdf_upz = gpd.read_parquet(os.path.join(GOLD, 'dimensiones', 'dim_upz.parquet'))
gdf_loc = gpd.read_parquet(os.path.join(GOLD, 'dimensiones', 'dim_localidad.parquet'))

# ── Cruce estructural UPZ -> Localidad (spatial join, no es un "análisis") ──
gdf_upz_pt = gdf_upz.copy()
gdf_upz_pt['geometry'] = gdf_upz_pt.geometry.representative_point()
sj = gpd.sjoin(gdf_upz_pt, gdf_loc[['cod_localidad', 'nombre_localidad', 'geometry']],
               how='left', predicate='within')
match = sj['cod_localidad'].notna().sum()
print(f"UPZ -> Localidad (spatial join estructural): {match}/{len(gdf_upz)} asignadas")

# ── dimensions/upz.csv ──
upz_csv = pd.DataFrame({
    'upz_id': gdf_upz['cod_upz'],
    'upz_nombre': gdf_upz['nombre_upz'],
    'localidad_id': sj['cod_localidad'].values,
    'localidad_nombre': sj['nombre_localidad'].values,
    'area_km2': gdf_upz['area_km2'],
})
upz_csv.to_csv(os.path.join(OUT, 'dimensions', 'upz.csv'), index=False)
print(f"dimensions/upz.csv: {upz_csv.shape}")

# ── dimensions/localidades.csv ──
loc_csv = pd.DataFrame({
    'localidad_id': gdf_loc['cod_localidad'],
    'localidad_nombre': gdf_loc['nombre_localidad'],
    'area_km2': gdf_loc['area_km2'],
})
loc_csv.to_csv(os.path.join(OUT, 'dimensions', 'localidades.csv'), index=False)
print(f"dimensions/localidades.csv: {loc_csv.shape}")

# ── dimensions/years.csv — únicamente años presentes en datasets YA usados ──
emerg = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))
delitos = pd.read_parquet(os.path.join(GOLD, 'seguridad', 'delitos_localidad_anio.parquet'))
rbl = pd.read_parquet(os.path.join(GOLD, 'aseo', 'rbl_series_por_ase.parquet'))

anios = sorted(set(emerg['anio'].unique()) | set(delitos['anio'].unique()) | set(rbl['anio'].unique()))
years_csv = pd.DataFrame({'year': anios})
years_csv.to_csv(os.path.join(OUT, 'dimensions', 'years.csv'), index=False)
print(f"dimensions/years.csv: {years_csv.shape} -> {anios}")

print("\n✅ dimensions/ completo.")
