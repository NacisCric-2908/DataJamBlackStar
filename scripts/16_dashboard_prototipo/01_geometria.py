"""
Fase 16.1 - Geometria simplificada para el prototipo de tablero
DataJam Bogota 2026

Toma los dos GeoJSON de la capa de consumo (data/dashboard/spatial/) y los
reduce a un unico archivo liviano que se pueda incrustar dentro de un HTML
autocontenido. Los originales suman 5,1 MB, que es demasiado para embeber.

Que hace, en orden:
  1. Se queda con los 3 anillos mas grandes de cada entidad (descarta islas
     y artefactos de digitalizacion que no se ven a la escala del tablero).
  2. Simplifica cada anillo con Douglas-Peucker.
  3. Redondea las coordenadas a 5 decimales (~1 m en la latitud de Bogota).
  4. Excluye Sumapaz de la capa de localidades.

Sobre el punto 4: Sumapaz mide 780 km2, mas del doble que toda la Bogota
urbana junta, y deforma la proyeccion hasta dejar la ciudad como una mancha
ilegible. Ademas no tiene estrato oficial y ya queda fuera de los modelos por
localidad (que corren con n=19). Se excluye del mapa por coherencia con el
analisis, no por conveniencia visual, y queda declarado en el pie del tablero.

La simplificacion es SOLO para visualizacion. Ningun calculo del pipeline usa
esta geometria: las areas, los joins espaciales y las distancias salen de las
capas originales en data/gold/.

Salida: data/dashboard/prototipo/geo.json
"""
import json
import math
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SPATIAL = os.path.join(BASE, 'data', 'dashboard', 'spatial')
OUT = os.path.join(BASE, 'data', 'dashboard', 'prototipo')
os.makedirs(OUT, exist_ok=True)

TOLERANCIA = 0.00035   # grados, ~39 m
DECIMALES = 5
MAX_ANILLOS = 3
LOCALIDADES_EXCLUIDAS = {'20'}   # Sumapaz


def douglas_peucker(pts, tol):
    """Simplifica una polilinea conservando los vertices que definen su forma."""
    if len(pts) < 3:
        return pts

    def dist_a_segmento(p, a, b):
        if a == b:
            return math.hypot(p[0] - a[0], p[1] - a[1])
        dx, dy = b[0] - a[0], b[1] - a[1]
        t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))
        return math.hypot(p[0] - (a[0] + t * dx), p[1] - (a[1] + t * dy))

    d_max, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        d = dist_a_segmento(pts[i], pts[0], pts[-1])
        if d > d_max:
            d_max, idx = d, i

    if d_max > tol:
        izq = douglas_peucker(pts[:idx + 1], tol)
        der = douglas_peucker(pts[idx:], tol)
        return izq[:-1] + der
    return [pts[0], pts[-1]]


def limpiar(geom):
    """Normaliza Polygon/MultiPolygon a lista de poligonos ya simplificados."""
    if geom is None:
        return []
    tipo = geom.get('type')
    if tipo == 'Polygon':
        crudos = [geom['coordinates']]
    elif tipo == 'MultiPolygon':
        crudos = geom['coordinates']
    else:
        return []

    # solo el anillo exterior de cada parte, ordenados por numero de vertices
    exteriores = sorted((p[0] for p in crudos if p), key=len, reverse=True)

    salida = []
    for anillo in exteriores[:MAX_ANILLOS]:
        pts = [(c[0], c[1]) for c in anillo]
        simple = douglas_peucker(pts, TOLERANCIA)
        if len(simple) < 4:
            continue
        if simple[0] != simple[-1]:
            simple.append(simple[0])
        salida.append([[round(x, DECIMALES), round(y, DECIMALES)] for x, y in simple])
    return [[a] for a in salida]


def procesar(archivo, campo_id, excluir=frozenset()):
    with open(os.path.join(SPATIAL, archivo), encoding='utf-8') as fh:
        fc = json.load(fh)
    capa, descartados = {}, 0
    for feat in fc['features']:
        clave = str(feat['properties'][campo_id])
        if clave in excluir:
            descartados += 1
            continue
        polys = limpiar(feat.get('geometry'))
        if polys:
            capa[clave] = polys
    return capa, descartados


def main():
    upz, _ = procesar('upz_geometry.geojson', 'upz_id')
    loc, fuera = procesar('localidad_geometry.geojson', 'localidad_id',
                          excluir=LOCALIDADES_EXCLUIDAS)

    destino = os.path.join(OUT, 'geo.json')
    with open(destino, 'w', encoding='utf-8') as fh:
        json.dump({'upz': upz, 'loc': loc}, fh, separators=(',', ':'))

    origen_kb = sum(
        os.path.getsize(os.path.join(SPATIAL, f))
        for f in ('upz_geometry.geojson', 'localidad_geometry.geojson')
    ) / 1024
    print(f'UPZ:        {len(upz)} entidades')
    print(f'Localidades:{len(loc):4d} entidades ({fuera} excluida por regla)')
    print(f'Original:   {origen_kb:,.0f} KB')
    print(f'Salida:     {os.path.getsize(destino) / 1024:,.0f} KB -> {destino}')


if __name__ == '__main__':
    main()
