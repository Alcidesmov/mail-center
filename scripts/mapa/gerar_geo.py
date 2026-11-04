"""Gera app/dados/br_estados_geo.json (contornos dos 27 estados já projetados, em caminhos SVG).

Uso:
    pip install shapely
    curl -o estados.geojson https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson
    python3 scripts/mapa/gerar_geo.py estados.geojson app/dados/br_estados_geo.json
"""
import json
import math
import sys

from shapely.geometry import shape

LAT0 = -14.0   # latitude de referência da projeção
S = 15.0       # unidades do desenho por grau
COS = math.cos(math.radians(LAT0))
TOLERANCIA = 0.045   # simplificação, em graus (~5 km)


def proj(lon, lat):
    return ((lon + 74.1) * COS * S, (5.4 - lat) * S)


def main(entrada, saida):
    g = json.load(open(entrada, encoding='utf-8'))
    out, allx, ally = {}, [], []
    for f in g['features']:
        sig, nome = f['properties']['sigla'], f['properties']['name']
        geom = shape(f['geometry'])
        polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
        # tira ilhas oceânicas distantes (Noronha, Trindade) e fragmentos minúsculos
        keep = [p for p in polys if p.centroid.x < -34.8 and p.area > 0.04] or [max(polys, key=lambda p: p.area)]
        keep = [p.simplify(TOLERANCIA, preserve_topology=True) for p in keep]
        d = ''
        for p in keep:
            for ring in [p.exterior] + list(p.interiors):
                pts = [proj(x, y) for x, y in ring.coords]
                allx += [a for a, _ in pts]
                ally += [b for _, b in pts]
                d += 'M' + 'L'.join(f'{a:.1f},{b:.1f}' for a, b in pts) + 'Z'
        big = max(keep, key=lambda p: p.area)
        rp = big.representative_point()          # ponto de rótulo garantidamente dentro do estado
        cx, cy = proj(rp.x, rp.y)
        out[sig] = {'nome': nome, 'd': d, 'cx': round(cx, 1), 'cy': round(cy, 1)}
    W, H = max(allx), max(ally)
    json.dump({'W': round(W + 70, 1), 'H': round(H + 4, 1), 'maxx': round(W, 1), 'uf': out},
              open(saida, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('viewBox', round(W + 70), round(H + 4), '|', len(out), 'estados')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
