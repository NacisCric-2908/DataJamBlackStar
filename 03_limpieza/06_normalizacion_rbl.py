"""
Fases 3-4 — RBL (residuos, 2021-2026) → silver/aseo/rbl_series.parquet
Corrige el hallazgo de auditoría: desde 2023 dos columnas distintas colisionan
al mismo nombre canónico ('arrojo_clandestino_t' y 'total_t') y una sobrescribía
silenciosamente a la otra. Aquí cada concepto queda en su propia columna.
"""
import os
import re
import glob
import pandas as pd
import numpy as np

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'data', 'silver')
trazabilidad_path = os.path.join(os.path.dirname(__file__), 'trazabilidad.csv')


def traza(fuente, transformacion, motivo, n):
    df = pd.read_csv(trazabilidad_path)
    df = pd.concat([df, pd.DataFrame([{
        'fuente': fuente, 'transformacion': transformacion, 'motivo': motivo, 'registros_afectados': n
    }])], ignore_index=True)
    df.to_csv(trazabilidad_path, index=False)
    print(f"  [traza] {fuente} | {transformacion} | {motivo} | n={n}")


MESES_ES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}


def normalizar_nombre_col(col):
    """Mapea encabezados originales a nombres estandarizados.
    IMPORTANTE (fix de auditoría): 'punto limpio' y el total combinado
    quedan en columnas propias, NO se funden con las categorías principales.
    """
    c = str(col).lower().strip()
    if 'punto limpio' in c and 'total' not in c:
        return 'arrojo_clandestino_punto_limpio_t'
    if 'total' in c and 'punto limpio' in c:
        return 'total_combinado_t'  # = total_t + arrojo_clandestino_punto_limpio_t, redundante pero se conserva
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
    if pd.isna(val):
        return np.nan
    s = str(val).strip().replace('\xa0', '').replace(' ', '')
    if s in ('', '-', 'nan', 'NaN'):
        return np.nan
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.')
    elif ',' in s:
        s = s.replace(',', '.')
    elif '.' in s:
        partes = s.split('.')
        if len(partes) == 2 and len(partes[1]) == 3:
            s = s.replace('.', '')
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


def es_fila_total(val):
    s = str(val).lower().strip()
    return any(x in s for x in ['total', 'subtotal', 'suma', 'nan'])


AÑOS = range(2021, 2027)
frames = []
n_con_colision = 0

for year in AÑOS:
    year_dir = os.path.join(BRONZE, str(year))
    if not os.path.isdir(year_dir):
        continue
    for fpath in sorted(glob.glob(os.path.join(year_dir, '*.xlsx'))):
        fname = os.path.basename(fpath)
        mes_num = extraer_mes_de_nombre(fname)
        try:
            df_raw = pd.read_excel(fpath, sheet_name=0, header=None, dtype=str)
            header_row = 0
            for i, row in df_raw.iterrows():
                row_str = ' '.join(row.fillna('').astype(str)).lower()
                if any(x in row_str for x in ['domiciliari', 'ase y', 'concesionario']):
                    header_row = i
                    break
            df = pd.read_excel(fpath, sheet_name=0, header=header_row, dtype=str)
            df.columns = [str(c).strip() for c in df.columns]

            col_map, meta_cols = {}, []
            for col in df.columns:
                nombre = normalizar_nombre_col(col)
                if nombre == '_meta':
                    meta_cols.append(col)
                elif nombre:
                    col_map[col] = nombre
            if 'arrojo_clandestino_punto_limpio_t' in col_map.values():
                n_con_colision += 1

            if not col_map:
                continue
            col_ase = meta_cols[1] if len(meta_cols) > 1 else (meta_cols[0] if meta_cols else df.columns[0])
            col_fecha = meta_cols[0] if meta_cols else None

            df_data = df.copy()
            if col_ase in df_data.columns:
                df_data = df_data[~df_data[col_ase].apply(es_fila_total)]
                df_data = df_data[df_data[col_ase].notna()]
                df_data = df_data[df_data[col_ase].astype(str).str.strip() != '']

            rows = []
            for _, row in df_data.iterrows():
                ase_val = str(row.get(col_ase, '')).strip()
                if not ase_val or ase_val.lower() in ('nan', ''):
                    continue
                ase_clean = ase_val.upper()
                ase_num = None
                for k in ['ASE 1', 'ASE 2', 'ASE 3', 'ASE 4', 'ASE 5', 'ASE 6', 'RPC', 'AGUAS']:
                    if k in ase_clean:
                        ase_num = 'RPC' if k in ('RPC', 'AGUAS') else k.strip()
                        break

                mes_final, año_final = mes_num, year
                if col_fecha and col_fecha != col_ase:
                    fecha_val = str(row.get(col_fecha, ''))
                    if any(str(y) in fecha_val for y in range(2021, 2027)):
                        try:
                            ts = pd.Timestamp(fecha_val)
                            mes_final, año_final = ts.month, ts.year
                        except Exception:
                            pass

                fila = {'anio': año_final, 'mes': mes_final, 'ase': ase_num or ase_clean[:30],
                        'archivo_origen': fname}
                for col_orig, col_clean in col_map.items():
                    fila[col_clean] = limpiar_numero(row.get(col_orig))
                rows.append(fila)

            if rows:
                frames.append(pd.DataFrame(rows))
        except Exception as e:
            print(f"  ❌ Error en {fname}: {e}")

traza('RBL', "separar 'arrojo_clandestino_punto_limpio_t' y 'total_combinado_t' de las categorías principales",
      "desde 2023 existían dos columnas por concepto que colisionaban al mismo nombre canónico "
      "(la segunda sobrescribía a la primera silenciosamente); confirmado en auditoría sobre "
      "Bronze/2023/data-set-abril-2023.xlsx", n_con_colision)

df_silver = pd.concat(frames, ignore_index=True)
COLS_NUM = ['domiciliarios_t', 'barrido_t', 'corte_cesped_t', 'grandes_generadores_t',
            'arrojo_clandestino_t', 'arrojo_clandestino_punto_limpio_t',
            'domiciliarios_especiales_t', 'poda_arboles_t', 'total_t', 'total_combinado_t']
for col in COLS_NUM:
    if col not in df_silver.columns:
        df_silver[col] = np.nan
    else:
        df_silver[col] = pd.to_numeric(df_silver[col], errors='coerce')

df_silver = df_silver.sort_values(['anio', 'mes', 'ase']).reset_index(drop=True)
df_silver['fecha'] = pd.to_datetime(
    df_silver.apply(lambda r: f"{int(r['anio'])}-{int(r['mes']) if pd.notna(r['mes']) else 1:02d}-01", axis=1),
    errors='coerce')

df_silver.to_parquet(os.path.join(SILVER, 'aseo', 'rbl_series.parquet'), index=False)
print(f"\nShape: {df_silver.shape} | años: {sorted(df_silver['anio'].unique())}")
print(f"Archivos con la colisión de columnas (2023-2026): {n_con_colision}")
print("✅ silver/aseo/rbl_series.parquet guardado.")
