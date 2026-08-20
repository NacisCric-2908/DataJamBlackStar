"""
Fase 16.3 - Ensamblado del HTML autocontenido
DataJam Bogota 2026

Junta src/head.html + src/body.html + el payload + src/app.js en un solo
archivo que se abre con doble clic, sin servidor, sin dependencias y sin red
(la unica peticion externa es la hoja de tipografias de Google Fonts, que
degrada a las fuentes del sistema si no hay conexion).

Se mantiene separado en tres fuentes porque editar CSS, marcado y logica en
un archivo de 190 KB con el JSON incrustado en la mitad es inmanejable.

Salida: outputs/dashboard_prototipo_atlas.html
"""
import os

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
PAYLOAD = os.path.join(BASE, 'data', 'dashboard', 'prototipo', 'payload.json')
DESTINO = os.path.join(BASE, 'outputs', 'dashboard_prototipo_atlas.html')


def leer(ruta):
    if not os.path.exists(ruta):
        raise SystemExit(f'Falta {ruta}')
    with open(ruta, encoding='utf-8') as fh:
        return fh.read()


def main():
    head = leer(os.path.join(SRC, 'head.html'))
    body = leer(os.path.join(SRC, 'body.html'))
    app = leer(os.path.join(SRC, 'app.js'))
    payload = leer(PAYLOAD)

    # el payload viaja dentro de un <script type="application/json">, asi que
    # una secuencia "</script" en los datos romperia el documento
    if '</script' in payload.lower():
        raise SystemExit('El payload contiene una etiqueta de cierre de script')

    html = (
        head.rstrip() + '\n\n'
        + body.rstrip() + '\n\n'
        + '<script type="application/json" id="payload">' + payload + '</script>\n'
        + '<script>\n' + app.rstrip() + '\n</script>\n'
    )

    os.makedirs(os.path.dirname(DESTINO), exist_ok=True)
    with open(DESTINO, 'w', encoding='utf-8') as fh:
        fh.write(html)

    print(f'Payload: {len(payload) / 1024:,.0f} KB')
    print(f'Salida:  {os.path.getsize(DESTINO) / 1024:,.0f} KB -> {DESTINO}')


if __name__ == '__main__':
    main()
