"""
Fases 3-4 — Población oficial por UPZ y localidad → silver/poblacion/
DataJam Bogotá 2026

15ª fuente: "Proyecciones y retroproyecciones de población (2005-2035)"
(Secretaría Distrital de Planeación, calculadas por el DANE sobre el Censo 2018)
https://datosabiertos.bogota.gov.co/dataset/proyecciones-y-retroproyecciones-de-poblacion-2005-2035

Incorporada para resolver la limitación estructural declarada en versiones
previas del informe: sin población por UPZ los modelos solo podían normalizar
por área (km2), lo que confunde densidad urbana con déficit real de servicio.
El DANE publica estas proyecciones sobre exactamente los mismos 112 polígonos
UPZ que usa el pipeline (verificado: 112/112 en el join), sin requerir
imputación ni aproximación espacial.

Los dos archivos de la fuente tienen estructuras distintas y se tratan aparte:
  - UPZ:       grupos quinquenales (Hombres_0-4 ...), solo 'Cabecera Municipal'.
  - Localidad: edades año a año (Hombres_0 ... Hombres_100) y filas separadas
               para 'Cabecera Municipal' y 'Centro Poblado y Rural Disperso'.
               Se conservan ambos totales por separado, porque el denominador
               correcto depende del indicador: los delitos (DAILoc) cubren toda
               la localidad, mientras que el servicio de aseo domiciliario que
               analiza el proyecto es urbano.

Salida:
  silver/poblacion/poblacion_upz.parquet        (UPZ x año, 2005-2035)
  silver/poblacion/poblacion_localidad.parquet  (localidad x año)
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'data', 'silver', 'poblacion')
os.makedirs(SILVER, exist_ok=True)

URBANO = 'Cabecera Municipal'
TRAZA = []


def traza(fuente, transformacion, motivo, n):
    TRAZA.append(dict(fuente=fuente, transformacion=transformacion, motivo=motivo,
                      registros_afectados=n))
    print(f"  [{fuente}] {transformacion} -> {n}")


def edad_de(col):
    """Extrae la edad inicial de 'Hombres_0-4' o 'Hombres_7'. None si no aplica."""
    resto = str(col).split('_', 1)[-1]
    inicio = resto.split('-')[0]
    return int(inicio) if inicio.isdigit() else None


def totales_por_sexo(d, etiqueta):
    """Agrega los grupos de edad (quinquenales o año a año) a totales.

    'poblacion_0_14' permite normalizar los incidentes UAECOB que reportan
    niñas/niños expuestos (enfoque diferencial declarado en el proyecto).
    """
    cols_h = [c for c in d.columns if str(c).startswith('Hombres_')]
    cols_m = [c for c in d.columns if str(c).startswith('Mujeres_')]
    if not cols_h or not cols_m:
        raise ValueError(f'{etiqueta}: no se encontraron columnas Hombres_*/Mujeres_*')

    ninez = [c for c in cols_h + cols_m
             if (e := edad_de(c)) is not None and e < 15]

    out = pd.DataFrame({
        'poblacion_total':    d[cols_h + cols_m].sum(axis=1),
        'poblacion_hombres':  d[cols_h].sum(axis=1),
        'poblacion_mujeres':  d[cols_m].sum(axis=1),
        'poblacion_0_14':     d[ninez].sum(axis=1),
    }, index=d.index)
    traza(etiqueta, f'agregar {len(cols_h)+len(cols_m)} columnas de edad a totales por sexo y niñez (0-14)',
          'la fuente viene desagregada por sexo y edad; el pipeline necesita totales y el corte de niñez',
          len(d))
    return out


def leer(archivo, col_codigo, etiqueta):
    """El .ods trae 4 filas de preámbulo antes del encabezado real."""
    d = pd.read_excel(os.path.join(BRONZE, archivo), engine='odf',
                      sheet_name='Hoja1', header=4)
    n0 = len(d)
    d = d[d[col_codigo].notna()].copy()
    if n0 - len(d):
        traza(etiqueta, 'excluir filas sin código territorial (pie de tabla del .ods)',
              'el archivo trae filas de nota al final que no son unidades territoriales',
              n0 - len(d))
    d['anio'] = pd.to_numeric(d['AÑO'], errors='coerce').astype('Int64')
    return d


# ══════════════════════════════════════════════════════════════════
# UPZ — grupos quinquenales, solo suelo urbano
# ══════════════════════════════════════════════════════════════════
print("== POBLACIÓN UPZ ==")
upz = leer('202503_upz_proyeccion_retroproyeccion_poblacion_2005_2035.ods',
           'Código UPZ', 'poblacion_upz')

areas_upz = set(upz['Área'].dropna().unique())
if areas_upz != {URBANO}:
    raise ValueError(f'poblacion_upz: se esperaba solo {URBANO!r}, hay {areas_upz}')
print(f"  (la fuente UPZ es exclusivamente '{URBANO}' -- coincide con el alcance urbano del proyecto)")

upz = pd.concat([upz, totales_por_sexo(upz, 'poblacion_upz')], axis=1)
upz['cod_upz'] = pd.to_numeric(upz['Código UPZ'], errors='coerce').astype('Int64')
traza('poblacion_upz', "convertir 'Código UPZ' (texto con ceros a la izquierda) a entero",
      'la llave de UPZ del pipeline es entera (extraída de CMIUUPLA); sin esto el join falla',
      int(upz['cod_upz'].notna().sum()))

upz_out = (upz[['cod_upz', 'anio', 'poblacion_total', 'poblacion_hombres',
                'poblacion_mujeres', 'poblacion_0_14']]
           .dropna(subset=['cod_upz', 'anio'])
           .sort_values(['anio', 'cod_upz']))
upz_out.to_parquet(os.path.join(SILVER, 'poblacion_upz.parquet'), index=False)
print(f"  silver/poblacion/poblacion_upz.parquet: {upz_out.shape} "
      f"({upz_out['cod_upz'].nunique()} UPZ x {upz_out['anio'].nunique()} años)")

# ══════════════════════════════════════════════════════════════════
# Localidad — edades año a año, urbano + rural en filas separadas
# ══════════════════════════════════════════════════════════════════
print("\n== POBLACIÓN LOCALIDAD ==")
loc = leer('202503_localidad_proyeccion_retroproyeccion_poblacion_2005_2035.ods',
           'Código Localidad', 'poblacion_localidad')
loc = pd.concat([loc, totales_por_sexo(loc, 'poblacion_localidad')], axis=1)
loc['cod_localidad'] = (pd.to_numeric(loc['Código Localidad'], errors='coerce')
                          .astype('Int64').astype(str).str.zfill(2))
traza('poblacion_localidad', "normalizar 'Código Localidad' a texto de 2 dígitos con cero a la izquierda",
      'dim_localidad usa cod_localidad como texto zero-padded ("01".."20")',
      int(loc['cod_localidad'].notna().sum()))

llave = ['cod_localidad', 'anio']
medidas = ['poblacion_total', 'poblacion_hombres', 'poblacion_mujeres', 'poblacion_0_14']

n_filas = len(loc)
total = loc.groupby(llave, as_index=False)[medidas].sum()
urbano = (loc[loc['Área'] == URBANO].groupby(llave, as_index=False)['poblacion_total']
          .sum().rename(columns={'poblacion_total': 'poblacion_cabecera'}))
loc_out = total.merge(urbano, on=llave, how='left')
loc_out['poblacion_cabecera'] = loc_out['poblacion_cabecera'].fillna(0)
loc_out['pct_rural'] = ((1 - loc_out['poblacion_cabecera'] / loc_out['poblacion_total'])
                        * 100).round(2)
traza('poblacion_localidad',
      f"consolidar '{URBANO}' + 'Centro Poblado y Rural Disperso' en una fila por localidad-año",
      '7 localidades traen componente urbano y rural en filas separadas; se conserva '
      'poblacion_cabecera aparte porque el denominador correcto depende del indicador '
      '(los delitos cubren toda la localidad; el aseo domiciliario es urbano)',
      n_filas - len(loc_out))

loc_out = loc_out.sort_values(['anio', 'cod_localidad'])
loc_out.to_parquet(os.path.join(SILVER, 'poblacion_localidad.parquet'), index=False)
print(f"  silver/poblacion/poblacion_localidad.parquet: {loc_out.shape} "
      f"({loc_out['cod_localidad'].nunique()} localidades x {loc_out['anio'].nunique()} años)")

rural = loc_out[(loc_out['anio'] == 2024) & (loc_out['pct_rural'] > 0)]
if len(rural):
    print(f"  localidades con componente rural en 2024: {len(rural)} "
          f"(máx: {rural['pct_rural'].max():.0f}% — Sumapaz, 100% rural, "
          f"consistente con su exclusión del alcance urbano)")

# ══════════════════════════════════════════════════════════════════
# Trazabilidad (se anexa a la tabla común del pipeline)
# ══════════════════════════════════════════════════════════════════
ruta_traza = os.path.join(BASE, 'scripts', '03_limpieza', 'trazabilidad.csv')
df_traza = pd.DataFrame(TRAZA)
if os.path.exists(ruta_traza):
    previo = pd.read_csv(ruta_traza)
    previo = previo[~previo['fuente'].isin(['poblacion_upz', 'poblacion_localidad'])]
    df_traza = pd.concat([previo, df_traza], ignore_index=True)
df_traza.to_csv(ruta_traza, index=False)
print(f"\n✅ Fase 3-4 (población) completa. Trazabilidad: {len(TRAZA)} transformaciones nuevas.")
