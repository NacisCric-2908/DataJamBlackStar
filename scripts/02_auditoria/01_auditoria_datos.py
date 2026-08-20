"""
Fase 2 — Auditoría obligatoria de datos (agent.md, sección 3)
DataJam Bogotá 2026

Ejecuta los 16 chequeos exigidos ANTES de cualquier limpieza/transformación.
No corrige nada. Solo documenta. Todo hallazgo va a 02_auditoria/hallazgos.csv
y a 02_auditoria/reporte_auditoria.md (generado por separado a partir de este
run, ver 02_resumen_auditoria.md).
"""
import os
import re
import unicodedata
import pandas as pd
import numpy as np
import geopandas as gpd
import pyogrio

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
OUT = os.path.dirname(__file__)

BOGOTA_LAT = (3.7, 5.1)   # incluye Sumapaz rural
BOGOTA_LON = (-74.5, -73.9)

hallazgos = []


def log(fuente, chequeo, resultado, severidad='info'):
    hallazgos.append({'fuente': fuente, 'chequeo': chequeo, 'resultado': resultado, 'severidad': severidad})
    print(f"[{severidad.upper():5}] {fuente} — {chequeo}: {resultado}")


# ══════════════════════════════════════════════════════════════════
# 1. CAPAS VECTORIALES — geometría, CRS, validez, duplicados, nulos
# ══════════════════════════════════════════════════════════════════
CAPAS_VECTOR = [
    'IRUPZ.geojson', 'IRLoc.geojson', 'DAILoc.geojson', 'cestas.geojson',
    'contenerizacion.geojson', 'puntos_criticos_arrojo_clandestino_residuos.geojson',
    'macrorutas_de_barrido.geojson', 'ebom.geojson', 'cuadrantepolicia.geojson',
]

for capa in CAPAS_VECTOR:
    fpath = os.path.join(BRONZE, capa)
    gdf = gpd.read_file(fpath, engine='pyogrio')
    n = len(gdf)

    log(capa, 'n_registros', n)
    log(capa, 'tipo_geometria', gdf.geom_type.unique().tolist())
    log(capa, 'crs', str(gdf.crs))

    inv = (~gdf.geometry.is_valid).sum()
    log(capa, 'geometrias_invalidas', f"{inv}/{n} ({inv/n*100:.1f}%)",
        'warning' if inv > 0 else 'ok')

    nulls_geom = gdf.geometry.isna().sum()
    log(capa, 'geometrias_nulas', nulls_geom, 'warning' if nulls_geom > 0 else 'ok')

    dup = gdf.drop(columns='geometry').duplicated().sum()
    log(capa, 'filas_duplicadas_por_atributos', dup, 'warning' if dup > 0 else 'ok')

    # nulos por columna (top 5 peores)
    null_pct = gdf.drop(columns='geometry').isna().mean().sort_values(ascending=False)
    peores = null_pct[null_pct > 0].head(5)
    if len(peores) > 0:
        log(capa, 'columnas_con_mas_nulos', {k: f"{v*100:.1f}%" for k, v in peores.items()})

    # registros fuera de Bogotá (para geometrías puntuales, o centroides para polígonos)
    try:
        gdf_wgs = gdf.to_crs(epsg=4326) if gdf.crs and gdf.crs.to_epsg() != 4326 else gdf
        pts = gdf_wgs.geometry.centroid
        fuera = (~(pts.y.between(*BOGOTA_LAT) & pts.x.between(*BOGOTA_LON))).sum()
        log(capa, 'registros_fuera_de_bogota_bbox', f"{fuera}/{n}",
            'warning' if fuera > 0 else 'ok')
    except Exception as e:
        log(capa, 'registros_fuera_de_bogota_bbox', f'ERROR: {e}', 'error')

# ══════════════════════════════════════════════════════════════════
# 2. RBL — cambios de esquema entre años/carpetas 2017-2026
# ══════════════════════════════════════════════════════════════════
print("\n--- RBL: comparación de esquemas por año ---")
esquemas_rbl = {}
for anio in range(2017, 2027):
    year_dir = os.path.join(BRONZE, str(anio))
    if not os.path.isdir(year_dir):
        continue
    archivos = sorted(os.listdir(year_dir))
    for f in archivos[:1]:  # una muestra por año basta para el esquema
        fpath = os.path.join(year_dir, f)
        try:
            if f.endswith('.xlsx'):
                df = pd.read_excel(fpath, header=None, nrows=15, dtype=str)
            else:
                df = pd.read_csv(fpath, header=None, nrows=15, dtype=str,
                                  encoding_errors='ignore', sep=None, engine='python')
            # heurística simple: primera fila con >=3 celdas no vacías = posible encabezado
            header_row = None
            for i, row in df.iterrows():
                non_null = row.notna().sum()
                if non_null >= 3:
                    header_row = i
                    break
            cols = df.iloc[header_row].dropna().astype(str).str.strip().tolist() if header_row is not None else []
            esquemas_rbl[anio] = {'archivo_muestra': f, 'n_archivos_anio': len(archivos), 'columnas_muestra': cols}
        except Exception as e:
            esquemas_rbl[anio] = {'archivo_muestra': f, 'error': str(e)}

