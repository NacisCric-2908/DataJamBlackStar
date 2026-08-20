"""
Fase 5 (complemento) — Análisis de proximidad (agent.md, sección 11)
DataJam Bogotá 2026

Para cada punto crítico de arrojo clandestino: distancia (metros, EPSG:3116) a
la cesta, contenedor, macroruta, estación de bomberos y cuadrante de policía
más cercanos. Determina si los puntos críticos se concentran en zonas de baja
accesibilidad a infraestructura formal.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy import stats

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
OUT = os.path.dirname(__file__)

EPSG_M = 3116

gdf_pc = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'puntos_criticos.parquet')).to_crs(epsg=EPSG_M)
gdf_cestas = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'cestas.parquet')).to_crs(epsg=EPSG_M)
gdf_cont = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'contenerizacion.parquet')).to_crs(epsg=EPSG_M)
gdf_mr = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'macrorutas.parquet')).to_crs(epsg=EPSG_M)
gdf_ebom = gpd.read_parquet(os.path.join(SILVER, 'bomberos', 'estaciones.parquet')).to_crs(epsg=EPSG_M)
gdf_cuad = gpd.read_parquet(os.path.join(SILVER, 'policia', 'cuadrantes.parquet')).to_crs(epsg=EPSG_M)

print(f"Puntos críticos: {len(gdf_pc)}")


def distancia_minima(gdf_origen, gdf_destino, nombre):
    """Distancia de cada geometría en gdf_origen a la más cercana en gdf_destino (sjoin_nearest)."""
    res = gpd.sjoin_nearest(gdf_origen[['geometry']], gdf_destino[['geometry']], distance_col=f'dist_{nombre}_m')
    res = res[~res.index.duplicated(keep='first')]  # sjoin_nearest puede empatar -> quedarse con la primera
    print(f"  dist_{nombre}_m: media={res[f'dist_{nombre}_m'].mean():.1f}m, mediana={res[f'dist_{nombre}_m'].median():.1f}m")
    return res[f'dist_{nombre}_m']


gdf_pc = gdf_pc.reset_index(drop=True)
gdf_pc['dist_cesta_m'] = distancia_minima(gdf_pc, gdf_cestas, 'cesta').values
gdf_pc['dist_contenedor_m'] = distancia_minima(gdf_pc, gdf_cont, 'contenedor').values
gdf_pc['dist_bombero_m'] = distancia_minima(gdf_pc, gdf_ebom, 'bombero').values

# macrorutas y cuadrantes son polígonos: distancia 0 si el punto cae dentro
gdf_pc['dist_macroruta_m'] = gdf_pc.geometry.apply(lambda p: gdf_mr.distance(p).min())
gdf_pc['dist_cuadrante_m'] = gdf_pc.geometry.apply(lambda p: gdf_cuad.distance(p).min())
print(f"  dist_macroruta_m: media={gdf_pc['dist_macroruta_m'].mean():.1f}m (0 = dentro de una macroruta)")
print(f"  dist_cuadrante_m: media={gdf_pc['dist_cuadrante_m'].mean():.1f}m (0 = dentro de un cuadrante)")

# ══════════════════════════════════════════════════════════════════
# Grupo de control: puntos aleatorios dentro del área urbana (mismo n que puntos críticos)
# para comparar si los puntos críticos están sistemáticamente MÁS lejos de la infraestructura
# formal que un punto cualquiera de la ciudad.
# ══════════════════════════════════════════════════════════════════
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet')).to_crs(epsg=EPSG_M)
union_upz = gdf_upz.geometry.union_all()
minx, miny, maxx, maxy = union_upz.bounds
rng = np.random.default_rng(42)
puntos_random = []
while len(puntos_random) < len(gdf_pc):
    x = rng.uniform(minx, maxx)
    y = rng.uniform(miny, maxy)
    from shapely.geometry import Point
    p = Point(x, y)
    if union_upz.contains(p):
        puntos_random.append(p)
gdf_random = gpd.GeoDataFrame(geometry=puntos_random, crs=EPSG_M)

print(f"\n== Comparación puntos críticos (n={len(gdf_pc)}) vs {len(gdf_random)} puntos aleatorios en zona urbana ==")
comparacion = []
for nombre, gdf_dest in [('cesta', gdf_cestas), ('contenedor', gdf_cont), ('bombero', gdf_ebom)]:
    d_pc = distancia_minima(gdf_pc[['geometry']], gdf_dest, f'{nombre}_pc')
    d_rand = distancia_minima(gdf_random, gdf_dest, f'{nombre}_rand')
    stat, p = stats.mannwhitneyu(d_pc, d_rand, alternative='two-sided')
    mas_lejos = d_pc.mean() > d_rand.mean()
    comparacion.append({
        'infraestructura': nombre, 'dist_media_puntos_criticos_m': round(d_pc.mean(), 1),
        'dist_media_aleatorio_m': round(d_rand.mean(), 1),
        'puntos_criticos_mas_lejos': mas_lejos, 'mannwhitney_p': round(p, 5), 'sig_5pct': p < 0.05,
    })

df_comp = pd.DataFrame(comparacion)
print(df_comp.to_string(index=False))

# ══════════════════════════════════════════════════════════════════
# Guardar
# ══════════════════════════════════════════════════════════════════
cols_out = ['OBJECTID', 'cod_localidad', 'dist_cesta_m', 'dist_contenedor_m', 'dist_macroruta_m',
            'dist_bombero_m', 'dist_cuadrante_m']
gdf_pc[cols_out].to_parquet(os.path.join(OUT, 'proximidad_puntos_criticos.parquet'), index=False)
gdf_pc[cols_out].to_parquet(os.path.join(GOLD, 'aseo', 'proximidad_puntos_criticos.parquet'), index=False)
df_comp.to_csv(os.path.join(OUT, 'proximidad_vs_aleatorio.csv'), index=False)
df_comp.to_parquet(os.path.join(GOLD, 'aseo', 'proximidad_vs_aleatorio.parquet'), index=False)

print(f"\n✅ Fase 5 (proximidad) completa. {len(gdf_pc)} puntos críticos con 5 distancias cada uno.")
