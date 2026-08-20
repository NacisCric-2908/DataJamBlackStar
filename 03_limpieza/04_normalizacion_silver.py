"""
Fases 3-4 — Limpieza y normalización → Silver (separado por dominio)
DataJam Bogotá 2026

Aplica SOLO las correcciones documentadas en 02_auditoria/reporte_auditoria.md.
Cada transformación queda registrada en la tabla de trazabilidad
(03_limpieza/trazabilidad.csv). No se introduce ninguna conclusión analítica
aquí (eso es Gold).
"""
import os
import re
import unicodedata
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.validation import make_valid

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRONZE = os.path.join(BASE, 'data', 'bronze')
SILVER = os.path.join(BASE, 'data', 'silver')

trazabilidad = []


def traza(fuente, transformacion, motivo, registros_afectados):
    trazabilidad.append({
        'fuente': fuente, 'transformacion': transformacion,
        'motivo': motivo, 'registros_afectados': registros_afectados
    })
    print(f"  [traza] {fuente} | {transformacion} | {motivo} | n={registros_afectados}")


def normalizar_texto(texto):
    if pd.isna(texto):
        return ''
    s = unicodedata.normalize('NFKD', str(texto))
    s = s.encode('ascii', errors='ignore').decode('ascii')
    s = re.sub(r'[^A-Za-z0-9\s]', '', s)
    return s.strip().upper()


def reparar_geometrias(gdf, nombre):
    invalidas = (~gdf.geometry.is_valid).sum()
    if invalidas > 0:
        gdf.geometry = gdf.geometry.apply(
            lambda g: make_valid(g) if g is not None and not g.is_valid else g
        )
        traza(nombre, 'make_valid() sobre geometrías inválidas',
              'geometrías topológicamente inválidas detectadas en auditoría', int(invalidas))
    return gdf


def excluir_sin_localizacion(gdf, nombre, col_codigo, valor_sin_loc):
    mask = gdf[col_codigo].astype(str) == str(valor_sin_loc)
    n = mask.sum()
    if n > 0:
        traza(nombre, f'excluir fila código {valor_sin_loc} ("Sin Localización")',
              'geometría nula/inválida y fuera de Bogotá; es un bucket administrativo '
              'de "sin ubicar", no una localidad/UPZ real (verificado en auditoría)', int(n))
        gdf = gdf[~mask].copy()
    return gdf


def a_4326(gdf, nombre):
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        epsg_orig = gdf.crs.to_epsg()
        gdf = gdf.to_crs(epsg=4326)
        traza(nombre, f'reproyección EPSG:{epsg_orig} -> EPSG:4326', 'unificar CRS para joins espaciales', len(gdf))
    return gdf


# ══════════════════════════════════════════════════════════════════
# TERRITORIO
# ══════════════════════════════════════════════════════════════════
print("== TERRITORIO ==")
gdf_upz = gpd.read_file(os.path.join(BRONZE, 'IRUPZ.geojson'), engine='pyogrio')
gdf_upz = excluir_sin_localizacion(gdf_upz, 'IRUPZ', 'CMIUUPLA', 'UPZ999')
n0_upz = len(gdf_upz)
gdf_upz = gdf_upz[gdf_upz['CMIUUPLA'].str.startswith('UPZ')].copy()
traza('IRUPZ', "excluir CMIUUPLA con prefijo 'UPR' (rural)",
      "UPR (Unidad de Planeamiento Rural) reutiliza la misma numeración que UPZ "
      "(ej. UPZ3='Guaymaral' vs UPR3='Rio Tunjuelo') -- si se extrae solo el número "
      "quedan códigos duplicados y se fusionan zonas distintas; además zona rural está "
      "fuera del alcance declarado del proyecto (estratificación 1-6 solo aplica a suelo urbano)",
      n0_upz - len(gdf_upz))
gdf_upz = reparar_geometrias(gdf_upz, 'IRUPZ')
gdf_upz = a_4326(gdf_upz, 'IRUPZ')
gdf_upz['cod_upz'] = gdf_upz['CMIUUPLA'].str.extract(r'(\d+)').astype(float).astype('Int64')
gdf_upz['nombre_upz'] = gdf_upz['CMNOMUPLA'].str.strip().str.title()
gdf_upz['area_km2'] = (gdf_upz.geometry.to_crs(epsg=3116).area / 1e6).round(4)
gdf_upz[['cod_upz', 'nombre_upz', 'area_km2', 'geometry']].to_parquet(
    os.path.join(SILVER, 'territorio', 'upz.parquet'), index=False)

