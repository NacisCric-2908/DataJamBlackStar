"""
Script 04 — Build Silver: Estratos e Indicadores de Hábitat
DataJam Bogotá 2026

Fuentes:
- Bronze/Esoc.csv (sep=';') — 2.98M lotes con estrato
- Bronze/indicadores-urbanos-habitat-en-cifras-en-las-localidades.xlsx

Output: Silver/estrato_indicadores.parquet

Lógica:
- Leer Esoc.csv en chunks, filtrar estrato 0
- Agregar estrato modal y distribución por código de localidad
- Leer indicadores de hábitat por localidad
- Unificar en tabla de estratos + indicadores por localidad
"""

import os
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'Bronze')
SILVER = os.path.join(BASE, 'Silver')

print("=" * 60)
print("SCRIPT 04 — BUILD SILVER: ESTRATOS E INDICADORES")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# 1. Leer Esoc.csv — estrato por lote
# ═══════════════════════════════════════════════════════════════
print("\n📊 Leyendo Esoc.csv (2.98M lotes)...")
chunks = []
for chunk in pd.read_csv(
    os.path.join(BRONZE, 'Esoc.csv'),
    sep=';', chunksize=300000, low_memory=False
):
    # Filtrar inmediatamente estratos inválidos (0 o NaN)
    chunk['ESoEstrato'] = pd.to_numeric(chunk['ESoEstrato'], errors='coerce')
    chunk = chunk[chunk['ESoEstrato'].between(1, 6)]
    chunks.append(chunk[['ESoCLote', 'ESoChip', 'ESoEstrato']])

df_esoc = pd.concat(chunks, ignore_index=True)
print(f"  Lotes con estrato válido (1-6): {len(df_esoc):,}")

# Extraer código de localidad (primeros 2 dígitos de ESoCLote = código localidad IDECA)
df_esoc['cod_localidad'] = df_esoc['ESoCLote'].astype(str).str[:2]

# Distribución de estratos por localidad
print("\n  Distribución total de estratos (lotes válidos):")
print(df_esoc['ESoEstrato'].value_counts().sort_index())

# ─── Agregar a nivel de localidad ───────────────────────────
def moda_segura(x):
    m = x.mode()
    return m.iloc[0] if len(m) > 0 else np.nan

estrato_loc = df_esoc.groupby('cod_localidad')['ESoEstrato'].agg([
    ('estrato_modal', moda_segura),
    ('estrato_promedio', 'mean'),
    ('estrato_mediana', 'median'),
    ('n_lotes_con_estrato', 'count'),
    ('pct_lotes_1_2', lambda x: (x.isin([1, 2])).mean() * 100),
    ('pct_lotes_5_6', lambda x: (x.isin([5, 6])).mean() * 100),
]).reset_index()

# Distribución por estrato (conteo y porcentaje)
for e in [1, 2, 3, 4, 5, 6]:
    estrato_loc[f'n_lotes_estrato_{e}'] = (
        df_esoc[df_esoc['ESoEstrato'] == e]
        .groupby('cod_localidad')['ESoEstrato'].count()
        .reindex(estrato_loc['cod_localidad'])
        .fillna(0)
        .values
    )

estrato_loc['cod_localidad'] = estrato_loc['cod_localidad'].astype(str).str.zfill(2)
estrato_loc = estrato_loc.round(2)

print(f"\n  Estrato modal por localidad:")
print(estrato_loc[['cod_localidad', 'estrato_modal', 'estrato_promedio',
                    'pct_lotes_1_2', 'pct_lotes_5_6']].to_string(index=False))

# ═══════════════════════════════════════════════════════════════
# 2. Leer Indicadores de Hábitat (XLSX)
# ═══════════════════════════════════════════════════════════════
print("\n📊 Leyendo indicadores-urbanos-habitat.xlsx...")
HABITAT_PATH = os.path.join(BRONZE,
    'indicadores-urbanos-habitat-en-cifras-en-las-localidades.xlsx')

xf = pd.ExcelFile(HABITAT_PATH)
print(f"  Hojas: {xf.sheet_names}")

# Leer todas las hojas y combinar
frames_hab = []
for sheet in xf.sheet_names:
    df_s = pd.read_excel(HABITAT_PATH, sheet_name=sheet)
    df_s.columns = [str(c).strip() for c in df_s.columns]
    df_s = df_s.dropna(how='all')
    df_s['hoja_origen'] = sheet
    frames_hab.append(df_s)
    print(f"  Hoja '{sheet}': {df_s.shape} | cols: {list(df_s.columns)[:6]}")

