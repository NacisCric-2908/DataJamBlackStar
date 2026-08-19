"""
Script 02 — Build Silver: Capas Geoespaciales
DataJam Bogotá 2026

Fuentes: GeoJSON/JSON en Bronze/
Outputs: Silver/capas_geo/*.geoparquet

Capas procesadas:
- upz_bogota.geoparquet          (IRUPZ.geojson — 117 UPZ con datos residuos)
- localidades_bogota.geoparquet  (IRLoc.geojson)
- cestas_limpia.geoparquet       (cestas.geojson — re-proyectar EPSG:3857→4326)
- contenerizacion_limpia.geoparquet
- puntos_criticos.geoparquet
- rutas_barrido.geoparquet       (reparar geometrías inválidas)
- estaciones_bomberos.geoparquet
- indicadores_ambientales.geoparquet (DAILoc.geojson)
- cuadrantes_policia.geoparquet
"""

import os
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.validation import make_valid

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BRONZE = os.path.join(BASE, 'Bronze')
SILVER_GEO = os.path.join(BASE, 'Silver', 'capas_geo')
os.makedirs(SILVER_GEO, exist_ok=True)

print("=" * 60)
print("SCRIPT 02 — BUILD SILVER: CAPAS GEOESPACIALES")
print("=" * 60)

def reparar_geometrias(gdf, nombre):
    """Repara geometrías inválidas con make_valid."""
    invalidas = (~gdf.geometry.is_valid).sum()
    if invalidas > 0:
        print(f"  🔧 Reparando {invalidas} geometrías inválidas en {nombre}...")
        gdf.geometry = gdf.geometry.apply(
            lambda g: make_valid(g) if g is not None and not g.is_valid else g
        )
        invalidas_post = (~gdf.geometry.is_valid).sum()
        print(f"     Después de reparar: {invalidas_post} inválidas")
    return gdf

def guardar_geoparquet(gdf, nombre_out):
    """Re-proyecta a EPSG:4326 y guarda como GeoParquet."""
    if gdf.crs is None:
        print(f"  ⚠️  Sin CRS definido — asignando EPSG:4326")
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        print(f"  🔄 Re-proyectando {gdf.crs.to_epsg()} → 4326")
        gdf = gdf.to_crs(epsg=4326)

    out_path = os.path.join(SILVER_GEO, nombre_out)
    gdf.to_parquet(out_path, index=False)
    size_kb = os.path.getsize(out_path) / 1024
    print(f"  ✅ Guardado: {nombre_out} ({len(gdf):,} features | {size_kb:.0f} KB)")
    return gdf

# ═══════════════════════════════════════════════════════════════
# 1. UPZ Bogotá (IRUPZ.geojson) — capa maestra
# ═══════════════════════════════════════════════════════════════
print("\n📍 1. UPZ Bogotá (IRUPZ.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'IRUPZ.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf)} | CRS: {gdf.crs}")
gdf = reparar_geometrias(gdf, 'IRUPZ')

# Extraer código numérico de UPZ desde 'CMIUUPLA' (ej: 'UPZ75' → 75)
gdf['cod_upz'] = gdf['CMIUUPLA'].str.extract(r'(\d+)').astype(float).astype('Int64')
gdf['nombre_upz'] = gdf['CMNOMUPLA'].str.strip().str.title()

# Seleccionar columnas útiles: geometría + identificadores + indicadores clave de residuos
# CMRTOTAL = total residuos recogidos acumulado, CMNTOTAL = no recogidos, CMAOPTOTAL = AOP
cols_mantener = ['CMIUUPLA', 'cod_upz', 'nombre_upz', 'CMMES',
                 'CMRTOTAL', 'CMNTOTAL', 'CMAOPTOTAL', 'CMMMTOTAL',
                 'CMMTOTAL', 'CMDTOTAL', 'CMPIATOTAL', 'CMHTOTAL', 'CMHCTOTAL',
                 'CMR26CONT', 'CMN26CONT', 'CMAOP26CON', 'CMM26CONT',
                 'SHAPE_AREA', 'SHAPE_LEN', 'geometry']
