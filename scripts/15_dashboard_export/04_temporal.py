"""
agent2.md — Fase 15: temporal/trends.csv
DataJam Bogotá 2026

Formato largo (year, geography_level, geography_id, variable, value).
Solo variables con serie temporal REAL ya calculada:
- emergencias UPZ x año (2016-2020)
- delitos localidad x año (2018-2026, homicidios y violencia intrafamiliar)
- RBL por ASE x mes/año (2021-2026)
NO incluye cestas/contenedores/puntos_críticos/estrato: son snapshots sin
serie temporal real (ver limitación documentada en el informe final).
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
OUT = os.path.join(BASE, 'data', 'dashboard')
os.makedirs(OUT, exist_ok=True)

filas = []

emerg = pd.read_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'))
for col, var in [('n_incidentes', 'emergencies'), ('n_incendios', 'fires'),
                  ('n_rescates', 'rescues'), ('n_emerg_ambiental', 'environmental_emergencies')]:
    sub = emerg[['cod_upz', 'anio', col]].rename(columns={'cod_upz': 'geography_id', 'anio': 'year', col: 'value'})
    sub['geography_level'] = 'UPZ'
    sub['variable'] = var
    filas.append(sub[['year', 'geography_level', 'geography_id', 'variable', 'value']])

delitos = pd.read_parquet(os.path.join(GOLD, 'seguridad', 'delitos_localidad_anio.parquet'))
for col, var in [('homicidios', 'homicides'), ('violencia_intrafamiliar', 'domestic_violence')]:
    sub = delitos[['cod_localidad', 'anio', col]].rename(columns={'cod_localidad': 'geography_id', 'anio': 'year', col: 'value'})
    sub['geography_level'] = 'Localidad'
    sub['variable'] = var
    filas.append(sub[['year', 'geography_level', 'geography_id', 'variable', 'value']])

rbl = pd.read_parquet(os.path.join(GOLD, 'aseo', 'rbl_series_por_ase.parquet'))
rbl_anual = rbl.groupby(['ase', 'anio'])['total_t'].sum().reset_index()
sub = rbl_anual.rename(columns={'ase': 'geography_id', 'anio': 'year', 'total_t': 'value'})
sub['geography_level'] = 'ASE'
sub['variable'] = 'residuos_total_t'
filas.append(sub[['year', 'geography_level', 'geography_id', 'variable', 'value']])

trends = pd.concat(filas, ignore_index=True)
trends.to_csv(os.path.join(OUT, 'temporal', 'trends.csv'), index=False)

print(f"temporal/trends.csv: {trends.shape}")
print(trends.groupby(['geography_level', 'variable'])['year'].agg(['min', 'max', 'count']))
print("\n✅ temporal/ completo.")
