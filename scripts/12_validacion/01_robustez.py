"""
Fase 12 — Validación estadística y análisis de robustez
DataJam Bogotá 2026

Repite las asociaciones clave bajo distintas especificaciones:
- UPZ vs Localidad (MAUP)
- conteo crudo vs densidad vs log-densidad
- pesos espaciales Queen vs KNN (Moran's I)
"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import geopandas as gpd
from scipy import stats
from libpysal.weights import Queen, KNN
from esda.moran import Moran

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
OUT = os.path.dirname(__file__)

master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

# ══════════════════════════════════════════════════════════════════
# 1. Robustez de H1 (estrato <-> déficit aseo) y H4 (puntos críticos <-> delitos/incidentes)
#    bajo 3 especificaciones: crudo, densidad, log(densidad+1)
# ══════════════════════════════════════════════════════════════════
resultados = []


def testear(df, xcol, ycol, nombre_unidad, hipotesis, transform):
    d = df[[xcol, ycol]].dropna()
    if transform == 'log':
        d = d.copy()
        d[ycol] = np.log1p(d[ycol])
    r, p = stats.spearmanr(d[xcol], d[ycol])
    resultados.append({'hipotesis': hipotesis, 'unidad': nombre_unidad, 'transformacion': transform,
                        'x': xcol, 'y': ycol, 'spearman_rho': round(r, 3), 'p_value': round(p, 4),
                        'n': len(d), 'sig_5pct': p < 0.05})


# H1: estrato vs deficit_aseo_relativo (ya es un índice relativo, no admite "crudo/densidad")
for df, u in [(master_upz, 'UPZ'), (master_loc, 'Localidad')]:
    testear(df, 'estrato_promedio_oficial', 'deficit_aseo_relativo', u, 'H1', 'estandarizado')

# H4/H5: puntos_criticos (crudo, densidad, log-densidad) vs incidentes/homicidios
for df, u, ycol in [(master_upz, 'UPZ', 'n_incidentes_total'), (master_loc, 'Localidad', 'homicidios_cont')]:
    testear(df, 'n_puntos_criticos', ycol, u, 'H4/H5 (conteo crudo)', 'crudo')
    dens_x = 'densidad_puntos_criticos_km2'
    dens_y = f"densidad_{'incidentes' if ycol=='n_incidentes_total' else 'homicidios'}_km2"
    testear(df, dens_x, dens_y, u, 'H4/H5 (densidad)', 'densidad')
    testear(df, dens_x, dens_y, u, 'H4/H5 (log-densidad)', 'log')

df_rob = pd.DataFrame(resultados)
print("== Robustez de H1 y H4/H5 bajo distintas especificaciones ==")
print(df_rob.to_string(index=False))

# ══════════════════════════════════════════════════════════════════
# 2. Robustez de Moran's I a la definición de pesos espaciales (Queen vs KNN-5)
# ══════════════════════════════════════════════════════════════════
print("\n== Sensibilidad de Moran's I a la matriz de pesos espaciales (UPZ) ==")
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet')).reset_index(drop=True)
gdf_upz_m = gdf_upz.merge(master_upz, on=['cod_upz', 'nombre_upz', 'area_km2'], how='left')

w_queen = Queen.from_dataframe(gdf_upz_m, use_index=False)
w_queen.transform = 'r'
w_knn = KNN.from_dataframe(gdf_upz_m, k=5)
w_knn.transform = 'r'

resultados_w = []
for col in ['deficit_aseo_relativo', 'densidad_puntos_criticos_km2', 'densidad_incidentes_km2']:
    y = gdf_upz_m[col].fillna(gdf_upz_m[col].median()).values
    for nombre_w, w in [('Queen (contigüidad)', w_queen), ('KNN k=5', w_knn)]:
        mi = Moran(y, w, permutations=999)
        resultados_w.append({'variable': col, 'pesos_espaciales': nombre_w,
                              'moran_I': round(mi.I, 4), 'p_value': round(mi.p_sim, 4)})
df_w = pd.DataFrame(resultados_w)
print(df_w.to_string(index=False))

# ══════════════════════════════════════════════════════════════════
# 3. Tabla resumen MAUP: significancia UPZ vs Localidad, todas las variables Fase 9
# ══════════════════════════════════════════════════════════════════
moran_global = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_global', 'moran_global.parquet'))
maup = moran_global.pivot_table(index='variable', columns='unidad', values=['moran_I', 'p_value_sim'])
print("\n== MAUP: Moran's I global UPZ vs Localidad (mismas variables donde existen en ambas) ==")
print(maup.round(4))

df_rob.to_csv(os.path.join(OUT, 'robustez_especificaciones.csv'), index=False)
df_w.to_csv(os.path.join(OUT, 'robustez_pesos_espaciales.csv'), index=False)
maup.to_csv(os.path.join(OUT, 'maup_upz_vs_localidad.csv'))

n_robustas = df_rob.groupby(['hipotesis', 'unidad'])['sig_5pct'].agg(['sum', 'count'])
print(f"\n✅ Fase 12 completa. Resumen de robustez guardado en 12_validacion/.")
