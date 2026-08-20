"""
Script 05 — Build Gold: Tablas Analíticas Maestras (Integrando Residuos, Emergencias y Delitos/Seguridad)
DataJam Bogotá 2026

Fuentes: Silver/ y Silver/capas_geo/
Outputs:
- Gold/gold_upz_analisis.geoparquet & .geojson
- Gold/gold_localidad_analisis.parquet & .csv
- Gold/gold_series_temporales.parquet & .csv
- Gold/gold_diferencial_genero.parquet & .csv
- Gold/gold_delitos_seguridad.parquet & .csv
"""

import os
import re
import unicodedata
import geopandas as gpd
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'Silver')
SILVER_GEO = os.path.join(SILVER, 'capas_geo')
GOLD = os.path.join(BASE, 'Gold')
os.makedirs(GOLD, exist_ok=True)

print("=" * 60)
print("SCRIPT 05 — BUILD GOLD: TABLAS ANALÍTICAS MAESTRAS")
print("=" * 60)

def normalizar_texto(texto):
    if pd.isna(texto):
        return ''
    s = unicodedata.normalize('NFKD', str(texto))
    s = s.encode('ascii', errors='ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9\s]', '', s)
    return s.strip().upper()

# ═══════════════════════════════════════════════════════════════
# 1. Cargar Capas Base Silver & Bronze
# ═══════════════════════════════════════════════════════════════
print("\n📂 1. Cargando capas espaciales Silver y Datos de Seguridad...")
gdf_upz = gpd.read_parquet(os.path.join(SILVER_GEO, 'upz_bogota.geoparquet'))
gdf_loc = gpd.read_parquet(os.path.join(SILVER_GEO, 'localidades_bogota.geoparquet'))
gdf_cestas = gpd.read_parquet(os.path.join(SILVER_GEO, 'cestas_limpia.geoparquet'))
gdf_cont = gpd.read_parquet(os.path.join(SILVER_GEO, 'contenerizacion_limpia.geoparquet'))
gdf_pc = gpd.read_parquet(os.path.join(SILVER_GEO, 'puntos_criticos.geoparquet'))
gdf_cuad = gpd.read_parquet(os.path.join(SILVER_GEO, 'cuadrantes_policia.geoparquet'))
gdf_ebom = gpd.read_parquet(os.path.join(SILVER_GEO, 'estaciones_bomberos.geoparquet'))
df_inc = pd.read_parquet(os.path.join(SILVER, 'incidentes_uaecob_clean.parquet'))
df_rbl = pd.read_parquet(os.path.join(SILVER, 'rbl_series_unificada.parquet'))
df_est = pd.read_parquet(os.path.join(SILVER, 'estrato_indicadores.parquet'))

# Cargar DAILoc para Delitos de Alto Impacto
gdf_dai = gpd.read_file(os.path.join(BRONZE, 'DAILoc.geojson'), engine='pyogrio')

print(f"  UPZs: {len(gdf_upz)} | Localidades: {len(gdf_loc)} | Cuadrantes Policía: {len(gdf_cuad)}")
print(f"  Cestas: {len(gdf_cestas):,} | Contenedores: {len(gdf_cont):,} | Puntos críticos: {len(gdf_pc):,}")
print(f"  Incidentes: {len(df_inc):,} | RBL registros: {len(df_rbl):,}")

# Asegurar CRS EPSG:4326
for g in [gdf_upz, gdf_loc, gdf_cestas, gdf_cont, gdf_pc, gdf_cuad, gdf_ebom]:
    if g.crs is None or g.crs.to_epsg() != 4326:
        g.set_crs(epsg=4326, inplace=True, allow_override=True)

# Calcular área métrica exacta en km2 usando Magna-Sirgas Bogotá (EPSG:3116)
gdf_upz['area_km2'] = (gdf_upz.geometry.to_crs(epsg=3116).area / 1e6).round(3)

# ═══════════════════════════════════════════════════════════════
# 2. Procesar Delitos de Alto Impacto (DAILoc) y Cuadrantes Policía
# ═══════════════════════════════════════════════════════════════
print("\n🚨 2. Procesando Delitos de Alto Impacto (DAI) y Cuadrantes...")

