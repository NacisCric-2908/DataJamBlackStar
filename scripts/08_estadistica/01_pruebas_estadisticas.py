"""
Fase 8 — Estadística (no espacial): correlaciones formales entre TODAS las
variables clave, con corrección por comparaciones múltiples, y prueba de
normalidad para justificar Pearson vs Spearman.
DataJam Bogotá 2026
"""
import os
import itertools
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
from scipy import stats
from statsmodels.stats.multitest import multipletests

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
OUT = os.path.dirname(__file__)

master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

# Las variables per cápita (15ª fuente: población DANE/SDP por UPZ) entran junto a las
# de densidad por km2, no en su lugar: comparar ambas normalizaciones es justamente lo
# que revela cuánto de un "déficit" es densidad urbana y cuánto es cobertura real.
VARS_UPZ = ['estrato_promedio_oficial', 'estrato_promedio_reportado', 'deficit_aseo_relativo', 'densidad_cestas_km2',
            'densidad_contenedores_km2', 'densidad_puntos_criticos_km2', 'densidad_cuadrantes_km2',
            'densidad_incidentes_km2', 'dist_estacion_bomberos_m', 'cobertura_macrorutas_pct',
            'deficit_aseo_percapita', 'cestas_por_1000hab', 'contenedores_por_1000hab',
            'puntos_criticos_por_100milhab', 'incidentes_por_100milhab', 'densidad_poblacional_hab_km2']
VARS_LOC = ['estrato_promedio_oficial', 'estrato_promedio_reportado', 'deficit_aseo_relativo', 'densidad_cestas_km2',
            'densidad_puntos_criticos_km2', 'densidad_cuadrantes_km2', 'densidad_homicidios_km2',
            'densidad_incidentes_km2', 'dist_estacion_bomberos_m',
            'deficit_aseo_percapita', 'cestas_por_1000hab', 'puntos_criticos_por_100milhab',
            'homicidios_por_100milhab', 'densidad_poblacional_hab_km2']


def test_normalidad(df, cols):
    filas = []
    for c in cols:
        x = df[c].dropna()
        if len(x) < 8:
            continue
        stat, p = stats.shapiro(x)
        filas.append({'variable': c, 'shapiro_stat': round(stat, 4), 'p_value': round(p, 5),
                       'normal_al_5pct': p > 0.05})
    return pd.DataFrame(filas)


def matriz_correlacion(df, cols, nombre_unidad):
    filas = []
    for a, b in itertools.combinations(cols, 2):
        d = df[[a, b]].dropna()
        if len(d) < 5:
            continue
        rp, pp = stats.pearsonr(d[a], d[b])
        rs, ps = stats.spearmanr(d[a], d[b])
        filas.append({'unidad': nombre_unidad, 'var_x': a, 'var_y': b,
                       'pearson_r': round(rp, 3), 'pearson_p': round(pp, 5),
                       'spearman_rho': round(rs, 3), 'spearman_p': round(ps, 5), 'n': len(d)})
    df_r = pd.DataFrame(filas)
    # corrección por comparaciones múltiples (Benjamini-Hochberg, FDR) sobre Spearman
    if len(df_r) > 0:
        rej, p_adj, _, _ = multipletests(df_r['spearman_p'], alpha=0.05, method='fdr_bh')
        df_r['spearman_p_fdr'] = p_adj.round(5)
        df_r['sig_tras_fdr'] = rej
    return df_r


print("== Normalidad (Shapiro-Wilk) — UPZ ==")
norm_upz = test_normalidad(master_upz, VARS_UPZ)
print(norm_upz.to_string(index=False))
print(f"\n  {(~norm_upz['normal_al_5pct']).sum()}/{len(norm_upz)} variables NO son normales -> se prioriza Spearman sobre Pearson")

print("\n== Matriz de correlación completa — UPZ (n=112) ==")
corr_upz = matriz_correlacion(master_upz, VARS_UPZ, 'UPZ')
sig_upz = corr_upz[corr_upz['sig_tras_fdr']].sort_values('spearman_rho', key=abs, ascending=False)
print(f"Pares significativos tras corrección FDR: {len(sig_upz)}/{len(corr_upz)}")
print(sig_upz[['var_x', 'var_y', 'spearman_rho', 'spearman_p_fdr']].to_string(index=False))

print("\n== Matriz de correlación completa — Localidad (n=20) ==")
corr_loc = matriz_correlacion(master_loc, VARS_LOC, 'Localidad')
sig_loc = corr_loc[corr_loc['sig_tras_fdr']].sort_values('spearman_rho', key=abs, ascending=False)
print(f"Pares significativos tras corrección FDR: {len(sig_loc)}/{len(corr_loc)}")
print(sig_loc[['var_x', 'var_y', 'spearman_rho', 'spearman_p_fdr']].to_string(index=False))

norm_upz.to_csv(os.path.join(OUT, 'normalidad_upz.csv'), index=False)
pd.concat([corr_upz, corr_loc], ignore_index=True).to_csv(os.path.join(OUT, 'matriz_correlacion.csv'), index=False)
pd.concat([corr_upz, corr_loc], ignore_index=True).to_parquet(os.path.join(GOLD, 'estadistica_espacial', 'matriz_correlacion.parquet'), index=False)

print(f"\n✅ Fase 8 completa. {len(corr_upz)+len(corr_loc)} pares evaluados, guardado en 08_estadistica/matriz_correlacion.csv")
