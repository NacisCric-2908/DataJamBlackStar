"""
Script 03 — Build Silver: Incidentes UAECOB Unificados
DataJam Bogotá 2026

Fuente: Bronze/incidentes-atendidos-por-uaecob-*.csv (2016-2020)
Output: Silver/incidentes_uaecob_clean.parquet

Lógica:
- Leer con encoding Windows-1252 (cp1252), separador ';'
- Normalizar columnas entre años (esquemas distintos)
- Clasificar tipo de incidente
- Extraer mes de la fecha en texto ('viernes 1 de enero de 2016')
- Guardar Parquet con campos canónicos
"""

import os
import re
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'Silver')
os.makedirs(SILVER, exist_ok=True)

print("=" * 60)
print("SCRIPT 03 — BUILD SILVER: INCIDENTES UAECOB")
print("=" * 60)

ARCHIVOS_UAECOB = {
    2016: 'incidentes-atendidos-por-uaecob-2016.csv',
    2017: 'incidentes-atendidos-por-uaecob-2017-1.csv',
    2018: 'incidentes-atendidos-por-uaecob-2018.csv',
    2019: 'incidentes-atendidos-por-uaecob-2019.csv',
    2020: 'incidentes-atendidos-por-uaecob-corte-31-agosto-2020.csv',
}

MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

def clasificar_incidente(servicio):
    """Clasifica el servicio en categorías para la hipótesis."""
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
    """Extrae número de mes de texto como 'viernes 1 de enero de 2016'."""
    if pd.isna(fecha_str):
        return None
    s = str(fecha_str).lower()
    for mes, num in MESES_ES.items():
        if mes in s:
            return num
    return None

def buscar_col(columnas, terminos):
    """Busca una columna que contenga alguno de los términos."""
    cols_lower = {c.lower().strip(): c for c in columnas}
    for t in terminos:
        for cl, orig in cols_lower.items():
            if t in cl:
                return orig
    return None

frames = []