# Extraer tipos de delitos sumando 2018-2026
h_cols = [c for c in gdf_dai.columns if c.startswith('CMH') and 'CONT' in c and not c.startswith(('CMHC', 'CMHP', 'CMHR', 'CMHA', 'CMHB', 'CMHM', 'CMHCE'))]
hp_cols = [c for c in gdf_dai.columns if c.startswith('CMHP') and 'CONT' in c]
hr_cols = [c for c in gdf_dai.columns if c.startswith('CMHR') and 'CONT' in c]
hc_cols = [c for c in gdf_dai.columns if c.startswith('CMHC') and 'CONT' in c and not c.startswith('CMHCE')]
hce_cols = [c for c in gdf_dai.columns if c.startswith('CMHCE') and 'CON' in c]
lp_cols = [c for c in gdf_dai.columns if c.startswith('CMLP') and 'CONT' in c]
ds_cols = [c for c in gdf_dai.columns if c.startswith('CMDS') and 'CONT' in c]
vi_cols = [c for c in gdf_dai.columns if c.startswith('CMVI') and 'CONT' in c]
all_crime_cols = [c for c in gdf_dai.columns if 'CONT' in c or 'CON' in c]

gdf_dai['homicidios_total'] = gdf_dai[h_cols].sum(axis=1)
gdf_dai['hurto_personas_total'] = gdf_dai[hp_cols].sum(axis=1)
gdf_dai['hurto_residencias_total'] = gdf_dai[hr_cols].sum(axis=1)
gdf_dai['hurto_comercio_total'] = gdf_dai[hc_cols].sum(axis=1)
gdf_dai['hurto_celulares_total'] = gdf_dai[hce_cols].sum(axis=1)
gdf_dai['lesiones_personales_total'] = gdf_dai[lp_cols].sum(axis=1)
gdf_dai['delitos_sexuales_total'] = gdf_dai[ds_cols].sum(axis=1)
gdf_dai['violencia_intrafamiliar_total'] = gdf_dai[vi_cols].sum(axis=1)
gdf_dai['delitos_alto_impacto_total'] = gdf_dai[all_crime_cols].sum(axis=1)

gdf_dai['localidad_norm'] = gdf_dai['CMNOMLOCAL'].apply(normalizar_texto)

df_delitos_loc = gdf_dai[[
    'localidad_norm', 'homicidios_total', 'hurto_personas_total', 'hurto_residencias_total',
    'hurto_comercio_total', 'hurto_celulares_total', 'lesiones_personales_total',
    'delitos_sexuales_total', 'violencia_intrafamiliar_total', 'delitos_alto_impacto_total'
]].copy()

# Guardar tabla de delitos de seguridad
df_delitos_loc.to_parquet(os.path.join(GOLD, 'gold_delitos_seguridad.parquet'), index=False)
df_delitos_loc.to_csv(os.path.join(GOLD, 'gold_delitos_seguridad.csv'), index=False)
print(f"  ✅ Delitos de Alto Impacto procesados: {len(df_delitos_loc)} localidades.")

# ═══════════════════════════════════════════════════════════════
# 3. Spatial Joins con UPZ (Infraestructura, Policía, Residuos)
# ═══════════════════════════════════════════════════════════════
print("\n🗺️ 3. Realizando Spatial Joins a nivel UPZ...")

# Spatial Join Cestas -> UPZ
sjoin_cestas = gpd.sjoin(gdf_cestas, gdf_upz[['upz_id', 'geometry']], how='inner', predicate='within')
cestas_por_upz = sjoin_cestas.groupby('upz_id').size().reset_index(name='n_cestas')

# Spatial Join Contenedores -> UPZ
sjoin_cont = gpd.sjoin(gdf_cont, gdf_upz[['upz_id', 'geometry']], how='inner', predicate='within')
cont_por_upz = sjoin_cont.groupby('upz_id').size().reset_index(name='n_contenedores')

# Spatial Join Puntos Críticos -> UPZ
sjoin_pc = gpd.sjoin(gdf_pc, gdf_upz[['upz_id', 'geometry']], how='inner', predicate='within')
pc_por_upz = sjoin_pc.groupby('upz_id').size().reset_index(name='n_puntos_criticos')

# Spatial Join Cuadrantes de Policía -> UPZ
sjoin_cuad = gpd.sjoin(gdf_cuad, gdf_upz[['upz_id', 'geometry']], how='inner', predicate='intersects')
cuad_por_upz = sjoin_cuad.groupby('upz_id').size().reset_index(name='n_cuadrantes_policia')

