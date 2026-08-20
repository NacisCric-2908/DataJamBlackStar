"""
Fase 10 — Modelos multivariables
DataJam Bogotá 2026

Variables de conteo -> GLM Poisson primero; si hay sobredispersión
(deviance/df >> 1) se reajusta con Binomial Negativa (NB2, statsmodels).
Offset = log(area_km2) para modelar TASA por km2, no conteo bruto.
Se reporta VIF de los predictores antes de cada modelo.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.dirname(__file__)

master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

resultados = []


def vif_de(df, cols):
    X = sm.add_constant(df[cols].fillna(df[cols].median()))
    vifs = {c: variance_inflation_factor(X.values, i + 1) for i, c in enumerate(cols)}
    return vifs


def ajustar_conteo(df, formula, offset_col, nombre_modelo, hipotesis):
    d = df.copy()
    d['log_offset'] = np.log(d[offset_col].replace(0, np.nan))
    d = d.dropna(subset=[offset_col])

    # Poisson primero
    mod_poi = smf.glm(formula=formula, data=d, family=sm.families.Poisson(),
                       offset=d['log_offset']).fit()
    disp = mod_poi.deviance / mod_poi.df_resid
    print(f"\n--- {nombre_modelo} ({hipotesis}) ---")
    print(f"  Poisson: deviance/df = {disp:.2f} ({'sobredispersión -> uso NB' if disp > 1.5 else 'aceptable, uso Poisson'})")

    if disp > 1.5:
        try:
            mod = smf.glm(formula=formula, data=d, family=sm.families.NegativeBinomial(alpha=1.0),
                           offset=d['log_offset']).fit()
            familia = 'BinomialNegativa(alpha=1.0)'
        except Exception as e:
            mod = mod_poi
            familia = f'Poisson (NB falló: {e})'
    else:
        mod = mod_poi
        familia = 'Poisson'

    for var in mod.params.index:
        if var == 'Intercept':
            continue
        coef = mod.params[var]
        ci = mod.conf_int().loc[var]
        resultados.append({
            'modelo': nombre_modelo, 'hipotesis': hipotesis, 'familia': familia,
            'variable': var, 'coef': round(coef, 4), 'coef_exp_irr': round(np.exp(coef), 3),
            'p_value': round(mod.pvalues[var], 4), 'ci_low': round(ci[0], 4), 'ci_high': round(ci[1], 4),
            'n': int(mod.nobs), 'aic': round(mod.aic, 1),
        })
        sig = '***' if mod.pvalues[var] < 0.01 else ('**' if mod.pvalues[var] < 0.05 else ('*' if mod.pvalues[var] < 0.1 else ''))
        print(f"  {var}: coef={coef:.4f} IRR={np.exp(coef):.3f} p={mod.pvalues[var]:.4f} {sig}")
    return mod


# ══════════════════════════════════════════════════════════════════
# H2/H3 — Puntos críticos ~ Déficit de aseo + Estrato (control: área vía offset)
# ══════════════════════════════════════════════════════════════════
cols_h2 = ['deficit_aseo_relativo', 'estrato_promedio_oficial']
print("VIF modelo H2/H3 (UPZ):", vif_de(master_upz, cols_h2))
ajustar_conteo(master_upz, 'n_puntos_criticos ~ deficit_aseo_relativo + estrato_promedio_oficial',
               'area_km2', 'M1_puntos_criticos_UPZ', 'H2+H3: Déficit aseo / Vulnerabilidad -> Arrojo clandestino')

# ══════════════════════════════════════════════════════════════════
# H5 — Incidentes ~ Puntos críticos + Estrato (control: distancia a bomberos, área offset)
# ══════════════════════════════════════════════════════════════════
cols_h5 = ['n_puntos_criticos', 'estrato_promedio_oficial', 'dist_estacion_bomberos_m']
print("\nVIF modelo H5 (UPZ):", vif_de(master_upz, cols_h5))
ajustar_conteo(master_upz, 'n_incidentes_total ~ n_puntos_criticos + estrato_promedio_oficial + dist_estacion_bomberos_m',
               'area_km2', 'M2_incidentes_UPZ', 'H5+H7: Arrojo / Vulnerabilidad -> Emergencias urbanas')

# ══════════════════════════════════════════════════════════════════
# H4/H6 — Homicidios (localidad) ~ Puntos críticos + Déficit aseo + Cuadrantes (control policial)
# ══════════════════════════════════════════════════════════════════
cols_h4 = ['n_puntos_criticos', 'deficit_aseo_relativo', 'n_cuadrantes']
print("\nVIF modelo H4/H6 (Localidad):", vif_de(master_loc, cols_h4))
ajustar_conteo(master_loc, 'homicidios_cont ~ n_puntos_criticos + deficit_aseo_relativo + n_cuadrantes',
               'area_km2', 'M3_homicidios_localidad', 'H4+H6: Arrojo / Vulnerabilidad -> Delitos de alto impacto')

# ══════════════════════════════════════════════════════════════════
# Hipótesis conjunta (§9 de agent.md): Delitos ~ Vulnerabilidad + DéficitAseo + Arrojo + Densidad + Policía
# ══════════════════════════════════════════════════════════════════
cols_hc = ['estrato_promedio_oficial', 'deficit_aseo_relativo', 'n_puntos_criticos', 'n_cuadrantes']
print("\nVIF modelo conjunto (Localidad):", vif_de(master_loc, cols_hc))
ajustar_conteo(master_loc,
               'homicidios_cont ~ estrato_promedio_oficial + deficit_aseo_relativo + n_puntos_criticos + n_cuadrantes',
               'area_km2', 'M4_conjunto_delitos_localidad',
               'Hipótesis conjunta: Vulnerabilidad+DéficitAseo+Arrojo+Policía -> Delitos')

df_res = pd.DataFrame(resultados)
df_res.to_parquet(os.path.join(GOLD, 'modelos', 'resultados_modelos.parquet'), index=False)
df_res.to_csv(os.path.join(OUT, 'resultados_modelos.csv'), index=False)
print(f"\n✅ Fase 10 completa. {len(df_res)} coeficientes guardados en gold/modelos/resultados_modelos.parquet")
