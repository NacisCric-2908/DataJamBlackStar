"""
agent2.md — Fase 16: hypotheses/hypothesis_results.csv
DataJam Bogotá 2026

Transcribe pruebas estadísticas YA REALIZADAS (10_modelos, 12_validacion,
09_estadistica_espacial, 05_integracion_espacial). No se ejecuta ningún
modelo nuevo aquí -- este script solo lee los CSV de resultados existentes
y los reorganiza al esquema de agent2.md. Las conclusiones (evidence_level)
son las mismas ya reportadas en 14_resultados/informe_final.md sección 6,
no se re-derivan.
"""
import os
import pandas as pd
from statsmodels.stats.multitest import multipletests

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(BASE, 'data', 'dashboard')
os.makedirs(OUT, exist_ok=True)

modelos = pd.read_csv(os.path.join(BASE, 'scripts', '10_modelos', 'resultados_modelos.csv'))
robustez = pd.read_csv(os.path.join(BASE, 'scripts', '12_validacion', 'robustez_especificaciones.csv'))
moran_biv = pd.read_csv(os.path.join(BASE, 'scripts', '09_estadistica_espacial', 'moran_bivariado.csv'))
proximidad = pd.read_csv(os.path.join(BASE, 'scripts', '05_integracion_espacial', 'proximidad_vs_aleatorio.csv'))
periodos = pd.read_csv(os.path.join(BASE, 'scripts', '12_validacion', 'robustez_periodos_temporales.csv'))

filas = []


def add(hid, hname, vx, vy, method, statistic, p_value, effect_size, ci, conclusion, evidence, n=None):
    filas.append(dict(hypothesis_id=hid, hypothesis_name=hname, variable_x=vx, variable_y=vy,
                       method=method, statistic=round(float(statistic), 4) if statistic is not None else None,
                       p_value=round(float(p_value), 4) if p_value is not None else None,
                       effect_size=effect_size, confidence_interval=ci, n=n,
                       conclusion=conclusion, evidence_level=evidence))


# H1 — Vulnerabilidad -> Déficit de aseo
for _, r in robustez[robustez['hipotesis'] == 'H1'].iterrows():
    add('H1', 'Vulnerabilidad socioeconómica -> Déficit de infraestructura de aseo',
        'estrato_promedio_oficial', 'deficit_aseo_relativo', f"Spearman ({r['unidad']})",
        r['spearman_rho'], r['p_value'], 'rho', None,
        'SUPPORTED' if r['sig_5pct'] else 'NOT_SUPPORTED', 'CONFIRMADA', n=r['n'])
biv = moran_biv[(moran_biv['var_x'] == 'estrato_promedio_oficial') & (moran_biv['var_y'] == 'deficit_aseo_relativo')].iloc[0]
add('H1', 'Vulnerabilidad socioeconómica -> Déficit de infraestructura de aseo',
    'estrato_promedio_oficial', 'deficit_aseo_relativo', 'Moran Bivariado (UPZ)',
    biv['moran_I_bivariado'], biv['p_value_sim'], 'Moran I bivariado', None,
    'SUPPORTED', 'CONFIRMADA')

# H1 (per cápita) — evidencia con la 15ª fuente: población oficial por UPZ
m5 = modelos[(modelos['modelo'] == 'M5_cestas_percapita_UPZ') &
             (modelos['variable'] == 'estrato_promedio_oficial')]
if len(m5):
    r5 = m5.iloc[0]
    add('H1', 'Vulnerabilidad socioeconómica -> Déficit de infraestructura de aseo',
        'estrato_promedio_oficial', 'cestas_por_1000hab',
        'Binomial Negativa (UPZ, offset=población, controla densidad poblacional)',
        r5['coef'], r5['p_value'], f"IRR={r5['coef_exp_irr']}",
        f"[{r5['ci_low']}, {r5['ci_high']}]", 'SUPPORTED', 'CONFIRMADA', n=int(r5['n']))

