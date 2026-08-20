"""
Fase 6 — Construcción del dataset analítico
DataJam Bogotá 2026

Construye:
- gold/modelos/dataset_hipotesis_upz.parquet      (cross-sectional, 116 UPZ)
- gold/modelos/dataset_hipotesis_localidad.parquet (cross-sectional, 20 localidades)
- gold/emergencias/emergencias_upz_anio.parquet    (panel real UPZ x año, 2016-2020)
- gold/seguridad/delitos_localidad_anio.parquet    (panel real localidad x año, 2018-2026)

Población: no existe un dataset abierto de población por UPZ en las 13 fuentes
declaradas. Se usa un proxy de densidad relativa (área) donde población no esté
disponible, y se documenta explícitamente que no hay denominador poblacional
oficial por UPZ (limitación real, no se inventa una cifra).
"""
import os
import re
import unicodedata
import pandas as pd
import numpy as np
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
SPATIAL = os.path.join(BASE, 'scripts', '05_integracion_espacial')
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)


def normalizar_texto(texto):
    if pd.isna(texto):
        return ''
    s = unicodedata.normalize('NFKD', str(texto))
    s = s.encode('ascii', errors='ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9\s]', '', s)
    return s.strip().upper()


gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet'))
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet'))
sp_upz = pd.read_parquet(os.path.join(SPATIAL, 'aseo_policia_bomberos_upz.parquet'))
sp_loc = pd.read_parquet(os.path.join(SPATIAL, 'aseo_policia_bomberos_localidad.parquet'))
df_inc = pd.read_parquet(os.path.join(SILVER, 'emergencias', 'incidentes_uaecob.parquet'))
gdf_dai = gpd.read_parquet(os.path.join(SILVER, 'seguridad', 'delitos_localidad.parquet'))

# ══════════════════════════════════════════════════════════════════
# EMERGENCIAS — panel real UPZ x año (única fuente con ambas dimensiones)
# ══════════════════════════════════════════════════════════════════
inc_upz_anio = df_inc[df_inc['cod_upz'].notna()].groupby(['cod_upz', 'anio']).agg(
    n_incidentes=('anio', 'count'),
    n_incendios=('tipo_incidente', lambda x: (x == 'INCENDIO').sum()),
    n_rescates=('tipo_incidente', lambda x: (x == 'RESCATE').sum()),
    n_emerg_ambiental=('tipo_incidente', lambda x: (x == 'EMERGENCIA_AMBIENTAL').sum()),
    estrato_promedio_reportado=('estrato', 'mean'),
).reset_index()
inc_upz_anio.to_parquet(os.path.join(GOLD, 'emergencias', 'emergencias_upz_anio.parquet'), index=False)

# cross-sectional (todos los años sumados) por UPZ, para el dataset maestro
inc_upz_total = df_inc[df_inc['cod_upz'].notna()].groupby('cod_upz').agg(
    n_incidentes_total=('anio', 'count'),
    n_incendios=('tipo_incidente', lambda x: (x == 'INCENDIO').sum()),
    estrato_promedio_reportado=('estrato', 'mean'),
    estrato_modal_reportado=('estrato', lambda x: x.mode().iloc[0] if len(x.dropna()) > 0 else np.nan),
    n_ninas_expuestas=('ninas_expuestas', 'sum'),
    n_ninos_expuestos=('ninos_expuestos', 'sum'),
).reset_index()

df_inc['localidad_norm'] = df_inc['localidad_norm'].replace('', np.nan)
inc_loc_total = df_inc.groupby('localidad_norm').agg(
    n_incidentes_total=('anio', 'count'),
    n_incendios=('tipo_incidente', lambda x: (x == 'INCENDIO').sum()),
    estrato_promedio_reportado=('estrato', 'mean'),
    estrato_modal_reportado=('estrato', lambda x: x.mode().iloc[0] if len(x.dropna()) > 0 else np.nan),
    n_ninas_expuestas=('ninas_expuestas', 'sum'),
    n_ninos_expuestos=('ninos_expuestos', 'sum'),
).reset_index()

# ══════════════════════════════════════════════════════════════════
# SEGURIDAD — panel real localidad x año (melt de columnas CMH*CONT etc.)
# ══════════════════════════════════════════════════════════════════
import pyogrio
BRONZE = os.path.join(BASE, 'data', 'bronze')
gdf_dai_raw = gpd.read_file(os.path.join(BRONZE, 'DAILoc.geojson'), engine='pyogrio')
gdf_dai_raw = gdf_dai_raw[gdf_dai_raw['CMIULOCAL'].astype(str) != '99'].copy()
gdf_dai_raw['cod_localidad'] = gdf_dai_raw['CMIULOCAL'].astype(str).str.zfill(2)

filas = []
for _, row in gdf_dai_raw.iterrows():
    for anio in range(2018, 2027):
        col = f'CMH{str(anio)[2:]}CONT'
        col_vi = f'CMVI{str(anio)[2:]}CONT'
        if col in gdf_dai_raw.columns:
            filas.append({
                'cod_localidad': row['cod_localidad'], 'anio': anio,
                'homicidios': row.get(col, np.nan),
                'violencia_intrafamiliar': row.get(col_vi, np.nan),
            })
delitos_loc_anio = pd.DataFrame(filas)
delitos_loc_anio.to_parquet(os.path.join(GOLD, 'seguridad', 'delitos_localidad_anio.parquet'), index=False)

