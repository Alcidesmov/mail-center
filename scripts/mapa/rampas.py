"""Rampas de cor do mapa: a vermelha é derivada da azul (mesma luminosidade em cada degrau).

Uso:  python3 scripts/mapa/rampas.py     -> imprime degrau, azul, vermelho
A azul (BLUE) é a rampa sequencial padrão do método de gráficos; a vermelha mantém
L (luminosidade) e C (croma) de cada degrau azul e troca só o matiz pelo do vermelho
categórico (#e34948), reduzindo o croma se a cor sair do espaço sRGB.
"""
import math


def srgb2lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin2srgb(c):
    c = max(0, min(1, c))
    return 255 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def hex2rgb(h):
    h = h.lstrip('#')
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def rgb2hex(r):
    return '#%02x%02x%02x' % tuple(round(x) for x in r)


def to_oklab(h):
    r, g, b = [srgb2lin(x) for x in hex2rgb(h)]
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = [x ** (1 / 3) for x in (l, m, s)]
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def from_oklab(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return [lin2srgb(x) for x in (r, g, bb)], (r, g, bb)


def oklch(h):
    L, a, b = to_oklab(h)
    return L, math.hypot(a, b), math.atan2(b, a)


def in_gamut(rgbl):
    return all(-1e-4 <= x <= 1 + 1e-4 for x in rgbl)


def make(L, C, H):
    while C > 0:
        rgb, lin = from_oklab(L, C * math.cos(H), C * math.sin(H))
        if in_gamut(lin):
            return rgb2hex(rgb)
        C -= 0.002
    return rgb2hex(from_oklab(L, 0, 0)[0])


BLUE = {100: '#cde2fb', 150: '#b7d3f6', 200: '#9ec5f4', 250: '#86b6ef', 300: '#6da7ec', 350: '#5598e7',
        400: '#3987e5', 450: '#2a78d6', 500: '#256abf', 550: '#1c5cab', 600: '#184f95', 650: '#104281', 700: '#0d366b'}
H_RED = oklch('#e34948')[2]
RED = {k: make(oklch(v)[0], oklch(v)[1], H_RED) for k, v in BLUE.items()}

if __name__ == '__main__':
    for k in BLUE:
        print(k, BLUE[k], RED[k])
