"""
Fases 3-4 — Emergencias UAECOB → silver/emergencias/
Corrige: año NaN (bug de sesión anterior, ya resuelto en notebooks/scripts/03),
duplicados exactos, y reemplaza el join UPZ por texto libre (19% match) por
extracción del código numérico oficial embebido en el campo (99.6% match).
"""
import os
import re
import unicodedata
import pandas as pd
import numpy as np
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
trazabilidad_path = os.path.join(os.path.dirname(__file__), 'trazabilidad.csv')


def traza(fuente, transformacion, motivo, n):
    df = pd.read_csv(trazabilidad_path)
    df = pd.concat([df, pd.DataFrame([{
        'fuente': fuente, 'transformacion': transformacion, 'motivo': motivo, 'registros_afectados': n
    }])], ignore_index=True)
    df.to_csv(trazabilidad_path, index=False)
    print(f"  [traza] {fuente} | {transformacion} | {motivo} | n={n}")


def normalizar_texto(texto):
    if pd.isna(texto):
        return ''
    s = unicodedata.normalize('NFKD', str(texto))
    s = s.encode('ascii', errors='ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9\s]', '', s)
    return s.strip().upper()


MESES_ES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}

ARCHIVOS_UAECOB = {
    2016: 'incidentes-atendidos-por-uaecob-2016.csv',
    2017: 'incidentes-atendidos-por-uaecob-2017-1.csv',
    2018: 'incidentes-atendidos-por-uaecob-2018.csv',
    2019: 'incidentes-atendidos-por-uaecob-2019.csv',
    2020: 'incidentes-atendidos-por-uaecob-corte-31-agosto-2020.csv',
}


def clasificar_incidente(servicio):
    if pd.isna(servicio):
        return 'SIN_CLASIFICAR'
    s = str(servicio).upper()
    if '1. INCENDIO' in s or ('INCENDIO' in s and 'FALSA' not in s):
        return 'INCENDIO'
    if 'EMERGENCIA' in s and 'QUIMICA' not in s and 'AMBIENTAL' not in s:
        return 'EMERGENCIA_GENERAL'
    if 'QUIMICA' in s or 'HAZMAT' in s or 'MATERIAL' in s:
        return 'MATERIALES_PELIGROSOS'
    if 'AMBIENTAL' in s:
        return 'EMERGENCIA_AMBIENTAL'
    if 'FALSA' in s or ('QUEMA' in s and 'PROHIBIDA' in s):
        return 'FALSA_ALARMA'
    if 'RESCATE' in s or 'SALVAMENTO' in s:
        return 'RESCATE'
    if 'ACCIDENTE' in s or 'TRÁNSITO' in s or 'TRANSITO' in s or 'VEHICULO' in s:
        return 'ACCIDENTE_TRANSITO'
    if 'ÁRBOL' in s or 'ARBOL' in s or 'VEGETACI' in s:
        return 'EMERGENCIA_AMBIENTAL'
    return 'OTRO'


def extraer_mes(fecha_str):
    if pd.isna(fecha_str):
        return None
    s = str(fecha_str).lower()
    for mes, num in MESES_ES.items():
        if mes in s:
            return num
    return None


def buscar_col(columnas, terminos):
    cols_lower = {c.lower().strip(): c for c in columnas}
    for t in terminos:
        for cl, orig in cols_lower.items():
            if t in cl:
                return orig
    return None


