"""
agent2.md — Fase 20-21: metadata/ + validación de integridad
DataJam Bogotá 2026
"""
import os
import glob
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(BASE, 'data', 'dashboard')
os.makedirs(OUT, exist_ok=True)

# ══════════════════════════════════════════════════════════════════
# metadata/dataset_catalog.csv — un registro por CSV/GeoJSON generado
# ══════════════════════════════════════════════════════════════════
catalogo = []
for carpeta in ['dimensions', 'indicators', 'spatial', 'temporal', 'hypotheses']:
    for fpath in sorted(glob.glob(os.path.join(OUT, carpeta, '*'))):
        fname = os.path.basename(fpath)
        rel = f"dashboard/{carpeta}/{fname}"
        if fname.endswith('.csv'):
            df = pd.read_csv(fpath, nrows=0)
            n_rows = sum(1 for _ in open(fpath)) - 1
            cols = list(df.columns)
            pk = cols[0] if cols else None
        elif fname.endswith('.geojson'):
            import geopandas as gpd
            gdf = gpd.read_file(fpath)
            n_rows, cols, pk = len(gdf), list(gdf.columns), cols[0] if False else gdf.columns[0]
        else:
            continue
        catalogo.append({
            'dataset_name': fname, 'path': rel, 'granularity': carpeta,
            'primary_key': pk, 'source_layer': 'data/gold/', 'row_count': n_rows, 'column_count': len(cols),
        })

dataset_catalog = pd.DataFrame(catalogo)
dataset_catalog.to_csv(os.path.join(OUT, 'metadata', 'dataset_catalog.csv'), index=False)
print(f"metadata/dataset_catalog.csv: {dataset_catalog.shape}")

# ══════════════════════════════════════════════════════════════════
# metadata/data_dictionary.csv — incluye lo disponible Y lo NOT_AVAILABLE_YET
# ══════════════════════════════════════════════════════════════════
NOT_AVAILABLE = [
    dict(dataset='ALL', column='population', description='Población oficial por UPZ/localidad',
         data_type='NOT_AVAILABLE_YET', unit='habitantes', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='Ninguna de las 14 fuentes trae población oficial por UPZ/localidad (ver informe_final.md limitaciones #3)'),
    dict(dataset='ALL', column='population_density', description='Densidad poblacional',
         data_type='NOT_AVAILABLE_YET', unit='hab/km2', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='Depende de population, no disponible'),
    dict(dataset='ALL', column='*_per_100k', description='Tasas por 100.000 habitantes (cestas, contenedores, puntos críticos, delitos, emergencias)',
         data_type='NOT_AVAILABLE_YET', unit='tasa/100k hab', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='Requieren población, no disponible. Se usa *_per_km2 en su lugar'),
    dict(dataset='vulnerability.csv', column='pct_stratum_1 / pct_stratum_2 (por separado)',
         description='Porcentaje de manzanas en estrato 1, y en estrato 2, por separado',
         data_type='NOT_AVAILABLE_YET', unit='%', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='Solo se calculó y validó la combinación pct_estrato_1_2 (no se desagregó 1 vs 2 por separado en el pipeline Gold)'),
    dict(dataset='vulnerability.csv', column='population_stratum_1_2', description='Población en estratos 1-2',
         data_type='NOT_AVAILABLE_YET', unit='habitantes', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='Requiere población, no disponible'),
    dict(dataset='crime (UPZ)', column='high_impact_crimes / crimes_per_km2 a nivel UPZ',
         description='Delitos de alto impacto por UPZ', data_type='NOT_AVAILABLE_YET', unit='conteo',
         source='NOT_AVAILABLE_YET', transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ',
         temporal_granularity='N/A', nullable='N/A',
         motivo='DAILoc (única fuente de delitos) nunca trae desagregación por UPZ, solo localidad. Disponible en crime_localidad.csv'),
    dict(dataset='critical_points', column='persistence', description='Persistencia temporal de puntos críticos',
         data_type='NOT_AVAILABLE_YET', unit='N/A', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='UPZ/Localidad', temporal_granularity='N/A',
         nullable='N/A', motivo='La fuente (puntos críticos de arrojo) es un snapshot sin fecha por punto; nunca se calculó una métrica de persistencia'),
    dict(dataset='critical_points_locations.csv', column='year', description='Año del punto crítico',
         data_type='NOT_AVAILABLE_YET', unit='N/A', source='NOT_AVAILABLE_YET',
         transformation='NOT_AVAILABLE_YET', spatial_granularity='punto', temporal_granularity='N/A',
         nullable='N/A', motivo='La fuente no trae fecha por punto crítico'),
    dict(dataset='ALL', column='intervention_priority_index / risk_score / prediction / recommended_intervention',
         description='Índices de priorización, riesgo o recomendaciones', data_type='BLOCKED', unit='N/A',
         source='N/A', transformation='N/A', spatial_granularity='N/A', temporal_granularity='N/A', nullable='N/A',
         motivo='BLOQUEADO explícitamente por agent2.md secciones 23-24 -- pertenece a una fase posterior (modelo predictivo / Decision Engine)'),
]