cols_existentes = [c for c in cols_mantener if c in gdf.columns]
gdf_upz = gdf[cols_existentes].copy()

# Renombrar columnas a nombres descriptivos
rename_map = {
    'CMIUUPLA': 'upz_id',
    'CMMES': 'periodo',
    'CMRTOTAL': 'residuos_recogidos_total_t',
    'CMNTOTAL': 'residuos_no_recogidos_total_t',
    'CMAOPTOTAL': 'residuos_aop_total_t',
    'CMMMTOTAL': 'residuos_mm_total_t',
    'CMMTOTAL': 'residuos_mixtos_total_t',
    'CMDTOTAL': 'residuos_dom_total_t',
    'CMPIATOTAL': 'residuos_pia_total_t',
    'CMHTOTAL': 'residuos_h_total_t',
    'CMHCTOTAL': 'residuos_hc_total_t',
    'CMR26CONT': 'residuos_recogidos_2026',
    'CMN26CONT': 'residuos_no_recogidos_2026',
    'CMAOP26CON': 'residuos_aop_2026',
    'CMM26CONT': 'residuos_mixtos_2026',
    'SHAPE_AREA': 'area_m2',
    'SHAPE_LEN': 'perimetro_m',
}
gdf_upz = gdf_upz.rename(columns={k: v for k, v in rename_map.items() if k in gdf_upz.columns})
gdf_upz['area_km2'] = gdf_upz.get('area_m2', pd.Series(dtype=float)) / 1e6