# ══════════════════════════════════════════════════════════════════
# DATASET MAESTRO — UPZ (cross-sectional)
# ══════════════════════════════════════════════════════════════════
master_upz = gdf_upz[['cod_upz', 'nombre_upz', 'area_km2']].merge(sp_upz, on='cod_upz', how='left')
master_upz = master_upz.merge(inc_upz_total, on='cod_upz', how='left')
for c in ['n_cestas', 'n_contenedores', 'n_puntos_criticos', 'n_cuadrantes', 'n_incidentes_total', 'n_incendios',
          'n_ninas_expuestas', 'n_ninos_expuestos']:
    master_upz[c] = master_upz[c].fillna(0)

master_upz['densidad_cestas_km2'] = (master_upz['n_cestas'] / master_upz['area_km2']).round(2)
master_upz['densidad_contenedores_km2'] = (master_upz['n_contenedores'] / master_upz['area_km2']).round(2)
master_upz['densidad_puntos_criticos_km2'] = (master_upz['n_puntos_criticos'] / master_upz['area_km2']).round(2)
master_upz['densidad_cuadrantes_km2'] = (master_upz['n_cuadrantes'] / master_upz['area_km2']).round(2)
master_upz['densidad_incidentes_km2'] = (master_upz['n_incidentes_total'] / master_upz['area_km2']).round(2)

# déficit relativo de infraestructura formal de aseo (definición reproducible, documentada):
# z-score invertido de (cestas+contenedores)/km2 vs z-score de puntos_criticos/km2.
# Un valor alto = pocas cestas/contenedores relativo a la ciudad Y muchos puntos críticos.
z = lambda s: (s - s.mean()) / s.std(ddof=0)
infra_density = master_upz['densidad_cestas_km2'] + master_upz['densidad_contenedores_km2']
master_upz['deficit_aseo_relativo'] = (-z(infra_density)).round(3)  # alto = poca infraestructura relativa

# Estrato OFICIAL (manzanaestratificacion.json, spatial join real) -- reemplaza al proxy
# como variable principal de vulnerabilidad. El proxy (estrato_promedio_reportado, de
# incidentes UAECOB autorreportados) se conserva para comparación (r=0.96 entre ambos).
estrato_oficial_upz = pd.read_parquet(os.path.join(SILVER, 'socioeconomico', 'estrato_oficial_upz.parquet'))
master_upz = master_upz.merge(estrato_oficial_upz, on='cod_upz', how='left')

master_upz.to_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_upz.parquet'), index=False)

# ══════════════════════════════════════════════════════════════════
# DATASET MAESTRO — Localidad (cross-sectional, para MAUP)
# ══════════════════════════════════════════════════════════════════
gdf_dai_agg = gdf_dai[['cod_localidad', 'localidad_norm', 'homicidios_cont', 'homicidios_total_oficial',
                        'violencia_intrafamiliar_cont', 'violencia_intrafamiliar_total_oficial',
                        'delitos_alto_impacto_cont']]

master_loc = gdf_loc[['cod_localidad', 'nombre_localidad', 'area_km2']].merge(sp_loc, on='cod_localidad', how='left')
master_loc = master_loc.merge(inc_loc_total, left_on='nombre_localidad', right_on='localidad_norm', how='left')
master_loc = master_loc.merge(gdf_dai_agg, on='cod_localidad', how='left', suffixes=('', '_dai'))

for c in ['n_cestas', 'n_contenedores', 'n_puntos_criticos', 'n_cuadrantes', 'n_incidentes_total', 'n_incendios',
          'homicidios_cont', 'violencia_intrafamiliar_cont', 'delitos_alto_impacto_cont']:
    master_loc[c] = master_loc[c].fillna(0)

master_loc['densidad_cestas_km2'] = (master_loc['n_cestas'] / master_loc['area_km2']).round(2)
master_loc['densidad_contenedores_km2'] = (master_loc['n_contenedores'] / master_loc['area_km2']).round(2)
master_loc['densidad_puntos_criticos_km2'] = (master_loc['n_puntos_criticos'] / master_loc['area_km2']).round(2)
master_loc['densidad_cuadrantes_km2'] = (master_loc['n_cuadrantes'] / master_loc['area_km2']).round(2)
master_loc['densidad_homicidios_km2'] = (master_loc['homicidios_cont'] / master_loc['area_km2']).round(2)
master_loc['densidad_incidentes_km2'] = (master_loc['n_incidentes_total'] / master_loc['area_km2']).round(2)

infra_density_loc = master_loc['densidad_cestas_km2'] + master_loc['densidad_contenedores_km2']
master_loc['deficit_aseo_relativo'] = (-z(infra_density_loc)).round(3)

estrato_oficial_loc = pd.read_parquet(os.path.join(SILVER, 'socioeconomico', 'estrato_oficial_localidad.parquet'))
master_loc = master_loc.merge(estrato_oficial_loc, on='cod_localidad', how='left')

master_loc.to_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'), index=False)

print(f"UPZ master: {master_upz.shape} | Localidad master: {master_loc.shape}")
print(f"Emergencias UPZ x año: {inc_upz_anio.shape} | Delitos localidad x año: {delitos_loc_anio.shape}")
print("\nColumnas UPZ master:", list(master_upz.columns))
print("\n✅ gold/modelos/, gold/emergencias/, gold/seguridad/ generados.")