# H2 — Déficit de aseo -> Arrojo clandestino
m1_deficit = modelos[(modelos['modelo'] == 'M1_puntos_criticos_UPZ') & (modelos['variable'] == 'deficit_aseo_relativo')].iloc[0]
add('H2', 'Déficit de infraestructura de aseo -> Arrojo clandestino',
    'deficit_aseo_relativo', 'n_puntos_criticos', 'Binomial Negativa multivariable (UPZ, controla estrato)',
    m1_deficit['coef'], m1_deficit['p_value'], f"IRR={m1_deficit['coef_exp_irr']}",
    f"[{m1_deficit['ci_low']}, {m1_deficit['ci_high']}]",
    'SIGNIFICANT_OPPOSITE_DIRECTION', 'NO_RESPALDADA', n=int(m1_deficit['n']))
biv2 = moran_biv[(moran_biv['var_x'] == 'deficit_aseo_relativo') & (moran_biv['var_y'] == 'densidad_puntos_criticos_km2')].iloc[0]
add('H2', 'Déficit de infraestructura de aseo -> Arrojo clandestino',
    'deficit_aseo_relativo', 'densidad_puntos_criticos_km2', 'Moran Bivariado (UPZ)',
    biv2['moran_I_bivariado'], biv2['p_value_sim'], 'Moran I bivariado', None,
    'NOT_SUPPORTED', 'NO_RESPALDADA')
for _, r in proximidad.iterrows():
    add('H2', 'Déficit de infraestructura de aseo -> Arrojo clandestino',
        'n_puntos_criticos', f"distancia_a_{r['infraestructura']}_m", 'Mann-Whitney U (vs. puntos aleatorios)',
        None, r['mannwhitney_p'],
        f"media_puntos_criticos={r['dist_media_puntos_criticos_m']}m vs media_aleatorio={r['dist_media_aleatorio_m']}m",
        None, 'SIGNIFICANT_OPPOSITE_DIRECTION' if r['sig_5pct'] else 'NOT_SUPPORTED', 'NO_RESPALDADA')

# H3 — Vulnerabilidad -> Arrojo clandestino
m1_estrato = modelos[(modelos['modelo'] == 'M1_puntos_criticos_UPZ') & (modelos['variable'] == 'estrato_promedio_oficial')].iloc[0]
add('H3', 'Vulnerabilidad socioeconómica -> Arrojo clandestino',
    'estrato_promedio_oficial', 'n_puntos_criticos', 'Binomial Negativa multivariable (UPZ)',
    m1_estrato['coef'], m1_estrato['p_value'], f"IRR={m1_estrato['coef_exp_irr']}",
    f"[{m1_estrato['ci_low']}, {m1_estrato['ci_high']}]", 'SUPPORTED', 'CONFIRMADA', n=int(m1_estrato['n']))

# H4 — Arrojo -> Delitos
for _, r in robustez[robustez['hipotesis'].str.startswith('H4/H5', na=False) & (robustez['unidad'] == 'Localidad')].iterrows():
    add('H4', 'Arrojo clandestino -> Delitos de alto impacto', r['x'], r['y'], f"Spearman bivariado ({r['transformacion']})",
        r['spearman_rho'], r['p_value'], 'rho', None,
        'SUPPORTED' if r['sig_5pct'] else 'NOT_SUPPORTED', 'PARCIALMENTE_RESPALDADA', n=r['n'])
m3_pc = modelos[(modelos['modelo'] == 'M3_homicidios_localidad') & (modelos['variable'] == 'n_puntos_criticos')].iloc[0]
add('H4', 'Arrojo clandestino -> Delitos de alto impacto', 'n_puntos_criticos', 'homicidios_cont',
    'Binomial Negativa multivariable (localidad, controla déficit+cuadrantes)',
    m3_pc['coef'], m3_pc['p_value'], f"IRR={m3_pc['coef_exp_irr']}", f"[{m3_pc['ci_low']}, {m3_pc['ci_high']}]",
    'NOT_SIGNIFICANT_INCREMENTAL', 'PARCIALMENTE_RESPALDADA', n=int(m3_pc['n']))