frames = []
dup_removidos_total = 0
for anio, fname in ARCHIVOS_UAECOB.items():
    fpath = os.path.join(BRONZE, fname)
    for enc in ['cp1252', 'latin-1', 'utf-8']:
        try:
            df = pd.read_csv(fpath, sep=';', encoding=enc, on_bad_lines='skip', low_memory=False)
            break
        except Exception:
            continue

    n0 = len(df)
    dup = df.duplicated()
    df = df[~dup].copy()
    dup_removidos_total += int(dup.sum())

    cols = list(df.columns)
    col_fecha = buscar_col(cols, ['fecha del evento', 'fecha'])
    col_localidad = buscar_col(cols, ['localidad'])
    col_upz = buscar_col(cols, ['upz'])
    col_estrato = buscar_col(cols, ['estrato'])
    col_servicio = buscar_col(cols, ['servicio'])
    col_clase = buscar_col(cols, ['clase de servicio'])
    col_h_exp = buscar_col(cols, ['hombres expuestos', 'pobla. expu.hombres'])
    col_m_exp = buscar_col(cols, ['mujeres expuestas', 'pobla. expu.mujeres'])
    col_mn_exp = buscar_col(cols, ['menores niñas expuestas', 'menores niñas'])
    col_mo_exp = buscar_col(cols, ['menores niños expuestos', 'menores niños', 'pobla. expu.menores'])

    df_clean = pd.DataFrame(index=df.index)  # bug de índice vacío ya corregido
    df_clean['anio'] = anio

    if col_fecha:
        df_clean['mes'] = df[col_fecha].apply(extraer_mes)
    else:
        df_clean['mes'] = np.nan

    col_serv_usar = col_clase if col_clase else col_servicio
    df_clean['tipo_incidente'] = df[col_serv_usar].apply(clasificar_incidente) if col_serv_usar else 'SIN_CLASIFICAR'

    df_clean['localidad_norm'] = df[col_localidad].apply(normalizar_texto) if col_localidad else ''
    df_clean['upz_raw'] = df[col_upz].astype(str) if col_upz else ''

    df_clean['estrato'] = pd.to_numeric(df[col_estrato], errors='coerce') if col_estrato else np.nan
    df_clean['estrato'] = df_clean['estrato'].where(df_clean['estrato'].between(1, 6))

    for campo, col in [('hombres_expuestos', col_h_exp), ('mujeres_expuestas', col_m_exp),
                        ('ninas_expuestas', col_mn_exp), ('ninos_expuestos', col_mo_exp)]:
        df_clean[campo] = pd.to_numeric(df[col], errors='coerce') if col else np.nan
    # cobertura real: 2016-2018 no diferencian niñas/niños (columna no existe)
    df_clean['genero_ninez_disponible'] = bool(col_mn_exp) and bool(col_mo_exp)

    frames.append(df_clean)

traza('UAECOB', 'eliminar duplicados exactos por archivo', 'duplicados confirmados en auditoría (58,68,4,3,0 por año)', dup_removidos_total)

df_all = pd.concat(frames, ignore_index=True)

# ── Join UPZ: código numérico embebido en el texto, contra código oficial IRUPZ ──
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet'))
codigos_oficiales = set(gdf_upz['cod_upz'].dropna().astype(int))

df_all['cod_upz'] = df_all['upz_raw'].str.strip().str.extract(r'^(\d+)').astype(float)
match = df_all['cod_upz'].isin(codigos_oficiales)
df_all.loc[~match, 'cod_upz'] = np.nan

traza('UAECOB', 'join a UPZ por código numérico embebido en el campo libre (no por nombre de texto)',
      f'el campo UPZ trae "<codigo> <nombre>" (ej. "103 LA SABANA"); extraer el código sube el match '
      f'de 19% (nombre normalizado, método anterior) a {match.mean()*100:.1f}%',
      int(match.sum()))

df_all.to_parquet(os.path.join(SILVER, 'emergencias', 'incidentes_uaecob.parquet'), index=False)

print(f"\nTotal incidentes: {len(df_all):,}")
print(f"Con UPZ resuelta: {df_all['cod_upz'].notna().sum():,} ({df_all['cod_upz'].notna().mean()*100:.1f}%)")
print(f"Con género/niñez disponible: {df_all['genero_ninez_disponible'].sum():,} ({df_all['genero_ninez_disponible'].mean()*100:.1f}%)")
print(f"Por año: {df_all['anio'].value_counts().sort_index().to_dict()}")
print("✅ silver/emergencias/incidentes_uaecob.parquet guardado.")
