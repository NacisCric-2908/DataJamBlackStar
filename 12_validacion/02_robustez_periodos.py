"""
Fase 12 (complemento) — Robustez a distintos períodos temporales (agent.md §19)
DataJam Bogotá 2026
"""
import os
import pandas as pd
from scipy import stats

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
OUT = os.path.dirname(__file__)

inc = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))
delitos = pd.read_parquet(os.path.join(GOLD, 'seguridad', 'delitos_localidad_anio.parquet'))
master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))
master_loc = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

resultados = []
for periodo, anios in [('2016-2017', [2016, 2017]), ('2019-2020', [2019, 2020])]:
    sub = inc[inc['anio'].isin(anios)].groupby('cod_upz')['n_incidentes'].sum().reset_index()
    d = master_upz[['cod_upz', 'n_puntos_criticos']].merge(sub, on='cod_upz', how='left').fillna(0)
    r, p = stats.spearmanr(d['n_puntos_criticos'], d['n_incidentes'])
    resultados.append({'hipotesis': 'H5 (arrojo vs incidentes, UPZ)', 'periodo': periodo,
                        'spearman_rho': round(r, 3), 'p_value': round(p, 4), 'n': len(d)})

for periodo, anios in [('2018-2021', [2018, 2019, 2020, 2021]), ('2022-2026', [2022, 2023, 2024, 2025, 2026])]:
    sub = delitos[delitos['anio'].isin(anios)].groupby('cod_localidad')['homicidios'].sum().reset_index()
    d = master_loc[['cod_localidad', 'n_puntos_criticos']].merge(sub, on='cod_localidad', how='left').fillna(0)
    r, p = stats.spearmanr(d['n_puntos_criticos'], d['homicidios'])
    resultados.append({'hipotesis': 'H4 (arrojo vs homicidios, localidad)', 'periodo': periodo,
                        'spearman_rho': round(r, 3), 'p_value': round(p, 4), 'n': len(d)})

df = pd.DataFrame(resultados)
print(df.to_string(index=False))
df.to_csv(os.path.join(OUT, 'robustez_periodos_temporales.csv'), index=False)
print(f"\n✅ Robustez a periodos temporales guardada en 12_validacion/robustez_periodos_temporales.csv")
