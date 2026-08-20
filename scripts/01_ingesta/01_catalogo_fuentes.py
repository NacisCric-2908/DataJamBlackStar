"""
Fase 1 — Ingesta: catálogo de fuentes Bronze
DataJam Bogotá 2026 — pipeline agent.md

Inventaría automáticamente todos los archivos de Bronze/, determina formato,
tipo de dato (tabular/vectorial), dimensiones, CRS (si aplica) y cobertura
temporal aproximada por nombre de archivo/carpeta. No modifica nada.

Output: 01_ingesta/catalogo_fuentes.csv
"""
import os
import glob
import json
import pandas as pd
import geopandas as gpd
import pyogrio

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
OUT = os.path.dirname(__file__)

FUENTES_DECLARADAS = {
    'rbl': ('Datos de residuos recogidos (RBL)', 'UAESP',
            'https://datosabiertos.bogota.gov.co/dataset/datos-residuos-recogidos-rbl-uaesp'),
    'incidentes-atendidos-por-uaecob': ('Incidente atendido por bomberos', 'UAECOB',
            'https://datosabiertos.bogota.gov.co/dataset/incidente-atendido-por-bomberos'),
    'DAILoc.geojson': ('Delito de alto impacto', 'Secretaría Distrital de Seguridad, Convivencia y Justicia',
            'https://datosabiertos.bogota.gov.co/dataset/delito-de-alto-impacto-bogota-d-c'),
    'cuadrantepolicia.geojson': ('Cuadrantes de policía', 'MEBOG',
            'https://datosabiertos.bogota.gov.co/dataset/cuadrantes-de-policia-bogota-d-c'),
    'Esoc.csv': ('Estrato socioeconómico', 'Secretaría Distrital de Planeación / IDECA',
            'https://datosabiertos.bogota.gov.co/dataset/estrato-socioeconomico-bogota-d-c'),
    'IRUPZ.geojson': ('Mapa de Referencia — UPZ', 'IDECA',
            'https://datosabiertos.bogota.gov.co/dataset/mapa-de-referencia'),
    'IRLoc.geojson': ('Mapa de Referencia — localidades', 'IDECA',
            'https://datosabiertos.bogota.gov.co/dataset/mapa-de-referencia'),
    'cestas.geojson': ('Cestas', 'UAESP',
            'https://datosabiertos.bogota.gov.co/dataset/cestas-bogota-d-c'),
    'contenerizacion.geojson': ('Contenerización', 'UAESP',
            'https://datosabiertos.bogota.gov.co/dataset/contenerizacion-bogota-d-c'),
    'puntos_criticos_arrojo_clandestino_residuos.geojson': ('Puntos críticos de arrojo clandestino', 'UAESP',
            'https://datosabiertos.bogota.gov.co/dataset/puntos-criticos-arrojo-clandestino-residuos-bogota-d-c'),
    'macrorutas_de_barrido.geojson': ('Macrorutas de barrido', 'UAESP',
            'https://datosabiertos.bogota.gov.co/dataset/macrorutas-de-barrido-bogota-d-c'),
    'ebom.geojson': ('Estación de bomberos', 'UAECOB',
            'https://datosabiertos.bogota.gov.co/dataset/estacion-de-bomberos-para-bogota'),
    'indicadores-urbanos-habitat-en-cifras-en-las-localidades.xlsx': ('Hábitat en cifras — indicadores urbanos',
            'Secretaría Distrital del Hábitat',
            'https://datosabiertos.bogota.gov.co/dataset/habitat-en-cifras-en-las-localidades-indicadores-urbanos'),
    '202503_upz_proyeccion_retroproyeccion_poblacion_2005_2035.ods': (
            'Proyecciones de población 2005-2035 (UPZ) — 15ª fuente, resuelve la normalización per cápita',
            'Secretaría Distrital de Planeación / DANE',
            'https://datosabiertos.bogota.gov.co/dataset/proyecciones-y-retroproyecciones-de-poblacion-2005-2035'),
    '202503_localidad_proyeccion_retroproyeccion_poblacion_2005_2035.ods': (
            'Proyecciones de población 2005-2035 (localidad) — 15ª fuente',
            'Secretaría Distrital de Planeación / DANE',
            'https://datosabiertos.bogota.gov.co/dataset/proyecciones-y-retroproyecciones-de-poblacion-2005-2035'),
    'manzanaestratificacion.json': ('Estratificación para Bogotá (manzana) — 14ª fuente, incorporada tras el proxy',
            'Secretaría Distrital de Planeación',
            'https://datosabiertos.bogota.gov.co/dataset/estratificacion-para-bogota'),
}


