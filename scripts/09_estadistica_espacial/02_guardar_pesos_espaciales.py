"""
Fase 9 (complemento) — Guardar las matrices de pesos espaciales usadas
DataJam Bogotá 2026

agent.md pide explícitamente un directorio gold/estadistica_espacial/spatial_weights/
con la metodología de pesos utilizada, para que el análisis sea reproducible sin
tener que re-derivar la matriz W.
"""
import os
import warnings
warnings.filterwarnings('ignore')
import pandas as pd
import geopandas as gpd
from libpysal.weights import Queen, KNN

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SILVER = os.path.join(BASE, 'data', 'silver')
os.makedirs(SILVER, exist_ok=True)
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
OUT = os.path.join(GOLD, 'estadistica_espacial', 'spatial_weights')


def guardar_pesos(gdf, nombre_unidad, id_col, nombre_metodo, w):
    filas = []
    for i, vecinos in w.neighbors.items():
        for j in vecinos:
            filas.append({'unidad': nombre_unidad, 'metodologia': nombre_metodo,
                           'origen_idx': i, 'destino_idx': j,
                           'origen_id': str(gdf.iloc[i][id_col]), 'destino_id': str(gdf.iloc[j][id_col])})
    df = pd.DataFrame(filas)
    n_islas = len(w.islands)
    print(f"  {nombre_unidad} / {nombre_metodo}: {len(df)} pares vecino-vecino, {n_islas} islas ({w.islands})")
    return df


gdf_upz = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'upz.parquet')).reset_index(drop=True)
gdf_loc = gpd.read_parquet(os.path.join(SILVER, 'territorio', 'localidades.parquet')).reset_index(drop=True)

w_upz_queen = Queen.from_dataframe(gdf_upz, use_index=False)
w_upz_knn = KNN.from_dataframe(gdf_upz, k=5)
w_loc_queen = Queen.from_dataframe(gdf_loc, use_index=False)

resultados = []
resultados.append(guardar_pesos(gdf_upz, 'UPZ', 'cod_upz', 'Queen (contigüidad)', w_upz_queen))
resultados.append(guardar_pesos(gdf_upz, 'UPZ', 'cod_upz', 'KNN k=5', w_upz_knn))
resultados.append(guardar_pesos(gdf_loc, 'Localidad', 'cod_localidad', 'Queen (contigüidad)', w_loc_queen))

df_todos = pd.concat(resultados, ignore_index=True)
df_todos.to_parquet(os.path.join(OUT, 'pesos_espaciales.parquet'), index=False)

metodologia = pd.DataFrame([
    {'unidad': 'UPZ', 'metodologia_principal': 'Queen (contigüidad)', 'n_unidades': len(gdf_upz),
     'n_islas': len(w_upz_queen.islands), 'islas_cod': str([gdf_upz.iloc[i]['cod_upz'] for i in w_upz_queen.islands]),
     'transformacion_pesos': 'row-standardized (r)', 'usado_en': '09_estadistica_espacial (Moran/LISA/Gi*), 10_modelos (offset espacial no aplica)'},
    {'unidad': 'Localidad', 'metodologia_principal': 'Queen (contigüidad)', 'n_unidades': len(gdf_loc),
     'n_islas': len(w_loc_queen.islands), 'islas_cod': str([gdf_loc.iloc[i]['cod_localidad'] for i in w_loc_queen.islands]),
     'transformacion_pesos': 'row-standardized (r)', 'usado_en': '09_estadistica_espacial'},
    {'unidad': 'UPZ', 'metodologia_principal': 'KNN k=5 (sensibilidad, Fase 12)', 'n_unidades': len(gdf_upz),
     'n_islas': 0, 'islas_cod': '[]', 'transformacion_pesos': 'row-standardized (r)', 'usado_en': '12_validacion (robustez)'},
])
metodologia.to_csv(os.path.join(OUT, 'metodologia_pesos.csv'), index=False)
metodologia.to_parquet(os.path.join(OUT, 'metodologia_pesos.parquet'), index=False)

print(f"\n✅ Pesos espaciales guardados en {OUT}")
print(metodologia.to_string(index=False))
