"""
Fase 2 (addendum) — Auditoría de la 14ª fuente: manzanaestratificacion.json
DataJam Bogotá 2026

Esta fuente se incorporó DESPUÉS de la auditoría original (Fase 2, 13 fuentes).
Se audita aquí retroactivamente con el mismo criterio de 01_auditoria_datos.py,
antes de considerarla apta para producción (regla de agent.md: auditar antes
de transformar). Ya se había limpiado en 03_limpieza/08_... -- esto documenta
los mismos hallazgos que motivaron esa limpieza, para dejar el orden correcto
registrado en 02_auditoria/hallazgos.csv.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
OUT = os.path.dirname(__file__)

hallazgos = []


def log(fuente, chequeo, resultado, severidad='info'):
    hallazgos.append({'fuente': fuente, 'chequeo': chequeo, 'resultado': str(resultado), 'severidad': severidad})
    print(f"[{severidad.upper():5}] {fuente} — {chequeo}: {resultado}")


capa = 'manzanaestratificacion.json'
gdf = gpd.read_file(os.path.join(BRONZE, capa), engine='pyogrio')
n = len(gdf)

log(capa, 'n_registros', n)
log(capa, 'tipo_geometria', gdf.geom_type.unique().tolist())
log(capa, 'crs', gdf.crs.name if gdf.crs else 'N/A')
log(capa, 'crs_es_local_no_estandar',
    'Sí -- PCS_CarMAGBOG (proyección cartesiana local de Bogotá, no un EPSG con nombre estándar; '
    'pyproj sí puede reproyectarla desde el WKT completo)', 'warning')

inv = (~gdf.geometry.is_valid).sum()
log(capa, 'geometrias_invalidas', f"{inv}/{n} ({inv/n*100:.2f}%)", 'warning' if inv > 0 else 'ok')

nulls_geom = gdf.geometry.isna().sum()
log(capa, 'geometrias_nulas', nulls_geom, 'warning' if nulls_geom > 0 else 'ok')

dup = gdf.drop(columns='geometry').duplicated().sum()
log(capa, 'filas_duplicadas_por_atributos', dup, 'warning' if dup > 0 else 'ok')

gdf['ESTRATO_num'] = pd.to_numeric(gdf['ESTRATO'], errors='coerce')
fuera_rango = (~gdf['ESTRATO_num'].between(0, 6)).sum()
log(capa, 'estrato_fuera_de_rango_0_6', fuera_rango, 'warning' if fuera_rango > 0 else 'ok')
n_cero_nulo = (gdf['ESTRATO_num'] == 0).sum() + gdf['ESTRATO_num'].isna().sum()
log(capa, 'estrato_0_o_nulo_sin_estratificar',
    f"{n_cero_nulo}/{n} ({n_cero_nulo/n*100:.1f}%) -- manzanas comerciales/industriales/institucionales, correctamente excluidas en Silver",
    'info')

dup_manz = gdf['CODIGO_MANZANA'].duplicated().sum()
log(capa, 'CODIGO_MANZANA_duplicados', dup_manz, 'warning' if dup_manz > 0 else 'ok')

fecha_min, fecha_max = gdf['FECHA_CAPTURA'].min(), gdf['FECHA_CAPTURA'].max()
log(capa, 'cobertura_temporal_captura', f"{fecha_min} a {fecha_max}", 'info')

df_h = pd.DataFrame(hallazgos)
hallazgos_path = os.path.join(OUT, 'hallazgos.csv')
existentes = pd.read_csv(hallazgos_path)
combinado = pd.concat([existentes, df_h], ignore_index=True)
combinado.to_csv(hallazgos_path, index=False)

print(f"\n✅ {len(df_h)} hallazgos de manzanaestratificacion.json añadidos a 02_auditoria/hallazgos.csv "
      f"({len(combinado)} hallazgos totales en el proyecto).")
