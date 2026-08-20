"""
Script 01 — Build Silver: Series RBL Unificadas
DataJam Bogotá 2026

Fuente: XLSX Bronze/2021-2026/
Output: Silver/rbl_series_unificada.parquet

Lógica:
- Leer todos los XLSX mensuales de RBL (2021-2026)
- Detectar fila de encabezado (row 0 = nombres de columnas)
- Estandarizar columnas a nombres canónicos
- Limpiar valores numéricos (separadores de miles, comas decimales)
- Extraer año/mes del nombre de archivo o del campo fecha
- Descartar filas de TOTAL/SUBTOTAL
- Guardar como Parquet
"""

import os
import re
import glob
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'Silver')
os.makedirs(SILVER, exist_ok=True)

print("=" * 60)
print("SCRIPT 01 — BUILD SILVER: RBL SERIES TEMPORALES")
print("=" * 60)

# ── Mapeo de meses en español ──────────────────────────────────
MESES_ES = {
    'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
    'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
    'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
}

# ── Mapeo canónico de columnas ─────────────────────────────────
def normalizar_nombre_col(col):
    """Mapea encabezados originales a nombres estandarizados."""
    c = str(col).lower().strip()
    if any(x in c for x in ['domiciliari']):
        return 'domiciliarios_t'
    if 'barrido' in c and 'corte' not in c:
        return 'barrido_t'
    if any(x in c for x in ['césped', 'cesped', 'corte']):
        return 'corte_cesped_t'
    if 'grandes' in c:
        return 'grandes_generadores_t'
    if any(x in c for x in ['arrojo', 'clandestino', 'voluminoso', 'complementar']):
        return 'arrojo_clandestino_t'
    if any(x in c for x in ['especial']):
        return 'domiciliarios_especiales_t'
    if any(x in c for x in ['poda', 'árbol', 'arbol']):
        return 'poda_arboles_t'
    if 'total' in c:
        return 'total_t'
    if any(x in c for x in ['ase', 'concesionario', 'operador', 'año/mes', 'fecha']):
        return '_meta'
    return None

def limpiar_numero(val):
    """Convierte '22.132,99' o '34.659' o '34659' a float."""
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('\xa0', '').replace(' ', '')
    if s in ('', '-', 'nan', 'NaN'):
        return np.nan
    # Formato europeo: punto=miles, coma=decimal
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        partes = s.split('.')
        if len(partes) == 2 and len(partes[1]) == 3:
            s = s.replace('.', '')  # miles sin decimal
    try:
        return float(s)
    except (ValueError, TypeError):
        return np.nan

def extraer_mes_de_nombre(filename):
    fn = filename.lower()
    for mes, num in MESES_ES.items():
        if mes in fn:
            return num
    return None

def extraer_año_de_nombre(filename):
    m = re.search(r'(20\d{2})', filename)
    return int(m.group(1)) if m else None

def es_fila_total(val):
    """Detecta filas de total/subtotal."""
    s = str(val).lower().strip()
    return any(x in s for x in ['total', 'subtotal', 'suma', 'nan'])

# ── Procesar cada archivo XLSX ─────────────────────────────────
AÑOS = range(2021, 2027)
frames = []
archivos_procesados = 0
archivos_error = 0