# Incidentes por texto de UPZ (todos los años 2016-2020)
df_inc['upz_norm'] = df_inc['upz'].apply(normalizar_texto)
gdf_upz['nombre_upz_norm'] = gdf_upz['nombre_upz'].apply(normalizar_texto)

inc_por_upz_texto = df_inc.groupby('upz_norm').agg(
    n_incidentes_total=('año', 'count'),
    n_incendios=('tipo_incidente', lambda x: (x == 'INCENDIO').sum()),
    n_rescates=('tipo_incidente', lambda x: (x == 'RESCATE').sum()),
    n_emergencias_amb=('tipo_incidente', lambda x: (x == 'EMERGENCIA_AMBIENTAL').sum()),
    estrato_promedio=('estrato', 'mean'),
    estrato_modal=('estrato', lambda x: x.mode().iloc[0] if len(x.dropna()) > 0 else np.nan)
).reset_index()

# ═══════════════════════════════════════════════════════════════
# 4. Construir Gold UPZ
# ═══════════════════════════════════════════════════════════════
print("\n🏆 4. Consolidando Gold UPZ...")
gold_upz = gdf_upz.copy()

# Unir conteos espaciales
gold_upz = gold_upz.merge(cestas_por_upz, on='upz_id', how='left')
gold_upz = gold_upz.merge(cont_por_upz, on='upz_id', how='left')
gold_upz = gold_upz.merge(pc_por_upz, on='upz_id', how='left')
gold_upz = gold_upz.merge(cuad_por_upz, on='upz_id', how='left')

# Unir incidentes por match de nombre
gold_upz = gold_upz.merge(
    inc_por_upz_texto,
    left_on='nombre_upz_norm',
    right_on='upz_norm',
    how='left'
)

# Llenar ceros en conteos
for col in ['n_cestas', 'n_contenedores', 'n_puntos_criticos', 'n_cuadrantes_policia',
            'n_incidentes_total', 'n_incendios', 'n_rescates', 'n_emergencias_amb']:
    if col in gold_upz.columns:
        gold_upz[col] = gold_upz[col].fillna(0).astype(int)

# Calcular densidades por km²
gold_upz['densidad_cestas_km2'] = (gold_upz['n_cestas'] / gold_upz['area_km2']).replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
gold_upz['densidad_contenedores_km2'] = (gold_upz['n_contenedores'] / gold_upz['area_km2']).replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
gold_upz['densidad_puntos_criticos_km2'] = (gold_upz['n_puntos_criticos'] / gold_upz['area_km2']).replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
gold_upz['densidad_cuadrantes_km2'] = (gold_upz['n_cuadrantes_policia'] / gold_upz['area_km2']).replace([np.inf, -np.inf], np.nan).fillna(0).round(2)
gold_upz['densidad_incidentes_km2'] = (gold_upz['n_incidentes_total'] / gold_upz['area_km2']).replace([np.inf, -np.inf], np.nan).fillna(0).round(2)

# Índice compuesto de Vulnerabilidad Territorial (0 a 100)
pc_norm = (gold_upz['densidad_puntos_criticos_km2'] - gold_upz['densidad_puntos_criticos_km2'].min()) / \
          (gold_upz['densidad_puntos_criticos_km2'].max() - gold_upz['densidad_puntos_criticos_km2'].min() + 1e-6)
inc_norm = (gold_upz['densidad_incidentes_km2'] - gold_upz['densidad_incidentes_km2'].min()) / \
           (gold_upz['densidad_incidentes_km2'].max() - gold_upz['densidad_incidentes_km2'].min() + 1e-6)
cestas_inv = 1.0 - (gold_upz['densidad_cestas_km2'] - gold_upz['densidad_cestas_km2'].min()) / \
             (gold_upz['densidad_cestas_km2'].max() - gold_upz['densidad_cestas_km2'].min() + 1e-6)

gold_upz['indice_vulnerabilidad_territorial'] = ((pc_norm * 0.4 + inc_norm * 0.4 + cestas_inv * 0.2) * 100).round(1)

# Guardar Gold UPZ
gold_upz.to_parquet(os.path.join(GOLD, 'gold_upz_analisis.geoparquet'), index=False)
gold_upz.to_file(os.path.join(GOLD, 'gold_upz_analisis.geojson'), driver='GeoJSON')
print(f"  ✅ Gold UPZ guardado: {len(gold_upz)} UPZ procesadas.")