gdf_loc = gpd.read_file(os.path.join(BRONZE, 'IRLoc.geojson'), engine='pyogrio')
gdf_loc = excluir_sin_localizacion(gdf_loc, 'IRLoc', 'CMIULOCAL', '99')
gdf_loc = reparar_geometrias(gdf_loc, 'IRLoc')
gdf_loc = a_4326(gdf_loc, 'IRLoc')
gdf_loc['cod_localidad'] = gdf_loc['CMIULOCAL'].astype(str).str.zfill(2)
gdf_loc['nombre_localidad'] = gdf_loc['CMNOMLOCAL'].apply(normalizar_texto)
gdf_loc['area_km2'] = (gdf_loc.geometry.to_crs(epsg=3116).area / 1e6).round(4)
gdf_loc[['cod_localidad', 'nombre_localidad', 'area_km2', 'geometry']].to_parquet(
    os.path.join(SILVER, 'territorio', 'localidades.parquet'), index=False)
print(f"  UPZ: {len(gdf_upz)} | Localidades: {len(gdf_loc)}")

# ══════════════════════════════════════════════════════════════════
# ASEO — cestas, contenedores, puntos críticos, macrorutas
# ══════════════════════════════════════════════════════════════════
print("== ASEO ==")
gdf_cestas = gpd.read_file(os.path.join(BRONZE, 'cestas.geojson'), engine='pyogrio')
n0 = len(gdf_cestas)
gdf_cestas = gdf_cestas[gdf_cestas['ESTADO'].isin([2, '2'])].copy()
traza('cestas', 'filtrar ESTADO==2 (instalada/activa)', 'excluir cestas retiradas/inactivas (ESTADO 99)', n0 - len(gdf_cestas))
gdf_cestas = a_4326(gdf_cestas, 'cestas')
gdf_cestas[['IDSEQ', 'geometry']].to_parquet(os.path.join(SILVER, 'aseo', 'cestas.parquet'), index=False)

gdf_cont = gpd.read_file(os.path.join(BRONZE, 'contenerizacion.geojson'), engine='pyogrio')
n0 = len(gdf_cont)
dup = gdf_cont.drop(columns='geometry').duplicated()
gdf_cont = gdf_cont[~dup].copy()
traza('contenerizacion', 'eliminar duplicados exactos por atributos', 'duplicados confirmados en auditoría', int(dup.sum()))
gdf_cont = a_4326(gdf_cont, 'contenerizacion')
gdf_cont[['CODINTERNO', 'geometry']].to_parquet(os.path.join(SILVER, 'aseo', 'contenerizacion.parquet'), index=False)

gdf_pc = gpd.read_file(os.path.join(BRONZE, 'puntos_criticos_arrojo_clandestino_residuos.geojson'), engine='pyogrio')
gdf_pc = a_4326(gdf_pc, 'puntos_criticos')
gdf_pc['cod_localidad'] = pd.to_numeric(gdf_pc['Nombre_Localidad'], errors='coerce').astype('Int64').astype(str).str.zfill(2)
gdf_pc[['OBJECTID', 'Frecuencia', 'Observación', 'cod_localidad', 'geometry']].to_parquet(
    os.path.join(SILVER, 'aseo', 'puntos_criticos.parquet'), index=False)

gdf_mr = gpd.read_file(os.path.join(BRONZE, 'macrorutas_de_barrido.geojson'), engine='pyogrio')
gdf_mr = reparar_geometrias(gdf_mr, 'macrorutas_de_barrido')
gdf_mr = gdf_mr[gdf_mr.geometry.notna() & gdf_mr.geometry.is_valid].copy()
gdf_mr = a_4326(gdf_mr, 'macrorutas_de_barrido')
gdf_mr[['OBJECTID', 'geometry']].to_parquet(os.path.join(SILVER, 'aseo', 'macrorutas.parquet'), index=False)
print(f"  cestas: {len(gdf_cestas)} | contenedores: {len(gdf_cont)} | puntos criticos: {len(gdf_pc)} | macrorutas: {len(gdf_mr)}")

# ══════════════════════════════════════════════════════════════════
# POLICÍA
# ══════════════════════════════════════════════════════════════════
print("== POLICIA ==")
gdf_cuad = gpd.read_file(os.path.join(BRONZE, 'cuadrantepolicia.geojson'), engine='pyogrio')
gdf_cuad = a_4326(gdf_cuad, 'cuadrantepolicia')
gdf_cuad[['PCUNCUADRA', 'PCUNOMEST', 'PCUNOMCAI', 'geometry']].to_parquet(
    os.path.join(SILVER, 'policia', 'cuadrantes.parquet'), index=False)
print(f"  cuadrantes: {len(gdf_cuad)}")

# ══════════════════════════════════════════════════════════════════
# BOMBEROS — estaciones
# ══════════════════════════════════════════════════════════════════
print("== BOMBEROS ==")
gdf_ebom = gpd.read_file(os.path.join(BRONZE, 'ebom.geojson'), engine='pyogrio')
gdf_ebom = a_4326(gdf_ebom, 'ebom')
gdf_ebom[['OBJECTID', 'EBONOMBRE', 'geometry']].to_parquet(
    os.path.join(SILVER, 'bomberos', 'estaciones.parquet'), index=False)
