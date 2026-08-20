"""
Fases 3-4 — Estrato socioeconómico (Esoc.csv, 2.99M unidades) → silver/socioeconomico/
Hallazgo de auditoría: ESoCLote (lote) no es la llave, ESoChip (unidad/predio) sí lo es.
NO se agrega por localidad/UPZ desde ESTA fuente: no existe una llave espacial
verificable entre ESoChip y una geometría de lote/predio (Predio.PreCManz no es
compatible con Manz.ManCodigo, verificado). Esta limitación quedó documentada
como tal (regla de agent.md: "no asumas") pero SÍ se resolvió el problema por
otra vía: ver 03_limpieza/08_normalizacion_estrato_oficial.py, que usa una 14ª
fuente con geometría real por manzana ("Estratificación para Bogotá") y sí
permite el spatial join directo a UPZ/localidad. Ese script, no este, es el
que alimenta `estrato_promedio_oficial` en el dataset maestro (Fase 6).
Este script (Esoc.csv) queda solo como fuente secundaria/comparación.
"""
import os
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


df = pd.read_csv(os.path.join(BRONZE, 'Esoc.csv'), sep=';', dtype=str)
n0 = len(df)
df['ESoEstrato'] = pd.to_numeric(df['ESoEstrato'], errors='coerce')

n_cero = (df['ESoEstrato'] == 0).sum()
df_validos = df[df['ESoEstrato'].between(1, 6)].copy()
traza('Esoc', 'excluir estrato==0 y fuera de 1-6', 'código 0 = "sin estratificar" (rural/institucional/en trámite), no es un estrato real', int(n0 - len(df_validos)))

df_validos = df_validos.rename(columns={'ESoChip': 'chip', 'ESoCLote': 'cod_lote', 'ESoEstrato': 'estrato'})
df_validos[['chip', 'cod_lote', 'estrato']].to_parquet(
    os.path.join(SILVER, 'socioeconomico', 'estrato_por_unidad.parquet'), index=False)

dist_citywide = df_validos['estrato'].value_counts(normalize=True).sort_index() * 100
resumen = pd.DataFrame({'estrato': dist_citywide.index, 'pct_unidades_bogota': dist_citywide.values.round(2),
                         'n_unidades': df_validos['estrato'].value_counts().sort_index().values})
resumen.to_parquet(os.path.join(SILVER, 'socioeconomico', 'distribucion_estrato_citywide.parquet'), index=False)

traza('Esoc', 'NO se construye agregación por localidad/UPZ desde Esoc.csv',
      'ESoCLote (lote) NO es una llave espacial confiable a localidad/UPZ '
      '(el prefijo de 2 dígitos solo coincide con el código oficial de localidad '
      'en 6 de 42 grupos derivados, verificado en sesión previa); no existe en los '
      'datos disponibles una geometría de lote/predio ni una llave compatible '
      '(Predio.PreCManz de 2 dígitos no es compatible con Manz.ManCodigo de 9 dígitos, '
      'verificado). RESUELTO por otra fuente: ver 08_normalizacion_estrato_oficial.py '
      '(manzanaestratificacion.json, spatial join real).',
      len(df_validos))

print(f"Unidades válidas (estrato 1-6): {len(df_validos):,} / {n0:,}")
print(resumen)
print("\n⚠️  Estrato por UPZ/localidad desde Esoc.csv específicamente: NO EVALUABLE (sin llave espacial).")
print("   RESUELTO por otra fuente -- ver 03_limpieza/08_normalizacion_estrato_oficial.py")
print("   (manzanaestratificacion.json, spatial join real a UPZ/localidad, 98.5%/100% cobertura).")
print("   Esta salida (Esoc.csv) queda como fuente secundaria, sin agregación territorial.")
print("✅ silver/socioeconomico/ guardado.")