for anio, info in esquemas_rbl.items():
    log('RBL', f'esquema_{anio}', info)

anios_con_cols = {a: set(v.get('columnas_muestra', [])) for a, v in esquemas_rbl.items() if 'columnas_muestra' in v}
anios_lista = sorted(anios_con_cols)
if len(anios_lista) > 1:
    base_cols = anios_con_cols[anios_lista[0]]
    for a in anios_lista[1:]:
        diff = base_cols.symmetric_difference(anios_con_cols[a])
        if diff:
            log('RBL', f'diferencia_esquema_{anios_lista[0]}_vs_{a}', list(diff), 'warning')

# ══════════════════════════════════════════════════════════════════
# 3. UAECOB — cambios de esquema entre años
# ══════════════════════════════════════════════════════════════════
print("\n--- UAECOB: comparación de esquemas por año ---")
ARCHIVOS_UAECOB = {
    2016: 'incidentes-atendidos-por-uaecob-2016.csv',
    2017: 'incidentes-atendidos-por-uaecob-2017-1.csv',
    2018: 'incidentes-atendidos-por-uaecob-2018.csv',
    2019: 'incidentes-atendidos-por-uaecob-2019.csv',
    2020: 'incidentes-atendidos-por-uaecob-corte-31-agosto-2020.csv',
}
cols_uaecob = {}
for anio, fname in ARCHIVOS_UAECOB.items():
    fpath = os.path.join(BRONZE, fname)
    for enc in ['cp1252', 'latin-1', 'utf-8']:
        try:
            df = pd.read_csv(fpath, sep=';', encoding=enc, on_bad_lines='skip', low_memory=False, nrows=1000)
            break
        except Exception:
            continue
    cols_uaecob[anio] = set(df.columns)
    log('UAECOB', f'n_columnas_{anio}', df.shape[1])
    dup = df.duplicated().sum()
    log('UAECOB', f'duplicados_muestra_{anio}', dup, 'warning' if dup > 0 else 'ok')

anios_u = sorted(cols_uaecob)
base = cols_uaecob[anios_u[0]]
for a in anios_u[1:]:
    diff = base.symmetric_difference(cols_uaecob[a])
    if diff:
        log('UAECOB', f'diferencia_esquema_{anios_u[0]}_vs_{a}', sorted(diff), 'warning')
    base = cols_uaecob[a]  # comparación incremental año contra año

# ══════════════════════════════════════════════════════════════════
# 4. Esoc.csv — duplicados, nulos, extremos
# ══════════════════════════════════════════════════════════════════
print("\n--- Esoc.csv ---")
df_esoc = pd.read_csv(os.path.join(BRONZE, 'Esoc.csv'), sep=';', dtype=str)
log('Esoc.csv', 'n_registros', len(df_esoc))
dup_lote = df_esoc['ESoCLote'].duplicated().sum()
log('Esoc.csv', 'ESoCLote_duplicados', dup_lote, 'warning' if dup_lote > 0 else 'ok')
estrato_num = pd.to_numeric(df_esoc['ESoEstrato'], errors='coerce')
fuera_rango = (~estrato_num.between(0, 6)).sum()
log('Esoc.csv', 'estrato_fuera_de_rango_0_6', fuera_rango, 'warning' if fuera_rango > 0 else 'ok')
log('Esoc.csv', 'distribucion_estrato', estrato_num.value_counts(dropna=False).sort_index().to_dict())

# ══════════════════════════════════════════════════════════════════
# 5. Guardar hallazgos
# ══════════════════════════════════════════════════════════════════
df_h = pd.DataFrame(hallazgos)
df_h['resultado'] = df_h['resultado'].astype(str)
out_path = os.path.join(OUT, 'hallazgos.csv')
df_h.to_csv(out_path, index=False)
print(f"\n✅ Auditoría completa. {len(df_h)} hallazgos guardados en {out_path}")
print(f"   Warnings: {(df_h['severidad']=='warning').sum()} | Errors: {(df_h['severidad']=='error').sum()}")