def clasificar(fname, carpeta_anio):
    if carpeta_anio is not None:
        return FUENTES_DECLARADAS['rbl']
    for clave, meta in FUENTES_DECLARADAS.items():
        if clave.lower() in fname.lower():
            return meta
    return ('NO DECLARADA (fuera de las 13 fuentes)', 'Desconocida', '')


def inspeccionar_geo(fpath):
    try:
        info = pyogrio.read_info(fpath)
        return {
            'n_filas': info.get('features'),
            'n_columnas': len(info.get('fields', [])),
            'crs_epsg': info.get('crs'),
            'tipo_geometria': info.get('geometry_type'),
            'columnas': ';'.join(info.get('fields', [])),
        }
    except Exception as e:
        return {'error': str(e)}


def inspeccionar_tabular(fpath, ext):
    try:
        if ext == '.csv':
            df = pd.read_csv(fpath, sep=None, engine='python', nrows=5, encoding_errors='ignore')
        elif ext in ('.xlsx',):
            df = pd.read_excel(fpath, nrows=5)
        else:
            return {}
        return {'n_columnas': df.shape[1], 'columnas': ';'.join(str(c) for c in df.columns)}
    except Exception as e:
        return {'error': str(e)}


registros = []
for root, dirs, files in os.walk(BRONZE):
    if 'gdb_mr_v06_26.gdb' in root:
        continue  # se cataloga aparte (geodatabase multi-capa)
    for f in files:
        fpath = os.path.join(root, f)
        rel = os.path.relpath(fpath, BRONZE)
        ext = os.path.splitext(f)[1].lower()
        carpeta_anio = os.path.basename(root) if os.path.basename(root).isdigit() else None
        nombre, entidad, enlace = clasificar(f, carpeta_anio)
        size_mb = os.path.getsize(fpath) / 1024**2

        row = {
            'archivo': rel,
            'fuente_declarada': nombre,
            'entidad': entidad,
            'enlace_portal': enlace,
            'extension': ext,
            'tamano_mb': round(size_mb, 3),
            'carpeta_anio': carpeta_anio,
        }

        if ext in ('.geojson', '.json'):
            row.update(inspeccionar_geo(fpath))
        elif ext in ('.csv', '.xlsx'):
            row.update(inspeccionar_tabular(fpath, ext))

        registros.append(row)

# Catalogar el geodatabase aparte (multi-capa)
gdb_path = os.path.join(BRONZE, 'gdb_mr_v06_26.gdb')
if os.path.isdir(gdb_path):
    capas = pyogrio.list_layers(gdb_path)
    for nombre_capa, tipo_geom in capas:
        try:
            info = pyogrio.read_info(gdb_path, layer=nombre_capa)
            registros.append({
                'archivo': f'gdb_mr_v06_26.gdb::{nombre_capa}',
                'fuente_declarada': 'Estrato socioeconómico' if nombre_capa == 'ESoc' else 'NO DECLARADA (capa extra del GDB de Catastro)',
                'entidad': 'IDECA / Catastro Bogotá',
                'enlace_portal': FUENTES_DECLARADAS['Esoc.csv'][2] if nombre_capa == 'ESoc' else '',
                'extension': '.gdb',
                'tamano_mb': None,
                'carpeta_anio': None,
                'n_filas': info.get('features'),
                'n_columnas': len(info.get('fields', [])),
                'crs_epsg': info.get('crs'),
                'tipo_geometria': tipo_geom,
                'columnas': ';'.join(info.get('fields', [])),
            })
        except Exception as e:
            registros.append({'archivo': f'gdb_mr_v06_26.gdb::{nombre_capa}', 'error': str(e)})

df_cat = pd.DataFrame(registros)
out_path = os.path.join(OUT, 'catalogo_fuentes.csv')
df_cat.to_csv(out_path, index=False)

print(f"Catálogo generado: {out_path}")
print(f"Total de archivos/capas catalogados: {len(df_cat)}")
print(f"\nFuentes declaradas cubiertas:")
print(df_cat['fuente_declarada'].value_counts())
