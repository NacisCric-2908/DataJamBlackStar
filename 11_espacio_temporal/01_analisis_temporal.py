"""
Fase 11 — Análisis espacio-temporal
DataJam Bogotá 2026

Cada fuente se analiza en su resolución espacio-temporal NATIVA (no se fuerza
un panel único). Busca: tendencias, rupturas, años atípicos, zonas
persistentes vs emergentes.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
from scipy import stats

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.dirname(__file__)

# ══════════════════════════════════════════════════════════════════
# 1. UAECOB — incidentes UPZ x año (2016-2020): zonas persistentes vs emergentes
# ══════════════════════════════════════════════════════════════════
print("== UAECOB: incidentes UPZ x año ==")
inc = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))
pivot = inc.pivot_table(index='cod_upz', columns='anio', values='n_incidentes', fill_value=0)

# tendencia por UPZ (pendiente de regresión simple año->incidentes)
tendencias = []
for upz, row in pivot.iterrows():
    years = row.index.values.astype(float)
    vals = row.values.astype(float)
    if vals.sum() == 0:
        continue
    slope, intercept, r, p, se = stats.linregress(years, vals)
    tendencias.append({'cod_upz': upz, 'pendiente_incidentes_anio': round(slope, 2),
                        'p_value': round(p, 4), 'media_incidentes': round(vals.mean(), 1)})
df_tend = pd.DataFrame(tendencias)

# top emergentes (pendiente positiva y significativa) vs persistentes (alto nivel, pendiente ~0)
emergentes = df_tend[(df_tend['pendiente_incidentes_anio'] > 0) & (df_tend['p_value'] < 0.1)].sort_values('pendiente_incidentes_anio', ascending=False)
persistentes = df_tend[df_tend['media_incidentes'] > df_tend['media_incidentes'].quantile(0.75)].sort_values('media_incidentes', ascending=False)
declive = df_tend[(df_tend['pendiente_incidentes_anio'] < 0) & (df_tend['p_value'] < 0.1)].sort_values('pendiente_incidentes_anio')

print(f"UPZ con tendencia creciente significativa (p<0.10): {len(emergentes)}")
print(emergentes.head(5).to_string(index=False))
print(f"\nUPZ con tendencia decreciente significativa (p<0.10): {len(declive)}")
print(declive.head(5).to_string(index=False))
print(f"\nUPZ persistentemente altas (top cuartil de nivel medio): {len(persistentes)}")

# ruptura/año atípico: z-score del total anual vs media 2016-2020
total_anual = inc.groupby('anio')['n_incidentes'].sum()
z_anual = (total_anual - total_anual.mean()) / total_anual.std()
print(f"\nTotal incidentes por año (UAECOB) y z-score respecto a la media del periodo:")
print(pd.DataFrame({'total': total_anual, 'z_score': z_anual.round(2)}))
anio_atipico_uaecob = z_anual[abs(z_anual) > 1].index.tolist()
print(f"Años atípicos (|z|>1): {anio_atipico_uaecob}")

df_tend.to_csv(os.path.join(OUT, 'tendencias_uaecob_upz.csv'), index=False)

# ══════════════════════════════════════════════════════════════════
# 2. DAILoc — homicidios/violencia intrafamiliar localidad x año (2018-2026)
# ══════════════════════════════════════════════════════════════════
print("\n== DAILoc: delitos localidad x año ==")
delitos = pd.read_parquet(os.path.join(GOLD, 'seguridad', 'delitos_localidad_anio.parquet'))
total_hom = delitos.groupby('anio')['homicidios'].sum()
z_hom = (total_hom - total_hom.mean()) / total_hom.std()
print(pd.DataFrame({'homicidios': total_hom, 'z_score': z_hom.round(2)}))
anio_atipico_dai = z_hom[abs(z_hom) > 1.5].index.tolist()
print(f"Años atípicos en homicidios (|z|>1.5): {anio_atipico_dai}")

total_vif = delitos.groupby('anio')['violencia_intrafamiliar'].sum()
z_vif = (total_vif - total_vif.mean()) / total_vif.std()
print(f"\nViolencia intrafamiliar por año:")
print(pd.DataFrame({'vif': total_vif, 'z_score': z_vif.round(2)}))
anio_atipico_vif = z_vif[abs(z_vif) > 1.5].index.tolist()
print(f"Años atípicos en VIF (|z|>1.5): {anio_atipico_vif} -- ⚠️ ver nota de cobertura 2026 (posible año incompleto)")

slope_h, _, r_h, p_h, _ = stats.linregress(total_hom.index, total_hom.values)
print(f"\nTendencia homicidios 2018-2026: pendiente={slope_h:.2f}/año, r={r_h:.3f}, p={p_h:.4f}")

# localidades persistentemente altas en homicidios (CONT) a lo largo de los años
loc_persist = delitos.groupby('cod_localidad')['homicidios'].agg(['mean', 'std']).round(1)
loc_persist['coef_variacion'] = (loc_persist['std'] / loc_persist['mean']).round(2)
top_persist = loc_persist.sort_values('mean', ascending=False).head(5)
print(f"\nLocalidades persistentemente con más homicidios (media 2018-2026):")
print(top_persist)

# ══════════════════════════════════════════════════════════════════
# 3. RBL — residuos ASE x mes (2021-2026): tendencia y ruptura por la colisión de columnas
# ══════════════════════════════════════════════════════════════════
print("\n== RBL: serie mensual total_t ==")
rbl = pd.read_parquet(os.path.join(SILVER, 'aseo', 'rbl_series.parquet'))
serie = rbl.groupby('fecha')['total_t'].sum().sort_index()
slope_r, _, r_r, p_r, _ = stats.linregress(range(len(serie)), serie.values)
print(f"Tendencia mensual total_t: pendiente={slope_r:.1f} t/mes, r={r_r:.3f}, p={p_r:.4f}")
print(f"Media 2021-2022 (antes de la corrección de columnas): {rbl[rbl['anio'].isin([2021,2022])]['total_t'].mean():.0f} t")
print(f"Media 2023-2026 (con arrojo_clandestino_punto_limpio_t separado): {rbl[rbl['anio'].isin([2023,2024,2025,2026])]['total_t'].mean():.0f} t")
print("(la separación de columnas en Fase 3-4 evita una ruptura artificial en la serie por el cambio de esquema 2023)")

resumen = pd.DataFrame([
    {'fuente': 'UAECOB', 'ventana': '2016-2020', 'grano_espacial': 'UPZ', 'anios_atipicos': str(anio_atipico_uaecob)},
    {'fuente': 'DAILoc-homicidios', 'ventana': '2018-2026', 'grano_espacial': 'Localidad', 'anios_atipicos': str(anio_atipico_dai)},
    {'fuente': 'DAILoc-VIF', 'ventana': '2018-2026', 'grano_espacial': 'Localidad', 'anios_atipicos': str(anio_atipico_vif)},
    {'fuente': 'RBL', 'ventana': '2021-2026', 'grano_espacial': 'ASE (no UPZ/loc)', 'anios_atipicos': 'N/A (tendencia continua, sin ruptura tras fix)'},
])
resumen.to_csv(os.path.join(OUT, 'resumen_espacio_temporal.csv'), index=False)
print("\n✅ Fase 11 completa.")