for year, fname in ARCHIVOS_UAECOB.items():
    fpath = os.path.join(BRONZE, fname)
    print(f"\n📄 {year}: {fname}")

    for enc in ['cp1252', 'latin-1', 'utf-8']:
        try:
            df = pd.read_csv(fpath, sep=';', encoding=enc,
                             on_bad_lines='skip', low_memory=False)
            print(f"  Encoding: {enc} | Filas: {len(df):,} | Cols: {df.shape[1]}")
            break
        except Exception as e:
            continue
    else:
        print(f"  ❌ No se pudo leer {fname}")
        continue

    cols = list(df.columns)

    # ── Mapear columnas clave ─────────────────────────────────
    col_fecha    = buscar_col(cols, ['fecha del evento', 'fecha'])
    col_localidad = buscar_col(cols, ['localidad'])
    col_upz      = buscar_col(cols, ['upz'])
    col_estrato  = buscar_col(cols, ['estrato'])
    col_barrio   = buscar_col(cols, ['barrio'])
    col_servicio = buscar_col(cols, ['servicio'])
    col_clase    = buscar_col(cols, ['clase de servicio'])
    col_lat      = buscar_col(cols, ['latitud', 'lat'])
    col_lon      = buscar_col(cols, ['longitud', 'lon'])
    col_hora     = buscar_col(cols, ['hora reporte', 'hora'])

    # ── Columnas de género ────────────────────────────────────
    col_h_exp  = buscar_col(cols, ['hombres expuestos', 'pobla. expu.hombres'])
    col_m_exp  = buscar_col(cols, ['mujeres expuestas', 'pobla. expu.mujeres'])
    col_mn_exp = buscar_col(cols, ['menores niñas expuestas', 'menores niñas'])
    col_mo_exp = buscar_col(cols, ['menores niños expuestos', 'menores niños', 'pobla. expu.menores'])
    col_h_af   = buscar_col(cols, ['hombres afectados', 'pobla. afec.hombres'])
    col_m_af   = buscar_col(cols, ['mujeres afectadas', 'pobla. afec.mujeres'])

    # ── Construir DataFrame limpio ────────────────────────────
    # OJO: pd.DataFrame() vacío no tiene índice, así que asignar un escalar
    # aquí crea una columna de longitud 0 que luego se llena de NaN al
    # alinearse con las columnas siguientes (que sí tienen índice de df).
    df_clean = pd.DataFrame(index=df.index)
    df_clean['año'] = year

    # Fecha y mes
    if col_fecha:
        df_clean['fecha_raw'] = df[col_fecha].astype(str)
        df_clean['mes'] = df[col_fecha].apply(extraer_mes)
    else:
        df_clean['fecha_raw'] = np.nan
        df_clean['mes'] = np.nan

    # Clasificación de incidente
    col_serv_usar = col_clase if col_clase else col_servicio
    if col_serv_usar:
        df_clean['servicio_raw'] = df[col_serv_usar].astype(str)
        df_clean['tipo_incidente'] = df[col_serv_usar].apply(clasificar_incidente)
    else:
        df_clean['servicio_raw'] = np.nan
        df_clean['tipo_incidente'] = 'SIN_CLASIFICAR'

    # Campos de localización
    for campo, col in [('localidad', col_localidad), ('upz', col_upz),
                       ('barrio', col_barrio), ('estrato', col_estrato)]:
        if col:
            df_clean[campo] = df[col].astype(str).str.upper().str.strip()
        else:
            df_clean[campo] = np.nan

    # Limpiar estrato a numérico
    df_clean['estrato'] = pd.to_numeric(df_clean['estrato'], errors='coerce')
    df_clean['estrato'] = df_clean['estrato'].where(df_clean['estrato'].between(1, 6))

    # Coordenadas (2019-2020)
    df_clean['lat'] = pd.to_numeric(df[col_lat], errors='coerce') if col_lat else np.nan
    df_clean['lon'] = pd.to_numeric(df[col_lon], errors='coerce') if col_lon else np.nan

    # Validar coordenadas dentro de Bogotá (-74.3 a -73.9, 4.4 a 4.9)
    if col_lat and col_lon:
        mask_valid = (df_clean['lat'].between(4.0, 5.1) &
                      df_clean['lon'].between(-74.5, -73.7))
        df_clean.loc[~mask_valid, 'lat'] = np.nan
        df_clean.loc[~mask_valid, 'lon'] = np.nan
        pct_geo = mask_valid.mean() * 100
        print(f"  Coordenadas válidas: {pct_geo:.1f}%")

    # Género
    for campo, col in [
        ('hombres_expuestos', col_h_exp), ('mujeres_expuestas', col_m_exp),
        ('niñas_expuestas', col_mn_exp), ('niños_expuestos', col_mo_exp),
        ('hombres_afectados', col_h_af), ('mujeres_afectadas', col_m_af)
    ]:
        df_clean[campo] = pd.to_numeric(df[col], errors='coerce') if col else np.nan

    frames.append(df_clean)
    print(f"  ✅ {len(df_clean):,} registros procesados")
    print(f"  Tipos: {df_clean['tipo_incidente'].value_counts().to_dict()}")

# ── Consolidar y guardar ──────────────────────────────────────
print(f"\n{'='*60}")
df_silver = pd.concat(frames, ignore_index=True)
print(f"Total registros: {len(df_silver):,}")

# Normalizar localidad — quitar números y caracteres extraños
df_silver['localidad'] = (
    df_silver['localidad']
    .str.replace(r'^\d+\s+', '', regex=True)
    .str.strip()
)

# Estadísticas finales
print(f"\nDistribución por año:")
print(df_silver['año'].value_counts().sort_index())
print(f"\nTipos de incidente:")
print(df_silver['tipo_incidente'].value_counts())
print(f"\n% con estrato reportado: {df_silver['estrato'].notna().mean()*100:.1f}%")
print(f"% con coordenadas: {df_silver['lat'].notna().mean()*100:.1f}%")

# Guardar
out_path = os.path.join(SILVER, 'incidentes_uaecob_clean.parquet')
df_silver.to_parquet(out_path, index=False, engine='pyarrow')
print(f"\n✅ Silver guardado: {out_path}")
print(f"   Shape: {df_silver.shape}")
