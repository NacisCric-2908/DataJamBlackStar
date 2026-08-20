"""
Fase 9 — Estadística espacial: Moran's I global, LISA (Moran local), Getis-Ord Gi*
DataJam Bogotá 2026
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import geopandas as gpd
import libpysal
from libpysal.weights import Queen
from esda.moran import Moran, Moran_Local, Moran_BV
from esda.getisord import G_Local

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.dirname(__file__)

np.random.seed(42)
N_PERM = 999


def analizar(gdf, cols, nombre_unidad):
    gdf = gdf.copy()
    w = Queen.from_dataframe(gdf, use_index=False)
    n_islas = len(w.islands)
    if n_islas > 0:
        print(f"  ⚠️  {n_islas} unidades sin vecinos (islas) en {nombre_unidad}: {w.islands} — Moran las excluye")
    w.transform = 'r'

    resultados_global = []
    resultados_local = []
    resultados_gistar = []

    for col in cols:
        y = gdf[col].fillna(gdf[col].median()).values
        if np.nanstd(y) == 0:
            print(f"  {col}: varianza 0, se omite")
            continue

        mi = Moran(y, w, permutations=N_PERM)
        resultados_global.append({
            'unidad': nombre_unidad, 'variable': col,
            'moran_I': round(mi.I, 4), 'p_value_sim': round(mi.p_sim, 4),
            'z_score': round(mi.z_sim, 3), 'n': len(y)
        })
        print(f"  [Moran global] {col}: I={mi.I:.4f} p={mi.p_sim:.4f} z={mi.z_sim:.3f}")

        lisa = Moran_Local(y, w, permutations=N_PERM, seed=42)
        q = lisa.q  # 1=HH, 2=LH, 3=LL, 4=HL
        sig = lisa.p_sim < 0.05
        etiqueta = {1: 'High-High', 2: 'Low-High', 3: 'Low-Low', 4: 'High-Low'}
        for i, idc in enumerate(gdf.index):
            resultados_local.append({
                'unidad': nombre_unidad, 'variable': col, 'idx': idc,
                'cluster': etiqueta[q[i]] if sig[i] else 'No significativo',
                'I_local': round(lisa.Is[i], 4), 'p_sim': round(lisa.p_sim[i], 4),
            })

        gi = G_Local(y, w, permutations=N_PERM, seed=42)
        for i, idc in enumerate(gdf.index):
            tipo = 'Hotspot (Gi* alto, sig.)' if (gi.Zs[i] > 0 and gi.p_sim[i] < 0.05) else \
                   'Coldspot (Gi* bajo, sig.)' if (gi.Zs[i] < 0 and gi.p_sim[i] < 0.05) else 'No significativo'
            resultados_gistar.append({
                'unidad': nombre_unidad, 'variable': col, 'idx': idc,
                'tipo': tipo, 'Gi_z': round(gi.Zs[i], 3), 'p_sim': round(gi.p_sim[i], 4),
            })

    return pd.DataFrame(resultados_global), pd.DataFrame(resultados_local), pd.DataFrame(resultados_gistar), w


# ══════════════════════════════════════════════════════════════════
# UPZ
# ══════════════════════════════════════════════════════════════════
print("== UPZ ==")
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet')).reset_index(drop=True)
master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
gdf_upz_m = gdf_upz.merge(master_upz, on=['cod_upz', 'nombre_upz', 'area_km2'], how='left')

vars_upz = ['deficit_aseo_relativo', 'densidad_puntos_criticos_km2', 'densidad_incidentes_km2',
            'densidad_cuadrantes_km2', 'estrato_promedio_oficial', 'estrato_promedio_reportado']
glob_upz, local_upz, gistar_upz, w_upz = analizar(gdf_upz_m, vars_upz, 'UPZ')

# Moran bivariado: deficit_aseo <-> puntos_criticos ; puntos_criticos <-> incidentes
print("\n  -- Moran bivariado (UPZ) --")
biv_resultados = []
pares = [('deficit_aseo_relativo', 'densidad_puntos_criticos_km2'),
         ('densidad_puntos_criticos_km2', 'densidad_incidentes_km2'),
         ('estrato_promedio_oficial', 'deficit_aseo_relativo')]
for xa, xb in pares:
    ya = gdf_upz_m[xa].fillna(gdf_upz_m[xa].median()).values
    yb = gdf_upz_m[xb].fillna(gdf_upz_m[xb].median()).values
    mbv = Moran_BV(ya, yb, w_upz, permutations=N_PERM)
    print(f"  {xa} <-> {xb}: I_biv={mbv.I:.4f} p={mbv.p_sim:.4f}")
    biv_resultados.append({'unidad': 'UPZ', 'var_x': xa, 'var_y': xb,
                            'moran_I_bivariado': round(mbv.I, 4), 'p_value_sim': round(mbv.p_sim, 4)})

# ══════════════════════════════════════════════════════════════════
# LOCALIDAD
# ══════════════════════════════════════════════════════════════════
print("\n== LOCALIDAD ==")
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet')).reset_index(drop=True)
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))
gdf_loc_m = gdf_loc.merge(master_loc, on=['cod_localidad', 'nombre_localidad', 'area_km2'], how='left')

vars_loc = ['deficit_aseo_relativo', 'densidad_puntos_criticos_km2', 'densidad_homicidios_km2',
            'densidad_incidentes_km2']
glob_loc, local_loc, gistar_loc, w_loc = analizar(gdf_loc_m, vars_loc, 'Localidad')

print("\n  -- Moran bivariado (Localidad) --")
for xa, xb in [('deficit_aseo_relativo', 'densidad_puntos_criticos_km2'),
               ('densidad_puntos_criticos_km2', 'densidad_homicidios_km2')]:
    ya = gdf_loc_m[xa].fillna(gdf_loc_m[xa].median()).values
    yb = gdf_loc_m[xb].fillna(gdf_loc_m[xb].median()).values
    mbv = Moran_BV(ya, yb, w_loc, permutations=N_PERM)
    print(f"  {xa} <-> {xb}: I_biv={mbv.I:.4f} p={mbv.p_sim:.4f}")
    biv_resultados.append({'unidad': 'Localidad', 'var_x': xa, 'var_y': xb,
                            'moran_I_bivariado': round(mbv.I, 4), 'p_value_sim': round(mbv.p_sim, 4)})

# ══════════════════════════════════════════════════════════════════
# Guardar
# ══════════════════════════════════════════════════════════════════
glob_all = pd.concat([glob_upz, glob_loc], ignore_index=True)
local_all = pd.concat([local_upz, local_loc], ignore_index=True)
gistar_all = pd.concat([gistar_upz, gistar_loc], ignore_index=True)
biv_all = pd.DataFrame(biv_resultados)

glob_all.to_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_global', 'moran_global.parquet'), index=False)
local_all.to_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_local', 'lisa_local.parquet'), index=False)
gistar_all.to_parquet(os.path.join(GOLD, 'estadistica_espacial', 'hotspots_gistar', 'gistar.parquet'), index=False)
biv_all.to_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_bivariado', 'moran_bivariado.parquet'), index=False)

glob_all.to_csv(os.path.join(OUT, 'moran_global.csv'), index=False)
biv_all.to_csv(os.path.join(OUT, 'moran_bivariado.csv'), index=False)
resumen_lisa = local_all.groupby(['unidad', 'variable', 'cluster']).size().reset_index(name='n')
resumen_lisa.to_csv(os.path.join(OUT, 'lisa_resumen.csv'), index=False)
resumen_gistar = gistar_all.groupby(['unidad', 'variable', 'tipo']).size().reset_index(name='n')
resumen_gistar.to_csv(os.path.join(OUT, 'gistar_resumen.csv'), index=False)

print("\n=== RESUMEN MORAN GLOBAL ===")
print(glob_all.to_string(index=False))
print("\n=== RESUMEN LISA (conteo de clusters por variable) ===")
print(resumen_lisa.to_string(index=False))
print("\n✅ Fase 9 completa.")