for _, r in periodos[periodos['hipotesis'].str.startswith('H4', na=False)].iterrows():
    add('H4', 'Arrojo clandestino -> Delitos de alto impacto', 'n_puntos_criticos', 'homicidios_cont',
        f"Spearman, sub-periodo {r['periodo']}", r['spearman_rho'], r['p_value'], 'rho', None,
        'SUPPORTED', 'PARCIALMENTE_RESPALDADA', n=r['n'])

# H5 — Arrojo -> Emergencias
for _, r in robustez[robustez['hipotesis'].str.startswith('H4/H5', na=False) & (robustez['unidad'] == 'UPZ')].iterrows():
    add('H5', 'Arrojo clandestino -> Emergencias urbanas', r['x'], r['y'], f"Spearman bivariado ({r['transformacion']})",
        r['spearman_rho'], r['p_value'], 'rho', None,
        'SUPPORTED' if r['sig_5pct'] else 'NOT_SUPPORTED', 'PARCIALMENTE_RESPALDADA', n=r['n'])
m2_pc = modelos[(modelos['modelo'] == 'M2_incidentes_UPZ') & (modelos['variable'] == 'n_puntos_criticos')].iloc[0]
add('H5', 'Arrojo clandestino -> Emergencias urbanas', 'n_puntos_criticos', 'n_incidentes_total',
    'Binomial Negativa multivariable (UPZ, controla estrato+distancia bomberos)',
    m2_pc['coef'], m2_pc['p_value'], f"IRR={m2_pc['coef_exp_irr']}", f"[{m2_pc['ci_low']}, {m2_pc['ci_high']}]",
    'NOT_SIGNIFICANT_INCREMENTAL', 'PARCIALMENTE_RESPALDADA', n=int(m2_pc['n']))
biv3 = moran_biv[(moran_biv['var_x'] == 'densidad_puntos_criticos_km2') & (moran_biv['var_y'] == 'densidad_incidentes_km2')].iloc[0]
add('H5', 'Arrojo clandestino -> Emergencias urbanas', 'densidad_puntos_criticos_km2', 'densidad_incidentes_km2',
    'Moran Bivariado (UPZ)', biv3['moran_I_bivariado'], biv3['p_value_sim'], 'Moran I bivariado', None,
    'SUPPORTED_WEAK', 'PARCIALMENTE_RESPALDADA')
for _, r in periodos[periodos['hipotesis'].str.startswith('H5', na=False)].iterrows():
    add('H5', 'Arrojo clandestino -> Emergencias urbanas', 'n_puntos_criticos', 'n_incidentes_total',
        f"Spearman, sub-periodo {r['periodo']}", r['spearman_rho'], r['p_value'], 'rho', None,
        'SUPPORTED' if r['p_value'] < 0.05 else 'NOT_SUPPORTED', 'PARCIALMENTE_RESPALDADA', n=r['n'])

# H6 — Vulnerabilidad -> Delitos
m4_estrato = modelos[(modelos['modelo'] == 'M4_conjunto_delitos_localidad') & (modelos['variable'] == 'estrato_promedio_oficial')].iloc[0]
add('H6', 'Vulnerabilidad socioeconómica -> Delitos de alto impacto', 'estrato_promedio_oficial', 'homicidios_cont',
    'Binomial Negativa multivariable conjunto (localidad, controla déficit+arrojo+cuadrantes)',
    m4_estrato['coef'], m4_estrato['p_value'], f"IRR={m4_estrato['coef_exp_irr']}",
    f"[{m4_estrato['ci_low']}, {m4_estrato['ci_high']}]", 'SUPPORTED', 'CONFIRMADA', n=int(m4_estrato['n']))

