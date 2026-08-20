"""
Fase 16.2 - Payload unico del prototipo de tablero
DataJam Bogota 2026

Reune en un solo JSON todo lo que el tablero necesita para funcionar sin red:
indicadores por UPZ y por localidad, resultados de las hipotesis, I de Moran
global, series temporales y la geometria simplificada de 01_geometria.py.

No calcula nada nuevo. Renombra columnas a claves cortas (para que el JSON
embebido pese poco) y redondea. Toda cifra que aparece en el tablero se puede
rastrear hasta una columna de data/gold/ o data/dashboard/.

Sumapaz queda fuera de la capa de localidades por la misma razon documentada
en 01_geometria.py: no tiene estrato oficial y los modelos por localidad
corren con n=19.

Salida: data/dashboard/prototipo/payload.json
"""
import json
import os

import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
DASH = os.path.join(BASE, 'data', 'dashboard')
OUT = os.path.join(DASH, 'prototipo')
os.makedirs(OUT, exist_ok=True)

LOCALIDADES_EXCLUIDAS = {'20'}   # Sumapaz, ver 01_geometria.py


def val(v, dec):
    """None para nulos, redondeo estable para el resto."""
    if v is None or pd.isna(v):
        return None
    return round(float(v), dec)


def construir_upz():
    """Indicadores por UPZ: ranking de Gold + nombre de localidad de la dimension."""
    rk = pd.read_parquet(os.path.join(GOLD, 'modelos', 'ranking_upz.parquet'))
    dim = pd.read_csv(os.path.join(DASH, 'dimensions', 'upz.csv'), dtype={'upz_id': str})
    nombre_loc = dict(zip(dim['upz_id'], dim['localidad_nombre']))

    campos = [
        ('area',     'area_km2',                    3),
        ('estrato',  'estrato_promedio_oficial',    3),
        ('pct12',    'pct_estrato_1_2_oficial',     3),
        ('cestas',   'densidad_cestas_km2',         2),
        ('cont',     'densidad_contenedores_km2',   2),
        ('deficit',  'deficit_aseo_relativo',       3),
        ('arrojo',   'densidad_puntos_criticos_km2', 2),
        ('narrojo',  'n_puntos_criticos',           0),
        ('emerg',    'densidad_incidentes_km2',     2),
        ('nemerg',   'n_incidentes_total',          0),
        ('incendios', 'n_incendios',                0),
        ('cuad',     'densidad_cuadrantes_km2',     2),
        ('ninas',    'n_ninas_expuestas',           0),
        ('ninos',    'n_ninos_expuestos',           0),
        ('distbomb', 'dist_estacion_bomberos_m',    3),
        ('idx',      'idx_vulnerabilidad_compuesta', 3),
    ]

    filas = []
    for _, r in rk.iterrows():
        clave = str(r['cod_upz'])
        fila = {
            'id': clave,
            'nom': r['nombre_upz'],
            'loc': nombre_loc.get(clave, ''),
            'modal': val(r['estrato_modal_oficial'], 0),
        }
        for destino, origen, dec in campos:
            fila[destino] = val(r[origen], dec)
        filas.append(fila)
    return filas


def construir_localidades():
    """Indicadores por localidad: unico nivel donde existen los delitos (DAILoc)."""
    df = pd.read_parquet(os.path.join(GOLD, 'modelos', 'dataset_hipotesis_localidad.parquet'))

    campos = [
        ('area',    'area_km2',                     3),
        ('estrato', 'estrato_promedio_oficial',     3),
        ('pct12',   'pct_estrato_1_2_oficial',      3),
        ('cestas',  'densidad_cestas_km2',          2),
        ('deficit', 'deficit_aseo_relativo',        3),
        ('arrojo',  'densidad_puntos_criticos_km2', 2),
        ('narrojo', 'n_puntos_criticos',            0),
        ('emerg',   'densidad_incidentes_km2',      2),
        ('nemerg',  'n_incidentes_total',           0),
        ('hom',     'homicidios_cont',              0),
        ('homd',    'densidad_homicidios_km2',      2),
        ('vif',     'violencia_intrafamiliar_cont', 0),
        ('delitos', 'delitos_alto_impacto_cont',    0),
    ]

    filas = []
    for _, r in df.iterrows():
        clave = str(r['cod_localidad'])
        if clave in LOCALIDADES_EXCLUIDAS:
            continue
        fila = {'id': clave, 'nom': r['nombre_localidad']}
        for destino, origen, dec in campos:
            fila[destino] = val(r[origen], dec)
        filas.append(fila)
    return filas