print(f"  estaciones bomberos: {len(gdf_ebom)}")

# ══════════════════════════════════════════════════════════════════
# SEGURIDAD — DAILoc (delitos), solo nivel localidad (fuente no trae UPZ)
# ══════════════════════════════════════════════════════════════════
print("== SEGURIDAD ==")
gdf_dai = gpd.read_file(os.path.join(BRONZE, 'DAILoc.geojson'), engine='pyogrio')
gdf_dai = excluir_sin_localizacion(gdf_dai, 'DAILoc', 'CMIULOCAL', '99')
gdf_dai = reparar_geometrias(gdf_dai, 'DAILoc')
gdf_dai = a_4326(gdf_dai, 'DAILoc')
gdf_dai['cod_localidad'] = gdf_dai['CMIULOCAL'].astype(str).str.zfill(2)
gdf_dai['localidad_norm'] = gdf_dai['CMNOMLOCAL'].apply(normalizar_texto)

h_cols = [c for c in gdf_dai.columns if c.startswith('CMH') and 'CONT' in c and not c.startswith(('CMHC', 'CMHP', 'CMHR', 'CMHA', 'CMHB', 'CMHM', 'CMHCE'))]
hp_cols = [c for c in gdf_dai.columns if c.startswith('CMHP') and 'CONT' in c]
hr_cols = [c for c in gdf_dai.columns if c.startswith('CMHR') and 'CONT' in c]
hc_cols = [c for c in gdf_dai.columns if c.startswith('CMHC') and 'CONT' in c and not c.startswith('CMHCE')]
hce_cols = [c for c in gdf_dai.columns if c.startswith('CMHCE') and 'CON' in c]
lp_cols = [c for c in gdf_dai.columns if c.startswith('CMLP') and 'CONT' in c]
ds_cols = [c for c in gdf_dai.columns if c.startswith('CMDS') and 'CONT' in c]
vi_cols = [c for c in gdf_dai.columns if c.startswith('CMVI') and 'CONT' in c]
all_crime_cols = [c for c in gdf_dai.columns if 'CONT' in c or 'CON' in c]

gdf_dai['homicidios_cont'] = gdf_dai[h_cols].sum(axis=1)
gdf_dai['hurto_personas_cont'] = gdf_dai[hp_cols].sum(axis=1)
gdf_dai['hurto_residencias_cont'] = gdf_dai[hr_cols].sum(axis=1)
gdf_dai['hurto_comercio_cont'] = gdf_dai[hc_cols].sum(axis=1)
gdf_dai['lesiones_personales_cont'] = gdf_dai[lp_cols].sum(axis=1)
gdf_dai['delitos_sexuales_cont'] = gdf_dai[ds_cols].sum(axis=1)
gdf_dai['violencia_intrafamiliar_cont'] = gdf_dai[vi_cols].sum(axis=1)
gdf_dai['delitos_alto_impacto_cont'] = gdf_dai[all_crime_cols].sum(axis=1)
# Totales oficiales del propio dataset (campo TOTAL, no derivado por nosotros)
gdf_dai['homicidios_total_oficial'] = gdf_dai.get('CMHTOTAL', np.nan)
gdf_dai['violencia_intrafamiliar_total_oficial'] = gdf_dai.get('CMVITOTAL', np.nan)

traza('DAILoc', 'construir homicidios_cont/_total_oficial en paralelo',
      'CMH*CONT (suma por año) y CMHTOTAL (campo oficial) NO coinciden '
      '(4.740 vs 11.445 hallado en sesión previa) — se conservan ambos, sin elegir uno, '
      'hasta aclarar semántica con la entidad fuente', len(gdf_dai))

cols_dai = ['cod_localidad', 'localidad_norm', 'homicidios_cont', 'homicidios_total_oficial',
            'hurto_personas_cont', 'hurto_residencias_cont', 'hurto_comercio_cont',
            'lesiones_personales_cont', 'delitos_sexuales_cont',
            'violencia_intrafamiliar_cont', 'violencia_intrafamiliar_total_oficial',
            'delitos_alto_impacto_cont', 'geometry']
gdf_dai[cols_dai].to_parquet(os.path.join(SILVER, 'seguridad', 'delitos_localidad.parquet'), index=False)
print(f"  delitos (localidad): {len(gdf_dai)}")

# guardar catálogo de trazabilidad
pd.DataFrame(trazabilidad).to_csv(os.path.join(os.path.dirname(__file__), 'trazabilidad.csv'), index=False)
print(f"\n✅ Silver (territorio/aseo/policia/bomberos/seguridad) construido. Trazabilidad: {len(trazabilidad)} transformaciones registradas.")