# ═══════════════════════════════════════════════════════════════
# 5. Construir Gold Localidad (Unificando Residuos, Bomberos y Policía)
# ═══════════════════════════════════════════════════════════════
print("\n🏆 5. Consolidando Gold Localidad...")

# Normalizar nombres en incidentes
df_inc['localidad_norm'] = df_inc['localidad'].apply(normalizar_texto)

# Agregado de incidentes por localidad
inc_loc = df_inc.groupby('localidad_norm').agg(
    n_incidentes_total=('año', 'count'),
    n_incendios=('tipo_incidente', lambda x: (x == 'INCENDIO').sum()),
    n_rescates=('tipo_incidente', lambda x: (x == 'RESCATE').sum()),
    n_emergencias_amb=('tipo_incidente', lambda x: (x == 'EMERGENCIA_AMBIENTAL').sum()),
    n_accidentes=('tipo_incidente', lambda x: (x == 'ACCIDENTE_TRANSITO').sum()),
    estrato_modal=('estrato', lambda x: x.mode().iloc[0] if len(x.dropna()) > 0 else np.nan),
    estrato_promedio=('estrato', 'mean'),
    pct_estrato_1_2=('estrato', lambda x: (x.isin([1, 2])).mean() * 100),
    pct_estrato_5_6=('estrato', lambda x: (x.isin([5, 6])).mean() * 100),
    total_hombres_expuestos=('hombres_expuestos', 'sum'),
    total_mujeres_expuestas=('mujeres_expuestas', 'sum'),
    total_ninas_expuestas=('niñas_expuestas', 'sum'),
    total_ninos_expuestos=('niños_expuestos', 'sum')
).reset_index()

# Puntos críticos por localidad
MAPA_LOC_ID = {
    1: 'USAQUEN', 2: 'CHAPINERO', 3: 'SANTA FE', 4: 'SAN CRISTOBAL',
    5: 'USME', 6: 'TUNJUELITO', 7: 'BOSA', 8: 'KENNEDY', 9: 'FONTIBON',
    10: 'ENGATIVA', 11: 'SUBA', 12: 'BARRIOS UNIDOS', 13: 'TEUSAQUILLO',
    14: 'LOS MARTIRES', 15: 'ANTONIO NARINO', 16: 'PUENTE ARANDA',
    17: 'LA CANDELARIA', 18: 'RAFAEL URIBE URIBE', 19: 'CIUDAD BOLIVAR', 20: 'SUMAPAZ'
}
gdf_pc['loc_norm'] = gdf_pc['cod_localidad'].map(MAPA_LOC_ID).fillna('')
pc_loc = gdf_pc[gdf_pc['loc_norm'] != ''].groupby('loc_norm').size().reset_index(name='n_puntos_criticos')

# Cestas, Contenedores y Cuadrantes por localidad
gdf_loc['loc_nombre_norm'] = gdf_loc['CMNOMLOCAL'].apply(normalizar_texto)
sjoin_cestas_loc = gpd.sjoin(gdf_cestas, gdf_loc[['loc_nombre_norm', 'geometry']], how='inner', predicate='within')
cestas_loc = sjoin_cestas_loc.groupby('loc_nombre_norm').size().reset_index(name='n_cestas')

sjoin_cont_loc = gpd.sjoin(gdf_cont, gdf_loc[['loc_nombre_norm', 'geometry']], how='inner', predicate='within')
cont_loc = sjoin_cont_loc.groupby('loc_nombre_norm').size().reset_index(name='n_contenedores')

sjoin_cuad_loc = gpd.sjoin(gdf_cuad, gdf_loc[['loc_nombre_norm', 'geometry']], how='inner', predicate='intersects')
cuad_loc = sjoin_cuad_loc.groupby('loc_nombre_norm').size().reset_index(name='n_cuadrantes_policia')

# Residuos por localidad desde IRLoc
residuos_loc = gdf_loc[['loc_nombre_norm', 'CMRTOTAL', 'geometry']].copy().rename(
    columns={'CMRTOTAL': 'residuos_recogidos_total_t'}
)
residuos_loc['area_km2'] = (residuos_loc.geometry.to_crs(epsg=3116).area / 1e6).round(2)

