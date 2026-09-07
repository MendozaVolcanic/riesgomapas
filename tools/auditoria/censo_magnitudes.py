#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""censo_magnitudes.py — lista TODA constante numérica «que manda» en scripts/ y web/
(frente de magnitudes, GUIA_MAESTRA_AUDITORIAS.md §4), con contexto, para que el auditor
no dependa de su propio grep y su cobertura sea auditable.

Portado el 6-sep-2026 desde ARSAND/tools/auditoria/censo-magnitudes.py. Formas de
constante que manda: comparación (x < 4.0), asignación (ANCHO = 4), valor por omisión
(`or 45`, `?? 45`, `.get("k", 40)`), respaldo de ternario (`? a : 0.55`) y factor
(`x * 0.5`).

No decide nada. Imprime un TSV: archivo:línea | constante | expresión | pistas de unidades
(palabras px/m/metros/ha/m²/grados/fracción/km en los comentarios cercanos).

LAS DOS PREGUNTAS DEL INSTRUMENTO:
  1. Si estuviera roto imprimiría 0 filas: el auditor lo ve.
  2. Control positivo incorporado (--control): tiene que encontrar en
     scripts/18_vectorizar_laminas.py el 0.55 (fracción del alto que debe cubrir una línea de
     grilla) y el 210 (umbral de neutro), y en web/app.js el 6371000 (radio terrestre en m) y
     el 11 de ZOOM_MIN_PLANO. Si no, el censo no vale y sale con código 2.

Uso:  python tools/auditoria/censo_magnitudes.py [--control] [ruta ...]
"""
import io
import os
import re
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DEFAULT = [os.path.join(RAIZ, 'scripts'), os.path.join(RAIZ, 'web')]
IDENT = r'[A-Za-z_][A-Za-z0-9_.\[\]()>-]*'
NUM = r'-?\d+(?:\.\d+)?(?:e-?\d+)?'
FORMAS = [
    re.compile(IDENT + r'\s*(?:[<>]=?|==|!=)\s*(' + NUM + r')\b'),
    re.compile(r'\b(' + NUM + r')\s*[<>]=?\s*' + IDENT),
    re.compile(r'^\s*(?:const\s+|let\s+|var\s+)?' + IDENT + r'\s*=\s*(' + NUM + r')\s*[;#]?\s*(?:#.*|//.*)?$'),
    re.compile(r'(?:\bor\b|\?\?)\s*(' + NUM + r')\b'),
    re.compile(r'\.get\([^,)]+,\s*(' + NUM + r')\)'),
    re.compile(r':\s*(' + NUM + r')\s*[;)]'),
    re.compile(r'[*/+-]\s*(' + NUM + r')\b'),
]
PISTAS = re.compile(
    r'\b(px|p[ií]xel\w*|metro\w*|m|km|ha|hect[aá]rea\w*|m2|m²|grado\w*|fracci[oó]n|frac|'
    r'porcentaje|zoom|dpi|segundo\w*|ms|bytes?|KB|MB|celda\w*|escala|umbral|tolerancia|'
    r'radio|distancia|ancho|area|área)\b', re.I)
EXT = ('.py', '.js', '.html')
IGNORAR = ('vendor', '__pycache__', 'node_modules')
TRIVIALES = ('0', '1', '-1', '2', '0.0', '1.0')


def pistas(lineas, i):
    lo, hi = max(0, i - 6), min(len(lineas), i + 3)
    txt = ' '.join(l for l in lineas[lo:hi] if '#' in l or '//' in l or '*' in l)
    return ','.join(sorted(set(m.group(1).lower() for m in PISTAS.finditer(txt))))


def censar(paths):
    filas = []
    for p in paths:
        try:
            lineas = io.open(p, encoding='utf-8', errors='replace').read().split('\n')
        except OSError:
            continue
        en_doc = False
        for i, l in enumerate(lineas):
            s = l.strip()
            if s.count('"""') % 2 == 1:
                en_doc = not en_doc
                continue
            if en_doc or not s or s.startswith(('#', '//', '*', '/*')):
                continue
            vistos = set()
            for rx in FORMAS:
                for m in rx.finditer(l):
                    const = m.group(1)
                    if const in TRIVIALES:
                        continue
                    clave = (m.start(1), const)
                    if clave in vistos:
                        continue
                    vistos.add(clave)
                    filas.append((os.path.relpath(p, RAIZ).replace('\\', '/'), i + 1, const,
                                  m.group(0).strip()[:90], pistas(lineas, i)))
    return filas


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    control = '--control' in sys.argv
    paths = []
    for base in (args or DEFAULT):
        for d, _, fs in os.walk(base):
            if any(x in d for x in IGNORAR):
                continue
            for f in fs:
                if f.endswith(EXT):
                    paths.append(os.path.join(d, f))
    filas = censar(paths)
    out = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    out.write('archivo:linea\tconstante\texpresion\tpistas\n')
    for f in filas:
        out.write('%s:%d\t%s\t%s\t%s\n' % f)
    out.write('# %d constantes en %d archivos\n' % (len(filas), len(paths)))
    out.flush()
    if control:
        def tiene(arch, c):
            return any(arch in f[0] and f[2] == c for f in filas)
        ok = (tiene('18_vectorizar_laminas.py', '0.55') and tiene('18_vectorizar_laminas.py', '210')
              and tiene('app.js', '6371000') and tiene('app.js', '11'))
        sys.stderr.write('CONTROL POSITIVO: %s\n' % (
            'OK (0.55 y 210 en el script 18; 6371000 y 11 en app.js)' if ok
            else 'FALLA -- el censo no encuentra las constantes conocidas: no vale'))
        sys.exit(0 if ok else 2)


if __name__ == '__main__':
    main()
