"""
Fase 6 (complemento) — Data dictionary + registro de lineage
DataJam Bogotá 2026

Por cada variable Gold: fuente, transformación, fórmula, unidad, unidad espacial,
periodo temporal, supuestos. Responde las 8 preguntas de agent.md
("Data lineage" en la arquitectura Medallion).
"""
import os
import pandas as pd

OUT = os.path.dirname(__file__)

filas = [
    dict(variable='estrato_promedio_oficial / estrato_modal_oficial', fuente='Bronze/manzanaestratificacion.json '
         '("Estratificación para Bogotá", Secretaría Distrital de Planeación, datosabiertos.bogota.gov.co)',
         transformacion='spatial join (representative_point within) de 39.150 manzanas con ESTRATO válido (1-6) a UPZ/Localidad; agregación mean/mode',
         formula='mean(ESTRATO) o mode(ESTRATO) agrupado por cod_upz o cod_localidad, ponderado por manzana (no por área)',
         unidad='estrato (1-6)', unidad_espacial='UPZ (98.5% cobertura) y Localidad (100% urbana, Sumapaz sin datos)',
         periodo='snapshot 2025-11-20 (fecha de actualización del dataset fuente)',
         supuestos='FUENTE OFICIAL, reemplaza al proxy; cada manzana pesa igual sin importar su área o población'),
    dict(variable='estrato_promedio_reportado', fuente='Bronze/incidentes-atendidos-por-uaecob-*.csv (campo ESTRATO)',
         transformacion='promedio del estrato autorreportado en incidentes UAECOB, agregado por UPZ/localidad',
         formula='mean(estrato) agrupado por cod_upz o cod_localidad', unidad='estrato (1-6)',
         unidad_espacial='UPZ y Localidad', periodo='2016-2020 (agregado, sin dimensión anual en el master cross-sectional)',
         supuestos='PROXY histórico, se conserva solo para comparación (r=0.96 con el oficial) -- cubre solo zonas con incidentes reportados, sesgo de selección hacia zonas con más actividad de bomberos'),
    dict(variable='deficit_aseo_relativo', fuente='Silver/aseo/cestas.parquet + contenerizacion.parquet',
         transformacion='z-score invertido de (densidad_cestas_km2 + densidad_contenedores_km2)',
         formula='-((x - mean(x)) / std(x))', unidad='z-score adimensional (relativo a la ciudad)',
         unidad_espacial='UPZ y Localidad (calculado independientemente en cada nivel)', periodo='snapshot actual, sin fecha de instalación confiable',
         supuestos='mayor valor = menos infraestructura relativa a la media de la ciudad; NO es un déficit "absoluto" ni normativo (no compara contra un estándar oficial de cobertura)'),
    dict(variable='n_puntos_criticos / densidad_puntos_criticos_km2', fuente='Bronze/puntos_criticos_arrojo_clandestino_residuos.geojson',
         transformacion='spatial join point-in-polygon (within) a UPZ/Localidad',
         formula='conteo; densidad = n / area_km2', unidad='conteo; conteo/km²',
         unidad_espacial='UPZ y Localidad', periodo='snapshot actual (478 puntos, sin fecha)',
         supuestos='"Observación"=ACTIVO en el 100% de los registros -- no hay distinción de puntos históricos/resueltos'),
    dict(variable='n_incidentes_total / densidad_incidentes_km2', fuente='Bronze/incidentes-atendidos-por-uaecob-*.csv',
         transformacion='join a UPZ por código numérico extraído del campo libre "UPZ" (99.2% de match); conteo agregado',
         formula='count(); densidad = n / area_km2', unidad='conteo; conteo/km²',
         unidad_espacial='UPZ (99.2% cobertura) y Localidad (por nombre normalizado)', periodo='2016-2020',
         supuestos='0.8% de incidentes sin UPZ resoluble (zona rural/fuera de Bogotá/"por definir"), excluidos'),
    dict(variable='homicidios_cont / homicidios_total_oficial', fuente='Bronze/DAILoc.geojson',
         transformacion='CMH*CONT: suma de columnas anuales (CMH18CONT..CMH26CONT). CMHTOTAL: campo oficial del dataset, sin transformar',
         formula='CONT = sum(CMH{yy}CONT); TOTAL = CMHTOTAL (tal cual)', unidad='conteo de homicidios',
         unidad_espacial='Localidad únicamente (DAILoc no trae UPZ)', periodo='CONT: 2018-2026 explícito; TOTAL: periodo no documentado por la fuente',
         supuestos='⚠️ CONT (4.740) y TOTAL (11.445) NO coinciden -- causa no determinada, se reportan ambos sin elegir uno'),
    dict(variable='poblacion_total / poblacion_mujeres / poblacion_0_14',
         fuente='Silver/poblacion/poblacion_upz.parquet (15ª fuente: proyecciones DANE/SDP 2005-2035)',
         transformacion='agregación de los grupos de edad por sexo; join por código UPZ entero (112/112 de cobertura)',
         formula='suma de columnas Hombres_* y Mujeres_*; niñez = grupos con edad inicial <15',
         unidad='habitantes', unidad_espacial='UPZ y Localidad',
         periodo='serie 2005-2035; el pipeline usa 2024',
         supuestos='son PROYECCIONES sobre el Censo 2018, no un conteo observado; la fuente UPZ cubre solo Cabecera Municipal (suelo urbano)'),
    dict(variable='densidad_poblacional_hab_km2',
         fuente='Silver/poblacion/ + Silver/territorio/',
         transformacion='cociente directo', formula='poblacion_total / area_km2',
         unidad='hab/km²', unidad_espacial='UPZ y Localidad', periodo='2024',
         supuestos='confusor clave: las UPZ de estrato bajo son sistemáticamente más densas (rho=-0.50 con estrato)'),
    dict(variable='cestas_por_1000hab / contenedores_por_1000hab',
         fuente='Silver/aseo/ + Silver/poblacion/',
         transformacion='normalización por población en vez de por área',
         formula='n / poblacion_total * 1000', unidad='unidades por 1.000 habitantes',
         unidad_espacial='UPZ y Localidad', periodo='infraestructura: snapshot actual; población: 2024',
         supuestos='⚠️ se calcula solo en UPZ residenciales (>=1000 hab); en parques/aeropuerto el denominador diminuto produce tasas sin sentido'),
    dict(variable='deficit_aseo_percapita',
         fuente='Silver/aseo/ + Silver/poblacion/',
         transformacion='z-score invertido de la cobertura conjunta por habitante',
         formula='-((x - mean(x)) / std(x)) sobre (cestas_por_1000hab + contenedores_por_1000hab)',
         unidad='z-score adimensional', unidad_espacial='UPZ y Localidad', periodo='2024',
         supuestos='NO es comparable en escala con deficit_aseo_relativo (que se normaliza por km²); la media/std se calculan solo sobre UPZ residenciales'),
    dict(variable='puntos_criticos_por_100milhab / incidentes_por_100milhab / homicidios_por_100milhab',
         fuente='Silver/aseo/ + Silver/emergencias/ + Silver/seguridad/ + Silver/poblacion/',
         transformacion='tasas por población', formula='n / poblacion * 1e5',
         unidad='casos por 100.000 habitantes', unidad_espacial='UPZ (arrojo/incidentes) y Localidad (homicidios)',
         periodo='2024 para el denominador', supuestos='el numerador es acumulado del periodo de cada fuente, el denominador es un corte de 2024 -- no es una tasa anual estricta'),
    dict(variable='n_cuadrantes / densidad_cuadrantes_km2', fuente='Bronze/cuadrantepolicia.geojson',
         transformacion='spatial join intersects (no within) a UPZ/Localidad -- un cuadrante puede cruzar límites administrativos',
         formula='conteo; densidad = n / area_km2', unidad='conteo; conteo/km²',
         unidad_espacial='UPZ y Localidad', periodo='snapshot actual',
         supuestos='suma >100% del total de cuadrantes por diseño (un cuadrante cuenta en cada zona que cruza)'),
    dict(variable='dist_estacion_bomberos_m', fuente='Bronze/ebom.geojson (17 estaciones)',
         transformacion='distancia euclidiana mínima del centroide UPZ/Localidad a la estación más cercana, EPSG:3116',
         formula='min(distance(centroide, estacion_i))', unidad='metros',
         unidad_espacial='UPZ y Localidad', periodo='snapshot actual (17 estaciones)',
         supuestos='distancia euclidiana, no de red vial -- subestima la distancia real de desplazamiento'),
    dict(variable='deficit_aseo_relativo (localidad)', fuente='igual que UPZ, recalculado sobre n=20',
         transformacion='mismo z-score, pero la media/std se calculan sobre las 20 localidades, no las 112 UPZ',
         formula='-((x - mean_20(x)) / std_20(x))', unidad='z-score adimensional',
         unidad_espacial='Localidad', periodo='snapshot actual',
         supuestos='NO es la misma escala que la versión UPZ -- "alto déficit" en localidad no es directamente comparable a "alto déficit" en UPZ'),
]

df = pd.DataFrame(filas)
df.to_csv(os.path.join(OUT, 'data_dictionary.csv'), index=False)

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'data', 'gold')
os.makedirs(GOLD, exist_ok=True)
df.to_parquet(os.path.join(GOLD, 'data_dictionary.parquet'), index=False)

print(df[['variable', 'unidad_espacial', 'periodo']].to_string(index=False))
print(f"\n✅ Data dictionary: {len(df)} variables documentadas en 06_construccion_variables/data_dictionary.csv")
print("   Lineage completo (fuente->transformación->registros afectados) ya en 03_limpieza/trazabilidad.csv (20 entradas)")