# Unificar Gold Localidad
gold_loc = pd.DataFrame({'localidad': list(MAPA_LOC_ID.values())})
gold_loc['localidad_norm'] = gold_loc['localidad'].apply(normalizar_texto)

gold_loc = gold_loc.merge(inc_loc, on='localidad_norm', how='left')
gold_loc = gold_loc.merge(pc_loc, left_on='localidad_norm', right_on='loc_norm', how='left')
if 'loc_norm' in gold_loc.columns: gold_loc.drop(columns=['loc_norm'], inplace=True)

gold_loc = gold_loc.merge(cestas_loc, left_on='localidad_norm', right_on='loc_nombre_norm', how='left')
if 'loc_nombre_norm' in gold_loc.columns: gold_loc.drop(columns=['loc_nombre_norm'], inplace=True)

gold_loc = gold_loc.merge(cont_loc, left_on='localidad_norm', right_on='loc_nombre_norm', how='left')
if 'loc_nombre_norm' in gold_loc.columns: gold_loc.drop(columns=['loc_nombre_norm'], inplace=True)

gold_loc = gold_loc.merge(cuad_loc, left_on='localidad_norm', right_on='loc_nombre_norm', how='left')
if 'loc_nombre_norm' in gold_loc.columns: gold_loc.drop(columns=['loc_nombre_norm'], inplace=True)

gold_loc = gold_loc.merge(residuos_loc[['loc_nombre_norm', 'residuos_recogidos_total_t', 'area_km2']],
                          left_on='localidad_norm', right_on='loc_nombre_norm', how='left')
if 'loc_nombre_norm' in gold_loc.columns: gold_loc.drop(columns=['loc_nombre_norm'], inplace=True)

# Unir Delitos de Alto Impacto (DAILoc)
gold_loc = gold_loc.merge(df_delitos_loc, on='localidad_norm', how='left')

# Llenar nulos numéricos
for c in ['n_incidentes_total', 'n_incendios', 'n_rescates', 'n_emergencias_amb',
          'n_accidentes', 'n_puntos_criticos', 'n_cestas', 'n_contenedores', 'n_cuadrantes_policia',
          'homicidios_total', 'hurto_personas_total', 'hurto_residencias_total', 'hurto_comercio_total',
          'hurto_celulares_total', 'lesiones_personales_total', 'delitos_sexuales_total',
          'violencia_intrafamiliar_total', 'delitos_alto_impacto_total']:
    if c in gold_loc.columns:
        gold_loc[c] = gold_loc[c].fillna(0).astype(int)

# Población proyectada aproximada (DANE / SDP Bogotá)
POBLACION_BOGOTA_APROX = {
    'USAQUEN': 580000, 'CHAPINERO': 180000, 'SANTA FE': 110000,
    'SAN CRISTOBAL': 410000, 'USME': 400000, 'TUNJUELITO': 200000,
    'BOSA': 820000, 'KENNEDY': 1050000, 'FONTIBON': 430000,
    'ENGATIVA': 890000, 'SUBA': 1350000, 'BARRIOS UNIDOS': 240000,
    'TEUSAQUILLO': 160000, 'LOS MARTIRES': 100000, 'ANTONIO NARINO': 115000,
    'PUENTE ARANDA': 260000, 'LA CANDELARIA': 25000, 'RAFAEL URIBE URIBE': 380000,
    'CIUDAD BOLIVAR': 780000, 'SUMAPAZ': 8000
}
gold_loc['poblacion_estimada'] = gold_loc['localidad_norm'].map(POBLACION_BOGOTA_APROX).fillna(100000)

