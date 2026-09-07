# -*- coding: utf-8 -*-
"""702 — ¿la apertura con núcleo par corre la mancha? Cuadrado sintético, sin PDF."""
import sys,io
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
import numpy as np, cv2
for ancho in (3,4,5,6):
    k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(ancho,ancho))
    a=np.zeros((80,80),"uint8"); a[20:60,20:60]=1     # cuadrado 40x40, filas/cols 20..59
    o=cv2.morphologyEx(a,cv2.MORPH_OPEN,k)
    ys,xs=np.nonzero(o)
    print(f"ancho={ancho}  núcleo:\n{k}")
    print(f"  entrada  filas 20..59 cols 20..59  ({a.sum()} px)")
    print(f"  salida   filas {ys.min()}..{ys.max()} cols {xs.min()}..{xs.max()}  ({o.sum()} px)")
    print(f"  desplazamiento del centroide: dy={ys.mean()-39.5:+.2f} px  dx={xs.mean()-39.5:+.2f} px")
    print()
