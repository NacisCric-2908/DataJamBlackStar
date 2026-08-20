"""
Fase 5 — Integración espacial
DataJam Bogotá 2026

Spatial joins reales (point-in-polygon / intersects / nearest) de infraestructura
de aseo, policía y bomberos hacia UPZ y localidad. No se usa matching por texto
en ningún punto de este script.
"""
import os
import pandas as pd
import numpy as np
import geopandas as gpd

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
OUT = os.path.dirname(__file__)

gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet'))
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet'))


def contar_por_zona(gdf_puntos, gdf_zona, id_col, nombre_out, predicate='within'):
    sj = gpd.sjoin(gdf_puntos, gdf_zona[[id_col, 'geometry']], how='inner', predicate=predicate)
    n_antes = len(gdf_puntos)
    conteo = sj.groupby(id_col).size().reset_index(name=nombre_out)
    n_asignados = sj[id_col].notna().sum()
    print(f"  {nombre_out}: {n_asignados}/{n_antes} asignados ({n_asignados/n_antes*100:.1f}%)")
    return conteo


resultados_upz = {'cod_upz': gdf_upz['cod_upz']}
resultados_loc = {'cod_localidad': gdf_loc['cod_localidad']}


def merge_conteo(base_dict, base_df, id_col, conteo, nombre_out):
    m = base_df[[id_col]].merge(conteo, on=id_col, how='left')
    base_dict[nombre_out] = m[nombre_out].fillna(0).astype(int).values


print("== Cestas ==")
gdf_cestas = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'cestas.parquet'))
merge_conteo(resultados_upz, gdf_upz, 'cod_upz', contar_por_zona(gdf_cestas, gdf_upz, 'cod_upz', 'n_cestas'), 'n_cestas')
merge_conteo(resultados_loc, gdf_loc, 'cod_localidad', contar_por_zona(gdf_cestas, gdf_loc, 'cod_localidad', 'n_cestas'), 'n_cestas')

print("== Contenedores ==")
gdf_cont = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'contenerizacion.parquet'))
merge_conteo(resultados_upz, gdf_upz, 'cod_upz', contar_por_zona(gdf_cont, gdf_upz, 'cod_upz', 'n_contenedores'), 'n_contenedores')
merge_conteo(resultados_loc, gdf_loc, 'cod_localidad', contar_por_zona(gdf_cont, gdf_loc, 'cod_localidad', 'n_contenedores'), 'n_contenedores')

print("== Puntos críticos de arrojo ==")
gdf_pc = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'puntos_criticos.parquet'))
gdf_pc = gdf_pc.drop(columns=['cod_localidad'])  # se recalcula por spatial join real, no por atributo
merge_conteo(resultados_upz, gdf_upz, 'cod_upz', contar_por_zona(gdf_pc, gdf_upz, 'cod_upz', 'n_puntos_criticos'), 'n_puntos_criticos')
merge_conteo(resultados_loc, gdf_loc, 'cod_localidad', contar_por_zona(gdf_pc, gdf_loc, 'cod_localidad', 'n_puntos_criticos'), 'n_puntos_criticos')

print("== Cobertura de macrorutas (% área UPZ/localidad cubierta) ==")
gdf_mr = gpd.read_parquet(os.path.join(SILVER, 'aseo', 'macrorutas.parquet'))
mr_union = gdf_mr.geometry.union_all()
gdf_upz_m = gdf_upz.to_crs(epsg=3116)
gdf_loc_m = gdf_loc.to_crs(epsg=3116)
mr_union_m = gpd.GeoSeries([mr_union], crs=4326).to_crs(epsg=3116).iloc[0]
resultados_upz['cobertura_macrorutas_pct'] = (
    gdf_upz_m.geometry.intersection(mr_union_m).area / gdf_upz_m.geometry.area * 100
).round(1).values
resultados_loc['cobertura_macrorutas_pct'] = (
    gdf_loc_m.geometry.intersection(mr_union_m).area / gdf_loc_m.geometry.area * 100
).round(1).values

print("== Cuadrantes de policía (intersects, no within: un cuadrante puede cruzar límites) ==")
gdf_cuad = gpd.read_parquet(os.path.join(SILVER, 'policia', 'cuadrantes.parquet'))
merge_conteo(resultados_upz, gdf_upz, 'cod_upz', contar_por_zona(gdf_cuad, gdf_upz, 'cod_upz', 'n_cuadrantes', predicate='intersects'), 'n_cuadrantes')
merge_conteo(resultados_loc, gdf_loc, 'cod_localidad', contar_por_zona(gdf_cuad, gdf_loc, 'cod_localidad', 'n_cuadrantes', predicate='intersects'), 'n_cuadrantes')

print("== Estaciones de bomberos: distancia al centroide (metros, EPSG:3116) ==")
gdf_ebom = gpd.read_parquet(os.path.join(SILVER, 'bomberos', 'estaciones.parquet')).to_crs(epsg=3116)
cent_upz = gdf_upz.to_crs(epsg=3116).geometry.centroid
cent_loc = gdf_loc.to_crs(epsg=3116).geometry.centroid
resultados_upz['dist_estacion_bomberos_m'] = [
    gdf_ebom.geometry.distance(pt).min() for pt in cent_upz
]
resultados_loc['dist_estacion_bomberos_m'] = [
    gdf_ebom.geometry.distance(pt).min() for pt in cent_loc
]
resultados_upz['n_estaciones_bomberos_5km'] = [
    (gdf_ebom.geometry.distance(pt) <= 5000).sum() for pt in cent_upz
]
resultados_loc['n_estaciones_bomberos_5km'] = [
    (gdf_ebom.geometry.distance(pt) <= 5000).sum() for pt in cent_loc
]

df_upz_out = pd.DataFrame(resultados_upz)
df_loc_out = pd.DataFrame(resultados_loc)
df_upz_out.to_parquet(os.path.join(OUT, 'aseo_policia_bomberos_upz.parquet'), index=False)
df_loc_out.to_parquet(os.path.join(OUT, 'aseo_policia_bomberos_localidad.parquet'), index=False)

print("\n✅ Integración espacial completa (UPZ y localidad).")
print(df_upz_out.describe().round(1))
