"""
Fase 6 (complemento) — Ranking territorial: índice de vulnerabilidad compuesta
DataJam Bogotá 2026

agent.md sección 20-E: identificar las UPZ con mayor concentración conjunta de
vulnerabilidad, déficit, arrojo y emergencias, con la fórmula documentada.
(Este script existía solo como comando suelto en una sesión anterior -- se
formaliza aquí como parte del pipeline reproducible, usando el estrato OFICIAL.)
"""
import os
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)

master_upz = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'))

z = lambda s: (s - s.mean()) / s.std(ddof=0)

# Índice compuesto (25% cada componente, documentado):
# - vulnerabilidad: estrato oficial invertido (menor estrato = más vulnerable = suma positivamente)
# - déficit de aseo relativo
# - densidad de puntos críticos de arrojo
# - densidad de incidentes UAECOB
master_upz['idx_vulnerabilidad_compuesta'] = (
    (-z(master_upz['estrato_promedio_oficial'])) * 0.25 +
    z(master_upz['deficit_aseo_relativo']) * 0.25 +
    z(master_upz['densidad_puntos_criticos_km2']) * 0.25 +
    z(master_upz['densidad_incidentes_km2']) * 0.25
)

top10 = master_upz.sort_values('idx_vulnerabilidad_compuesta', ascending=False)[
    ['cod_upz', 'nombre_upz', 'estrato_promedio_oficial', 'deficit_aseo_relativo',
     'densidad_puntos_criticos_km2', 'densidad_incidentes_km2', 'idx_vulnerabilidad_compuesta']
].head(10)

print('TOP 10 UPZ — índice de vulnerabilidad compuesta (estrato oficial):')
print(top10.to_string(index=False))

master_upz.to_parquet(os.path.join(GOLD, 'modelos', 'ranking_upz.parquet'), index=False)
print(f"\n✅ gold/modelos/ranking_upz.parquet actualizado con estrato oficial.")