# H7 — Vulnerabilidad -> Emergencias
m2_estrato = modelos[(modelos['modelo'] == 'M2_incidentes_UPZ') & (modelos['variable'] == 'estrato_promedio_oficial')].iloc[0]
add('H7', 'Vulnerabilidad socioeconómica -> Emergencias urbanas', 'estrato_promedio_oficial', 'n_incidentes_total',
    'Binomial Negativa multivariable (UPZ)', m2_estrato['coef'], m2_estrato['p_value'],
    f"IRR={m2_estrato['coef_exp_irr']}", f"[{m2_estrato['ci_low']}, {m2_estrato['ci_high']}]",
    'NOT_SUPPORTED', 'NO_RESPALDADA', n=int(m2_estrato['n']))

# Hipótesis conjunta
for _, r in modelos[modelos['modelo'] == 'M4_conjunto_delitos_localidad'].iterrows():
    add('H_CONJUNTA', 'Vulnerabilidad + Déficit + Arrojo + Policía -> Delitos (modelo conjunto)',
        r['variable'], 'homicidios_cont', 'Binomial Negativa multivariable conjunto (localidad)',
        r['coef'], r['p_value'], f"IRR={r['coef_exp_irr']}", f"[{r['ci_low']}, {r['ci_high']}]",
        'SUPPORTED' if r['p_value'] < 0.05 else 'NOT_SIGNIFICANT', 'PARCIALMENTE_RESPALDADA_POR_VULNERABILIDAD', n=int(r['n']))

df = pd.DataFrame(filas)

# ── Corrección por comparaciones múltiples (Benjamini-Hochberg) ──
# La tabla reúne toda la familia de pruebas de hipótesis del estudio, así que
# los p crudos están sujetos a inflación del error tipo I. Se aplica el mismo
# criterio FDR que la fase 08 usa para la matriz de correlaciones, para que el
# nivel de rigor sea consistente entre ambas salidas.
mask = df['p_value'].notna()
rechaza, p_adj, _, _ = multipletests(df.loc[mask, 'p_value'], alpha=0.05, method='fdr_bh')
df['p_value_fdr'] = pd.NA
df.loc[mask, 'p_value_fdr'] = p_adj.round(4)
df['sig_tras_fdr'] = pd.NA
df.loc[mask, 'sig_tras_fdr'] = rechaza

# Un resultado que solo es significativo antes de corregir no puede sostenerse
# como "CONFIRMADA": se degrada explícitamente y queda trazable en la tabla.
degradadas = df[mask & (df['p_value'] < 0.05) & (~df['sig_tras_fdr'].astype(bool))]
df.loc[degradadas.index, 'evidence_level'] = (
    df.loc[degradadas.index, 'evidence_level'].replace('CONFIRMADA', 'PARCIALMENTE_RESPALDADA'))
df.loc[degradadas.index, 'conclusion'] = 'SUPPORTED_ONLY_BEFORE_FDR'

df.to_csv(os.path.join(OUT, 'hypotheses', 'hypothesis_results.csv'), index=False)
print(f"hypotheses/hypothesis_results.csv: {df.shape} ({df['hypothesis_id'].nunique()} hipótesis, {len(df)} pruebas)")
print(df.groupby('hypothesis_id').size())
print(f"\nFDR (Benjamini-Hochberg) sobre {int(mask.sum())} pruebas:")
print(f"  significativas con p crudo < 0.05 : {int((df.loc[mask, 'p_value'] < 0.05).sum())}")
print(f"  sobreviven la corrección FDR       : {int(df['sig_tras_fdr'].fillna(False).astype(bool).sum())}")
if len(degradadas):
    print("  degradadas (solo significativas antes de corregir):")
    for _, r in degradadas.iterrows():
        print(f"    - {r['hypothesis_id']}: {r['method']} (p={r['p_value']} -> p_fdr={r['p_value_fdr']})")
print("\n✅ hypotheses/ completo.")