DISPONIBLES = [
    dict(dataset='upz.csv', column='localidad_id/localidad_nombre', description='Localidad que contiene la UPZ',
         data_type='str', unit='N/A', source='data/gold/dimensiones/dim_upz.parquet + dim_localidad.parquet',
         transformation='spatial join (representative_point within), técnica ya validada en 05_integracion_espacial',
         spatial_granularity='UPZ', temporal_granularity='snapshot', nullable='No (100% de match)', motivo=''),
    dict(dataset='upz_year.csv', column='emergencies, emergencies_per_km2', description='Emergencias UAECOB por UPZ y año',
         data_type='int/float', unit='conteo; conteo/km2', source='data/gold/emergencias/emergencias_upz_anio.parquet',
         transformation='ninguna adicional (re-exportado)', spatial_granularity='UPZ', temporal_granularity='REAL, 2016-2020',
         nullable='No', motivo=''),
    dict(dataset='upz_year.csv', column='cestas, containers, critical_points, sweeping_route_coverage, pct_stratum_1_2',
         description='Infraestructura de aseo, arrojo y estrato, repetidos por año', data_type='int/float', unit='varía',
         source='data/gold/aseo/, data/gold/socioeconomico/', transformation='ninguna adicional (re-exportado)',
         spatial_granularity='UPZ', temporal_granularity='SNAPSHOT (mismo valor repetido en cada año 2016-2020, NO es serie temporal real)',
         nullable='No', motivo='⚠️ ver informe_final.md: ninguna fuente de aseo/estrato tiene dimensión temporal real'),
    dict(dataset='hypothesis_results.csv', column='todas', description='28 pruebas estadísticas ya ejecutadas (H1-H7 + conjunta)',
         data_type='mixto', unit='N/A', source='10_modelos/, 12_validacion/, 09_estadistica_espacial/, 05_integracion_espacial/',
         transformation='transcripción directa, sin re-ejecutar modelos', spatial_granularity='UPZ/Localidad',
         temporal_granularity='snapshot', nullable='No', motivo=''),
]

data_dict = pd.DataFrame(DISPONIBLES + NOT_AVAILABLE)
data_dict.to_csv(os.path.join(OUT, 'metadata', 'data_dictionary.csv'), index=False)
print(f"metadata/data_dictionary.csv: {data_dict.shape} ({len(DISPONIBLES)} disponibles documentados + {len(NOT_AVAILABLE)} NOT_AVAILABLE_YET/BLOCKED)")

# ══════════════════════════════════════════════════════════════════
# Validación (sección 21 de agent2.md)
# ══════════════════════════════════════════════════════════════════
print("\n=== VALIDACIÓN ===")
errores = []

dim_upz = pd.read_csv(os.path.join(OUT, 'dimensions', 'upz.csv'))
dim_loc = pd.read_csv(os.path.join(OUT, 'dimensions', 'localidades.csv'), dtype={'localidad_id': str})
upz_year = pd.read_csv(os.path.join(OUT, 'indicators', 'upz_year.csv'))

# Integridad: duplicados
if dim_upz['upz_id'].duplicated().any():
    errores.append('upz.csv tiene upz_id duplicados')
if dim_loc['localidad_id'].duplicated().any():
    errores.append('localidades.csv tiene localidad_id duplicados')

# Relaciones: upz_year.upz_id -> dimensions.upz.upz_id
huerfanos = set(upz_year['upz_id']) - set(dim_upz['upz_id'])
if huerfanos:
    errores.append(f'upz_year.csv tiene upz_id no presentes en dimensions/upz.csv: {huerfanos}')
else:
    print('✅ upz_year.upz_id ⊆ dimensions.upz.upz_id')

# Valores: porcentajes fuera de rango, negativos
vuln = pd.read_csv(os.path.join(OUT, 'indicators', 'vulnerability.csv'))
for col in ['pct_stratum_1_2', 'pct_stratum_5_6']:
    if (vuln[col] > 100).any() or (vuln[col] < 0).any():
        errores.append(f'vulnerability.csv: {col} fuera de rango [0,100]')
print('✅ Porcentajes de vulnerability.csv en rango [0,100]' if not errores else '')

for f, col in [('waste_infrastructure_upz.csv', 'cestas'), ('critical_points_upz.csv', 'critical_points')]:
    d = pd.read_csv(os.path.join(OUT, 'indicators', f))
    if (d[col] < 0).any():
        errores.append(f'{f}: {col} tiene valores negativos')
print('✅ Sin conteos negativos en cestas/critical_points')

# Coordenadas válidas (Bogotá aprox)
pc = pd.read_csv(os.path.join(OUT, 'spatial', 'critical_points_locations.csv'))
fuera = ~(pc['latitude'].between(3.5, 5.2) & pc['longitude'].between(-74.6, -73.9))
if fuera.any():
    errores.append(f'critical_points_locations.csv: {fuera.sum()} coordenadas fuera del rango esperado de Bogotá')
else:
    print(f'✅ {len(pc)} coordenadas de critical_points_locations.csv dentro del rango esperado de Bogotá')

if errores:
    print('\n❌ ERRORES DE VALIDACIÓN:')
    for e in errores:
        print(f'  - {e}')
    raise SystemExit(1)
else:
    print('\n✅ Validación de integridad completa, sin errores.')

print("\n✅ metadata/ completo. Capa dashboard/ terminada.")
