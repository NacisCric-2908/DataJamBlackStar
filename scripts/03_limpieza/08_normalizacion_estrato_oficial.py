"""
Fase 3-4 (actualización) — Estrato socioeconómico OFICIAL por manzana → silver/socioeconomico/
DataJam Bogotá 2026

Reemplaza el proxy (estrato autorreportado en incidentes UAECOB) por la fuente
oficial real: "Estratificación para Bogotá" (Secretaría Distrital de Planeación,
https://datosabiertos.bogota.gov.co/dataset/estratificacion-para-bogota),
manzanaestratificacion.json — polígonos de manzana con ESTRATO ya asignado.

A diferencia de Esoc.csv (sin llave espacial verificable a UPZ/localidad), esta
fuente SÍ trae geometría real por manzana -> spatial join directo, sin necesidad
de cruces de códigos frágiles.
"""
import os
import re
import unicodedata
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.validation import make_valid

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


print("Leyendo manzanaestratificacion.json (83 MB, puede tardar)...")
gdf_manz = gpd.read_file(os.path.join(BRONZE, 'manzanaestratificacion.json'), engine='pyogrio')
n0 = len(gdf_manz)
print(f"  {n0:,} manzanas leídas | CRS original: {gdf_manz.crs.name if gdf_manz.crs else 'N/A'}")

# Reparar geometrías inválidas (mismo criterio que el resto del pipeline)
invalidas = (~gdf_manz.geometry.is_valid).sum()
if invalidas > 0:
    gdf_manz.geometry = gdf_manz.geometry.apply(lambda g: make_valid(g) if g is not None and not g.is_valid else g)
    traza('manzanaestratificacion', 'make_valid() sobre geometrías inválidas',
          'geometrías topológicamente inválidas', int(invalidas))

# Estrato válido 1-6 (excluir 0 = sin estratificar, y nulos)
gdf_manz['ESTRATO'] = pd.to_numeric(gdf_manz['ESTRATO'], errors='coerce')
n_antes = len(gdf_manz)
gdf_manz = gdf_manz[gdf_manz['ESTRATO'].between(1, 6)].copy()
traza('manzanaestratificacion', 'filtrar ESTRATO entre 1 y 6',
      'excluir manzanas sin estratificar (comercial/industrial/institucional) o con estrato inválido',
      n_antes - len(gdf_manz))

# Reproyectar a EPSG:4326 para el join (CRS original es una proyección cartesiana local de Bogotá)
gdf_manz = gdf_manz.to_crs(epsg=4326)
traza('manzanaestratificacion', 'reproyección a EPSG:4326', 'unificar CRS para spatial join', len(gdf_manz))

# Punto representativo de cada manzana (más robusto que centroide para polígonos irregulares)
gdf_manz['geom_punto'] = gdf_manz.geometry.representative_point()
gdf_puntos = gdf_manz.set_geometry('geom_punto')[['CODIGO_MANZANA', 'ESTRATO', 'geom_punto']].rename(
    columns={'geom_punto': 'geometry'}).set_geometry('geometry')
gdf_puntos.crs = 'EPSG:4326'

# ── Join espacial a UPZ ──────────────────────────────────────────
gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet'))
sj_upz = gpd.sjoin(gdf_puntos, gdf_upz[['cod_upz', 'geometry']], how='inner', predicate='within')

estrato_upz = sj_upz.groupby('cod_upz')['ESTRATO'].agg(
    estrato_modal_oficial=lambda x: x.mode().iloc[0],
    estrato_promedio_oficial='mean',
    n_manzanas='count',
    pct_estrato_1_2_oficial=lambda x: (x.isin([1, 2])).mean() * 100,
    pct_estrato_5_6_oficial=lambda x: (x.isin([5, 6])).mean() * 100,
).reset_index()
match_upz = sj_upz['cod_upz'].notna().sum()
print(f"\nManzanas asignadas a UPZ: {match_upz:,}/{len(gdf_puntos):,} ({match_upz/len(gdf_puntos)*100:.1f}%)")

# ── Join espacial a Localidad ────────────────────────────────────
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet'))
sj_loc = gpd.sjoin(gdf_puntos, gdf_loc[['cod_localidad', 'geometry']], how='inner', predicate='within')

estrato_loc = sj_loc.groupby('cod_localidad')['ESTRATO'].agg(
    estrato_modal_oficial=lambda x: x.mode().iloc[0],
    estrato_promedio_oficial='mean',
    n_manzanas='count',
    pct_estrato_1_2_oficial=lambda x: (x.isin([1, 2])).mean() * 100,
    pct_estrato_5_6_oficial=lambda x: (x.isin([5, 6])).mean() * 100,
).reset_index()
match_loc = sj_loc['cod_localidad'].notna().sum()
print(f"Manzanas asignadas a Localidad: {match_loc:,}/{len(gdf_puntos):,} ({match_loc/len(gdf_puntos)*100:.1f}%)")

traza('manzanaestratificacion', 'spatial join (representative_point within) a UPZ y Localidad',
      f'reemplaza el proxy de estrato autorreportado en UAECOB por la fuente oficial real; '
      f'match {match_upz/len(gdf_puntos)*100:.1f}% a UPZ, {match_loc/len(gdf_puntos)*100:.1f}% a Localidad',
      len(gdf_puntos))

estrato_upz.to_parquet(os.path.join(SILVER, 'socioeconomico', 'estrato_oficial_upz.parquet'), index=False)
estrato_loc.to_parquet(os.path.join(SILVER, 'socioeconomico', 'estrato_oficial_localidad.parquet'), index=False)

print(f"\nEstrato oficial por UPZ (muestra):")
print(estrato_upz.head())
print(f"\nEstrato oficial por Localidad:")
print(estrato_loc.sort_values('cod_localidad').to_string(index=False))
print(f"\n✅ silver/socioeconomico/estrato_oficial_{{upz,localidad}}.parquet guardados.")
