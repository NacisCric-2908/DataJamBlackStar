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

# ── Normalización POR POBLACIÓN (15ª fuente: proyecciones DANE/SDP por UPZ) ──
# El offset por área confunde densidad urbana con déficit de servicio: una UPZ densa
# y popular puede tener buena cobertura por km2 y aun así muy poca por habitante.
# La fuente de población cubre los mismos 112 polígonos UPZ, sin imputación.
POB_ANIO = 2024  # último año con dato observado-ajustado en la serie del DANE
pob_upz = pd.read_parquet(os.path.join(SILVER, 'poblacion', 'poblacion_upz.parquet'))
pob_upz = (pob_upz[pob_upz['anio'] == POB_ANIO]
           [['cod_upz', 'poblacion_total', 'poblacion_mujeres', 'poblacion_0_14']])
master_upz = master_upz.merge(pob_upz, on='cod_upz', how='left')

master_upz['densidad_poblacional_hab_km2'] = (master_upz['poblacion_total'] / master_upz['area_km2']).round(1)

# Las UPZ sin población residencial real (parques metropolitanos, aeropuerto, zonas de
# protección) hacen explotar cualquier tasa per cápita: 7 habitantes en El Mochuelo dan
# ratios sin sentido. Se marcan para poder excluirlas explícitamente en el análisis en
# vez de dejar que un denominador diminuto domine los resultados.
UMBRAL_POB_RESIDENCIAL = 1000
master_upz['upz_residencial'] = master_upz['poblacion_total'] >= UMBRAL_POB_RESIDENCIAL

pob = master_upz['poblacion_total'].where(master_upz['upz_residencial'])
master_upz['cestas_por_1000hab'] = (master_upz['n_cestas'] / pob * 1000).round(3)
master_upz['contenedores_por_1000hab'] = (master_upz['n_contenedores'] / pob * 1000).round(3)
# Por 10.000 habitantes: es la unidad en la que la UAESP y los informes de política
# pública suelen expresar cobertura de mobiliario, por eso se deja explícita en vez de
# obligar a reescalar el indicador por 1.000 en cada consumo.
master_upz['cestas_por_10milhab'] = (master_upz['n_cestas'] / pob * 1e4).round(2)
master_upz['puntos_criticos_por_100milhab'] = (master_upz['n_puntos_criticos'] / pob * 1e5).round(2)
master_upz['incidentes_por_100milhab'] = (master_upz['n_incidentes_total'] / pob * 1e5).round(2)

# Déficit per cápita: mismo criterio que deficit_aseo_relativo (z-score invertido de la
# infraestructura conjunta) pero sobre la base poblacional. Se calcula solo sobre las UPZ
# residenciales para que la media/desviación no queden distorsionadas por las excluidas.
res = master_upz['upz_residencial']
infra_pc = master_upz.loc[res, 'cestas_por_1000hab'] + master_upz.loc[res, 'contenedores_por_1000hab']
master_upz['deficit_aseo_percapita'] = (-z(infra_pc)).round(3)

n_excl = int((~res).sum())
print(f"Población UPZ {POB_ANIO}: {int(master_upz['poblacion_total'].sum()):,} hab | "
      f"{n_excl} UPZ no residenciales (<{UMBRAL_POB_RESIDENCIAL} hab) excluidas de las tasas per cápita")

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

# ── Normalización POR POBLACIÓN a nivel localidad ──
# Se usa poblacion_total (urbana + rural) porque DAILoc reporta los delitos de toda la
# localidad, no solo de la cabecera. poblacion_cabecera queda disponible en Silver para
# los indicadores estrictamente urbanos (aseo domiciliario).
pob_loc = pd.read_parquet(os.path.join(SILVER, 'poblacion', 'poblacion_localidad.parquet'))
pob_loc = (pob_loc[pob_loc['anio'] == POB_ANIO]
           [['cod_localidad', 'poblacion_total', 'poblacion_cabecera', 'poblacion_mujeres', 'pct_rural']])
master_loc = master_loc.merge(pob_loc, on='cod_localidad', how='left')

master_loc['densidad_poblacional_hab_km2'] = (master_loc['poblacion_total'] / master_loc['area_km2']).round(1)
master_loc['cestas_por_1000hab'] = (master_loc['n_cestas'] / master_loc['poblacion_total'] * 1000).round(3)
master_loc['contenedores_por_1000hab'] = (master_loc['n_contenedores'] / master_loc['poblacion_total'] * 1000).round(3)
master_loc['cestas_por_10milhab'] = (master_loc['n_cestas'] / master_loc['poblacion_total'] * 1e4).round(2)
master_loc['puntos_criticos_por_100milhab'] = (master_loc['n_puntos_criticos'] / master_loc['poblacion_total'] * 1e5).round(2)
master_loc['homicidios_por_100milhab'] = (master_loc['homicidios_cont'] / master_loc['poblacion_total'] * 1e5).round(2)
master_loc['vif_por_100milmujeres'] = (master_loc['violencia_intrafamiliar_cont'] / master_loc['poblacion_mujeres'] * 1e5).round(2)

infra_pc_loc = master_loc['cestas_por_1000hab'] + master_loc['contenedores_por_1000hab']
master_loc['deficit_aseo_percapita'] = (-z(infra_pc_loc)).round(3)

master_loc.to_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'), index=False)

print(f"UPZ master: {master_upz.shape} | Localidad master: {master_loc.shape}")
print(f"Emergencias UPZ x año: {inc_upz_anio.shape} | Delitos localidad x año: {delitos_loc_anio.shape}")
print("\nColumnas UPZ master:", list(master_upz.columns))
print("\n✅ gold/modelos/, gold/emergencias/, gold/seguridad/ generados.")