# Tasas por 10,000 habitantes
gold_loc['tasa_incidentes_10k_hab'] = (gold_loc['n_incidentes_total'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_incendios_10k_hab'] = (gold_loc['n_incendios'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_puntos_criticos_10k_hab'] = (gold_loc['n_puntos_criticos'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_cestas_10k_hab'] = (gold_loc['n_cestas'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_homicidios_10k_hab'] = (gold_loc['homicidios_total'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_violencia_intrafamiliar_10k_hab'] = (gold_loc['violencia_intrafamiliar_total'] / gold_loc['poblacion_estimada'] * 10000).round(2)
gold_loc['tasa_delitos_dai_10k_hab'] = (gold_loc['delitos_alto_impacto_total'] / gold_loc['poblacion_estimada'] * 10000).round(2)

# Clasificación de Vulnerabilidad Socioeconómica y de Seguridad
def clasificar_prioridad(row):
    if row['estrato_modal'] in [1, 2] and (row['n_puntos_criticos'] >= 20 or row['homicidios_total'] >= 300):
        return 'ALTA PRIORIDAD (Vulnerabilidad Crítica)'
    elif row['estrato_modal'] in [2, 3]:
        return 'PRIORIDAD MEDIA'
    else:
        return 'PRIORIDAD BAJA / CONSOLIDADO'

gold_loc['nivel_prioridad_intervencion'] = gold_loc.apply(clasificar_prioridad, axis=1)

# Guardar Gold Localidad
gold_loc.to_parquet(os.path.join(GOLD, 'gold_localidad_analisis.parquet'), index=False)
gold_loc.to_csv(os.path.join(GOLD, 'gold_localidad_analisis.csv'), index=False)
print(f"  ✅ Gold Localidad guardado: {len(gold_loc)} localidades.")

# ═══════════════════════════════════════════════════════════════
# 6. Construir Gold Series Temporales y Género
# ═══════════════════════════════════════════════════════════════
print("\n🏆 6. Consolidando Gold Series Temporales y Género...")

# Residuos mensual por operador
rbl_agg = df_rbl.groupby(['año', 'mes', 'ase']).agg(
    domiciliarios_t=('domiciliarios_t', 'sum'),
    barrido_t=('barrido_t', 'sum'),
    corte_cesped_t=('corte_cesped_t', 'sum'),
    grandes_generadores_t=('grandes_generadores_t', 'sum'),
    arrojo_clandestino_t=('arrojo_clandestino_t', 'sum'),
    total_t=('total_t', 'sum')
).reset_index()

rbl_agg['mes'] = rbl_agg['mes'].fillna(12).astype(int)
rbl_agg['fecha'] = pd.to_datetime(rbl_agg['año'].astype(str) + '-' + rbl_agg['mes'].astype(str).str.zfill(2) + '-01')
rbl_agg = rbl_agg.sort_values('fecha').reset_index(drop=True)

# Incidentes mensual por tipo
inc_agg = df_inc.groupby(['año', 'mes', 'tipo_incidente']).size().unstack(fill_value=0).reset_index()
inc_agg = inc_agg[inc_agg['año'].notna() & inc_agg['mes'].notna()].copy()
inc_agg['fecha'] = pd.to_datetime(inc_agg['año'].astype(int).astype(str) + '-' + inc_agg['mes'].astype(int).astype(str).str.zfill(2) + '-01')
inc_agg = inc_agg.sort_values('fecha').reset_index(drop=True)

rbl_agg.to_parquet(os.path.join(GOLD, 'gold_series_rbl_mensual.parquet'), index=False)
rbl_agg.to_csv(os.path.join(GOLD, 'gold_series_rbl_mensual.csv'), index=False)

inc_agg.to_parquet(os.path.join(GOLD, 'gold_series_incidentes_mensual.parquet'), index=False)
inc_agg.to_csv(os.path.join(GOLD, 'gold_series_incidentes_mensual.csv'), index=False)

genero_estrato = df_inc.groupby(['estrato', 'tipo_incidente']).agg(
    n_eventos=('año', 'count'),
    hombres_expuestos=('hombres_expuestos', 'sum'),
    mujeres_expuestas=('mujeres_expuestas', 'sum'),
    ninas_expuestas=('niñas_expuestas', 'sum'),
    ninos_expuestos=('niños_expuestos', 'sum'),
    hombres_afectados=('hombres_afectados', 'sum'),
    mujeres_afectadas=('mujeres_afectadas', 'sum')
).reset_index()

genero_estrato.to_parquet(os.path.join(GOLD, 'gold_diferencial_genero.parquet'), index=False)
genero_estrato.to_csv(os.path.join(GOLD, 'gold_diferencial_genero.csv'), index=False)
print("  ✅ Gold Series Temporales y Género guardados.")

print(f"\n{'='*60}")
print("RESUMEN DE ARCHIVOS GOLD GENERADOS:")
for f in sorted(os.listdir(GOLD)):
    sz = os.path.getsize(os.path.join(GOLD, f)) / 1024
    print(f"  🌟 {f} ({sz:.1f} KB)")
print("\n✅ Script 05 completado con éxito.")