guardar_geoparquet(gdf_upz, 'upz_bogota.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 2. Localidades Bogotá (IRLoc.geojson)
# ═══════════════════════════════════════════════════════════════
print("\n📍 2. Localidades Bogotá (IRLoc.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'IRLoc.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf)} | Columnas: {list(gdf.columns)[:8]}")
gdf = reparar_geometrias(gdf, 'IRLoc')
# Limpiar nulos de geometría
gdf = gdf[gdf.geometry.notna()].copy()
guardar_geoparquet(gdf, 'localidades_bogota.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 3. Indicadores Ambientales por Localidad (DAILoc.geojson)
# ═══════════════════════════════════════════════════════════════
print("\n📍 3. Indicadores Ambientales (DAILoc.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'DAILoc.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf)} | Columnas: {list(gdf.columns)[:8]}")
gdf = reparar_geometrias(gdf, 'DAILoc')
gdf = gdf[gdf.geometry.notna()].copy()
guardar_geoparquet(gdf, 'indicadores_ambientales_loc.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 4. Cestas de Basura (cestas.geojson) — CRS:3857 → 4326
# ═══════════════════════════════════════════════════════════════
print("\n📍 4. Cestas de Basura (cestas.geojson)")
print("  Leyendo archivo grande (~53 MB)...")
gdf = gpd.read_file(os.path.join(BRONZE, 'cestas.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf):,} | CRS: {gdf.crs}")

# Filtrar solo cestas instaladas/activas
if 'ESTADO' in gdf.columns:
    estados = gdf['ESTADO'].value_counts()
    print(f"  Estados: {estados.to_dict()}")
    gdf = gdf[gdf['ESTADO'].isin([2, 1, '2', '1', 'Instalada', 'INSTALADA'])].copy()
    print(f"  Filtradas (activas/instaladas): {len(gdf):,}")

# Seleccionar columnas útiles
cols_cestas = ['IDSEQ', 'IDLOCALID', 'NOMLOCALID', 'CAPACIDAD',
               'ESTADO', 'NOMESTADOE', 'TIPOCESTA', 'NOMTIPOCES',
               'TIPOEMPLAZ', 'NOMTIPOEMP', 'geometry']
cols_ok = [c for c in cols_cestas if c in gdf.columns]
gdf_cestas = gdf[cols_ok].copy()
guardar_geoparquet(gdf_cestas, 'cestas_limpia.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 5. Contenerización (contenerizacion.geojson)
# ═══════════════════════════════════════════════════════════════
print("\n📍 5. Contenerización (contenerizacion.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'contenerizacion.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf):,} | CRS: {gdf.crs}")
print(f"  Columnas: {list(gdf.columns)}")
gdf = reparar_geometrias(gdf, 'contenerizacion')
guardar_geoparquet(gdf, 'contenerizacion_limpia.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 6. Puntos Críticos de Arrojo Clandestino
# ═══════════════════════════════════════════════════════════════
print("\n📍 6. Puntos Críticos Arrojo (puntos_criticos_arrojo_clandestino_residuos.geojson)")
gdf = gpd.read_file(
    os.path.join(BRONZE, 'puntos_criticos_arrojo_clandestino_residuos.geojson'),
    engine='pyogrio'
)
print(f"  Features: {len(gdf)} | CRS: {gdf.crs}")
print(f"  Columnas: {list(gdf.columns)}")
# Parsear Nombre_Localidad a código numérico
if 'Nombre_Localidad' in gdf.columns:
    gdf['cod_localidad'] = pd.to_numeric(gdf['Nombre_Localidad'], errors='coerce').astype('Int64')
    print(f"  Localidades con puntos: {gdf['cod_localidad'].value_counts().to_dict()}")
if 'Observación' in gdf.columns:
    activos = (gdf['Observación'].str.upper() == 'ACTIVO').sum()
    print(f"  Puntos ACTIVOS: {activos} / {len(gdf)}")
guardar_geoparquet(gdf, 'puntos_criticos.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 7. Macrorutas de Barrido (macrorutas_de_barrido.geojson)
#    ⚠️ 89.9% geometrías inválidas — reparar obligatorio
# ═══════════════════════════════════════════════════════════════
print("\n📍 7. Rutas de Barrido (macrorutas_de_barrido.geojson)")
print("  Leyendo archivo grande (~35 MB)...")
gdf = gpd.read_file(os.path.join(BRONZE, 'macrorutas_de_barrido.geojson'),
                    engine='pyogrio')
print(f"  Features: {len(gdf):,} | CRS: {gdf.crs}")
print(f"  Columnas: {list(gdf.columns)}")

# Reparar geometrías inválidas
gdf = reparar_geometrias(gdf, 'rutas_barrido')
# Eliminar geometrías nulas post-reparación
gdf = gdf[gdf.geometry.notna() & gdf.geometry.is_valid].copy()
print(f"  Features válidas después de reparación: {len(gdf):,}")
guardar_geoparquet(gdf, 'rutas_barrido.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 8. Estaciones de Bomberos (ebom.geojson)
# ═══════════════════════════════════════════════════════════════
print("\n📍 8. Estaciones Bomberos (ebom.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'ebom.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf)} | CRS: {gdf.crs}")
print(f"  Columnas: {list(gdf.columns)}")
guardar_geoparquet(gdf, 'estaciones_bomberos.geoparquet')

# ═══════════════════════════════════════════════════════════════
# 9. Cuadrantes de Policía (cuadrantepolicia.geojson)
# ═══════════════════════════════════════════════════════════════
print("\n📍 9. Cuadrantes Policía (cuadrantepolicia.geojson)")
gdf = gpd.read_file(os.path.join(BRONZE, 'cuadrantepolicia.geojson'), engine='pyogrio')
print(f"  Features: {len(gdf):,} | CRS: {gdf.crs}")
print(f"  Columnas: {list(gdf.columns)[:6]}")
gdf = reparar_geometrias(gdf, 'cuadrantepolicia')
guardar_geoparquet(gdf, 'cuadrantes_policia.geoparquet')

# ═══════════════════════════════════════════════════════════════
# Resumen final
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*60}")
print("RESUMEN — Capas Silver generadas:")
for f in sorted(os.listdir(SILVER_GEO)):
    size_mb = os.path.getsize(os.path.join(SILVER_GEO, f)) / 1024**2
    print(f"  ✅ {f}: {size_mb:.1f} MB")
print("\n✅ Script 02 completado.")