df_hab = pd.concat(frames_hab, ignore_index=True)

# Identificar columna de localidad y normalizar
col_loc = None
for c in df_hab.columns:
    if 'local' in c.lower():
        col_loc = c
        break

if col_loc:
    df_hab_clean = df_hab.copy()
    df_hab_clean = df_hab_clean.rename(columns={col_loc: 'nombre_localidad'})
    df_hab_clean['nombre_localidad'] = (
        df_hab_clean['nombre_localidad'].astype(str).str.strip().str.upper()
    )
    print(f"\n  Localidades en XLSX:")
    print(df_hab_clean['nombre_localidad'].unique()[:25])
else:
    df_hab_clean = df_hab.copy()
    print("  ⚠️  Columna de localidad no identificada automáticamente")
    print(f"  Columnas disponibles: {list(df_hab.columns)}")

# ═══════════════════════════════════════════════════════════════
# 3. Tabla de Nombres de Localidades (para join)
# ═══════════════════════════════════════════════════════════════
# Mapa oficial: código localidad → nombre (fuente: IDECA / SDP Bogotá)
LOCALIDADES_BOGOTA = {
    '01': 'USAQUÉN',       '02': 'CHAPINERO',    '03': 'SANTA FE',
    '04': 'SAN CRISTÓBAL', '05': 'USME',          '06': 'TUNJUELITO',
    '07': 'BOSA',          '08': 'KENNEDY',       '09': 'FONTIBÓN',
    '10': 'ENGATIVÁ',      '11': 'SUBA',          '12': 'BARRIOS UNIDOS',
    '13': 'TEUSAQUILLO',   '14': 'LOS MÁRTIRES',  '15': 'ANTONIO NARIÑO',
    '16': 'PUENTE ARANDA', '17': 'LA CANDELARIA', '18': 'RAFAEL URIBE URIBE',
    '19': 'CIUDAD BOLÍVAR', '20': 'SUMAPAZ',
}

# Agregar nombre de localidad al DataFrame de estratos
# Los códigos de Esoc.csv pueden ser de 2 dígitos (ej: '10', '11')
# El código oficial es 01-20 (con cero inicial)
estrato_loc['nombre_localidad'] = estrato_loc['cod_localidad'].map(
    LOCALIDADES_BOGOTA
)

# Intentar join con hábitat por nombre
df_final = estrato_loc.copy()
if col_loc and 'nombre_localidad' in df_hab_clean.columns:
    # Simplificar nombre para join
    df_hab_clean['nombre_norm'] = (
        df_hab_clean['nombre_localidad']
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('ascii')
        .str.upper()
        .str.strip()
    )
    df_final['nombre_norm'] = (
        df_final['nombre_localidad'].fillna('')
        .str.normalize('NFKD')
        .str.encode('ascii', errors='ignore')
        .str.decode('ascii')
        .str.upper()
        .str.strip()
    )

    # Seleccionar columnas numéricas del XLSX para el join
    cols_num_hab = [c for c in df_hab_clean.columns
                    if c not in ('nombre_localidad', 'nombre_norm', 'hoja_origen')
                    and pd.api.types.is_numeric_dtype(df_hab_clean[c])]
    print(f"\n  Columnas numéricas del XLSX: {cols_num_hab[:10]}")

    if cols_num_hab:
        df_hab_join = df_hab_clean[['nombre_norm'] + cols_num_hab].drop_duplicates(
            subset='nombre_norm'
        )
        df_final = df_final.merge(df_hab_join, on='nombre_norm', how='left')
        matched = df_final[cols_num_hab[0]].notna().sum() if cols_num_hab else 0
        print(f"  Join hábitat: {matched}/{len(df_final)} localidades con datos")

# ═══════════════════════════════════════════════════════════════
# 4. Guardar Silver
# ═══════════════════════════════════════════════════════════════
# Limpiar columnas auxiliares
for col in ['nombre_norm']:
    if col in df_final.columns:
        df_final = df_final.drop(columns=[col])

out_path = os.path.join(SILVER, 'estrato_indicadores.parquet')
df_final.to_parquet(out_path, index=False, engine='pyarrow')

print(f"\n{'='*60}")
print(f"✅ Silver guardado: {out_path}")
print(f"   Shape: {df_final.shape}")
print(f"\nTabla final:")
print(df_final[['cod_localidad', 'nombre_localidad', 'estrato_modal',
                 'estrato_promedio', 'pct_lotes_1_2', 'pct_lotes_5_6',
                 'n_lotes_con_estrato']].to_string(index=False))