# Variables tematicas del tablero. Se dejan fuera las otras dos que trae
# hotspots.csv: densidad_cuadrantes_km2 (es un control de los modelos, no un
# fenomeno) y estrato_promedio_reportado (el proxy de la UAECOB, reemplazado
# por el estrato oficial de Planeacion).
CLUSTER_VARS = [
    'estrato_promedio_oficial',
    'deficit_aseo_relativo',
    'densidad_puntos_criticos_km2',
    'densidad_incidentes_km2',
]


def adjuntar_clusters(filas, nivel):
    """
    Pega a cada entidad su clasificacion Gi* por variable (hotspot / coldspot).

    Se lee hotspots.csv y NO gistar.parquet: en el parquet la columna 'idx' es
    el indice posicional del GeoDataFrame (0, 1, 2...), no el codigo de la UPZ.
    Cruzarlo contra cod_upz produce coincidencias falsas y silenciosas. La
    exportacion a hotspots.csv ya resuelve ese indice a geography_id.

    Se decide por 'cluster_type' y no por la bandera 'significant', porque las
    dos no siempre concuerdan: la UPZ 89 (San Isidro - Patios, Chapinero) sale
    con significant=True y p=0.001 en las seis variables, pero con statistic
    en NaN y etiqueta 'No significativo'. El Gi* no se pudo calcular ahi. La
    etiqueta es el campo conservador, asi que esa UPZ no recibe chip.
    """
    hs = pd.read_csv(os.path.join(DASH, 'spatial', 'hotspots.csv'),
                     dtype={'geography_id': str})
    hs = hs[(hs['geography_level'].str.upper() == nivel.upper())
            & (hs['variable'].isin(CLUSTER_VARS))]

    por_clave = {}
    for _, r in hs.iterrows():
        por_clave.setdefault(r['geography_id'], {})[r['variable']] = r['cluster_type']

    for fila in filas:
        encontrados = por_clave.get(fila['id'], {})
        fila['cluster'] = {v: encontrados.get(v) for v in CLUSTER_VARS}
    return filas


def construir_hipotesis():
    df = pd.read_csv(os.path.join(DASH, 'hypotheses', 'hypothesis_results.csv'))
    return [{
        'id':   r['hypothesis_id'],
        'nom':  r['hypothesis_name'],
        'x':    r['variable_x'],
        'y':    r['variable_y'],
        'met':  r['method'],
        'stat': val(r['statistic'], 3),
        'p':    val(r['p_value'], 3),
        'nn':   val(r['n'], 0),
        'niv':  r['evidence_level'],
    } for _, r in df.iterrows()]


def construir_series():
    """
    Series por variable, sumando todas las unidades geograficas disponibles.

    OJO: trends.csv mezcla tres niveles distintos segun la fuente (UPZ para
    la UAECOB, Localidad para los delitos, ASE para los residuos de la RBL).
    No se filtra por nivel: cada variable existe en uno solo, asi que sumar
    sobre todos los niveles equivale al total ciudad de esa variable.
    """
    df = pd.read_csv(os.path.join(DASH, 'temporal', 'trends.csv'))
    agg = df.groupby(['variable', 'year'], as_index=False)['value'].sum()
    series = {}
    for variable, grupo in agg.groupby('variable'):
        grupo = grupo.sort_values('year')
        series[variable] = [[int(a), round(float(b), 2)]
                            for a, b in zip(grupo['year'], grupo['value'])]
    return series


def construir_moran():
    df = pd.read_parquet(os.path.join(GOLD, 'estadistica_espacial', 'moran_global', 'moran_global.parquet'))
    return [{
        'niv': r['unidad'],
        'var': r['variable'],
        'I':   val(r['moran_I'], 3),
        'p':   val(r['p_value_sim'], 3),
        'sig': bool(r['p_value_sim'] < 0.05),
    } for _, r in df.iterrows()]


def main():
    geo_path = os.path.join(OUT, 'geo.json')
    if not os.path.exists(geo_path):
        raise SystemExit('Falta geo.json. Corre primero 01_geometria.py')
    with open(geo_path, encoding='utf-8') as fh:
        geo = json.load(fh)

    payload = {
        'upz':    adjuntar_clusters(construir_upz(), 'UPZ'),
        'loc':    adjuntar_clusters(construir_localidades(), 'Localidad'),
        'hip':    construir_hipotesis(),
        'trends': construir_series(),
        'moran':  construir_moran(),
        'geo':    geo,
    }

    destino = os.path.join(OUT, 'payload.json')
    with open(destino, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(',', ':'))

    print(f'UPZ:        {len(payload["upz"])}')
    print(f'Localidades:{len(payload["loc"]):4d}')
    print(f'Hipotesis:  {len(payload["hip"])} filas de resultado')
    print(f'Series:     {len(payload["trends"])} variables')
    print(f'Moran:      {len(payload["moran"])} pruebas')
    print(f'Salida:     {os.path.getsize(destino) / 1024:,.0f} KB -> {destino}')


if __name__ == '__main__':
    main()