for year in AÑOS:
    year_dir = os.path.join(BRONZE, str(year))
    if not os.path.isdir(year_dir):
        continue

    xlsx_files = glob.glob(os.path.join(year_dir, '*.xlsx'))
    print(f"\n📁 {year}: {len(xlsx_files)} archivos")

    for fpath in sorted(xlsx_files):
        fname = os.path.basename(fpath)
        mes_num = extraer_mes_de_nombre(fname)
        if mes_num is None:
            # Intentar extraer del contenido
            print(f"  ⚠️  Sin mes en nombre: {fname}")

        try:
            # Leer sin encabezado para detectar estructura
            df_raw = pd.read_excel(fpath, sheet_name=0, header=None, dtype=str)

            # Encontrar fila de encabezado (fila que contiene 'domiciliari' o 'ase')
            header_row = 0
            for i, row in df_raw.iterrows():
                row_str = ' '.join(row.fillna('').astype(str)).lower()
                if any(x in row_str for x in ['domiciliari', 'ase y', 'concesionario']):
                    header_row = i
                    break

            # Leer con el encabezado correcto
            df = pd.read_excel(fpath, sheet_name=0, header=header_row, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]

            # Identificar columnas
            col_map = {}
            meta_cols = []
            for col in df.columns:
                nombre = normalizar_nombre_col(col)
                if nombre == '_meta':
                    meta_cols.append(col)
                elif nombre:
                    col_map[col] = nombre

            if not col_map:
                print(f"  ⚠️  Sin columnas numéricas reconocidas: {fname}")
                archivos_error += 1
                continue

            # Identificar columna de operador/ASE (primera columna meta)
            col_ase = meta_cols[1] if len(meta_cols) > 1 else (meta_cols[0] if meta_cols else df.columns[0])

            # Extraer fecha de la primera columna meta (si es fecha)
            col_fecha = meta_cols[0] if meta_cols else None

            # Filtrar filas de datos (quitar totales y nulos en ASE)
            df_data = df.copy()
            if col_ase in df_data.columns:
                df_data = df_data[~df_data[col_ase].apply(lambda x: es_fila_total(x))]
                df_data = df_data[df_data[col_ase].notna()]
                df_data = df_data[df_data[col_ase].astype(str).str.strip() != '']

            # Construir DataFrame limpio
            rows = []
            for _, row in df_data.iterrows():
                ase_val = str(row.get(col_ase, '')).strip()
                if not ase_val or ase_val.lower() in ('nan', ''):
                    continue

                # Normalizar nombre del operador
                ase_clean = ase_val.upper()
                ase_num = None
                for k in ['ASE 1', 'ASE 2', 'ASE 3', 'ASE 4', 'ASE 5', 'ASE 6',
                           'RPC', 'AGUAS']:
                    if k in ase_clean:
                        if 'RPC' in k or 'AGUAS' in k:
                            ase_num = 'RPC'
                        else:
                            ase_num = k.strip()
                        break

                # Extraer fecha del campo si existe
                mes_final = mes_num
                año_final = year
                if col_fecha and col_fecha != col_ase:
                    fecha_val = str(row.get(col_fecha, ''))
                    if '2021' in fecha_val or '2022' in fecha_val or '2023' in fecha_val or \
                       '2024' in fecha_val or '2025' in fecha_val or '2026' in fecha_val:
                        try:
                            ts = pd.Timestamp(fecha_val)
                            mes_final = ts.month
                            año_final = ts.year
                        except Exception:
                            pass

                fila = {
                    'año': año_final,
                    'mes': mes_final,
                    'ase': ase_num or ase_clean[:30],
                    'operador': ase_val,
                    'archivo_origen': fname,
                }

                # Añadir columnas numéricas
                for col_orig, col_clean in col_map.items():
                    fila[col_clean] = limpiar_numero(row.get(col_orig))

                rows.append(fila)

            if rows:
                df_clean = pd.DataFrame(rows)
                frames.append(df_clean)
                archivos_procesados += 1
                print(f"  ✅ {fname}: {len(rows)} operadores/ASE extraídos")
            else:
                print(f"  ⚠️  Sin filas de datos: {fname}")
                archivos_error += 1

        except Exception as e:
            print(f"  ❌ Error en {fname}: {e}")
            archivos_error += 1

# ── Consolidar y guardar ───────────────────────────────────────
print(f"\n{'='*60}")
print(f"Procesados: {archivos_procesados} archivos | Errores: {archivos_error}")

if frames:
    df_silver = pd.concat(frames, ignore_index=True)

    # Asegurar columnas numéricas estándar (rellenar con NaN si no existen)
    COLS_NUMERICAS = [
        'domiciliarios_t', 'barrido_t', 'corte_cesped_t',
        'grandes_generadores_t', 'arrojo_clandestino_t',
        'domiciliarios_especiales_t', 'poda_arboles_t', 'total_t'
    ]
    for col in COLS_NUMERICAS:
        if col not in df_silver.columns:
            df_silver[col] = np.nan
        else:
            df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

    # Ordenar
    df_silver = df_silver.sort_values(['año', 'mes', 'ase']).reset_index(drop=True)

    # Añadir campo fecha
    df_silver['fecha'] = pd.to_datetime(
        df_silver.apply(
            lambda r: f"{int(r['año'])}-{int(r['mes']) if pd.notna(r['mes']) else 1:02d}-01",
            axis=1
        ),
        errors='coerce'
    )

    # Guardar Parquet
    out_path = os.path.join(SILVER, 'rbl_series_unificada.parquet')
    df_silver.to_parquet(out_path, index=False, engine='pyarrow')

    print(f"\n✅ Silver guardado: {out_path}")
    print(f"   Shape: {df_silver.shape}")
    print(f"   Años: {sorted(df_silver['año'].dropna().astype(int).unique().tolist())}")
    print(f"   ASEs únicas: {df_silver['ase'].unique().tolist()}")
    print(f"\nEstadísticas de toneladas totales:")
    print(df_silver.groupby('año')['total_t'].agg(['mean', 'sum', 'count']).round(1))
else:
    print("❌ No se generaron datos. Revisar estructura de archivos.")
