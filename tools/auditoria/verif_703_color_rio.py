# -*- coding: utf-8 -*-
"""703 — ¿el río de Angol tiene el mismo azul que «Alto»? Medido en la imagen de origen."""
import sys,io,json
sys.stdout=io.TextIOWrapper(sys.stdout.buffer,encoding="utf-8")
from pathlib import Path
import numpy as np, cv2
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/"scripts"))
import importlib.util
spec=importlib.util.spec_from_file_location("v18",R/"scripts/18_vectorizar_laminas.py")
v18=importlib.util.module_from_spec(spec); spec.loader.exec_module(v18)
pdf=R/"data/raw/documentos/angol/Estudio_Riesgo.pdf"
im=v18.imagenes_de(pdf,30)[0]
a=np.array(im).astype(int); h,w,_=a.shape
print(f"imagen de origen {w}x{h}")
ALTO=np.array([4,78,163]); MEDIO=np.array([0,114,255]); TOL=45; ANCHO=4
d_alto=np.linalg.norm(a-ALTO,axis=2); d_medio=np.linalg.norm(a-MEDIO,axis=2)
gan=np.stack([d_alto,d_medio]).argmin(0); dmin=np.stack([d_alto,d_medio]).min(0)
cruda_alto=(gan==0)&(dmin<TOL)
k=cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(ANCHO,ANCHO))
limpia=cv2.morphologyEx(cruda_alto.astype("uint8"),cv2.MORPH_OPEN,k).astype(bool)
comido=cruda_alto&~limpia
print(f"px 'Alto' crudos={cruda_alto.sum()}  tras apertura={limpia.sum()}  comidos={comido.sum()} ({100*comido.sum()/cruda_alto.sum():.1f} %)")
# componentes conexas de lo comido: las lineas largas y delgadas son candidatas a rio
n,lab,st,cen=cv2.connectedComponentsWithStats(comido.astype("uint8"),8)
larg=sorted(range(1,n),key=lambda i:-st[i,cv2.CC_STAT_AREA])[:8]
print("\ncomponentes mayores de lo comido por la apertura (¿río o franja legítima?):")
for i in larg:
    x,y,ww,hh,ar=st[i]
    m=lab==i
    rgb=a[m].mean(0)
    print(f"  area={ar:5d} px  bbox {ww}x{hh}  RGB medio=({rgb[0]:.0f},{rgb[1]:.0f},{rgb[2]:.0f})  "
          f"dist a ALTO={np.linalg.norm(rgb-ALTO):.1f}  dist a MEDIO={np.linalg.norm(rgb-MEDIO):.1f}  elongacion={max(ww,hh)/max(1,min(ww,hh)):.1f}")
# ¿cual es el color real de la red hidrica? buscar trazos finos oscuros azules
print("\n[premisa] color declarado 'Alto' = (4,78,163); 'Medio' = (0,114,255)")
# k-means sobre los pixeles clasificados como Alto crudo
px=a[cruda_alto]
Z=np.float32(px)
crit=(cv2.TERM_CRITERIA_EPS+cv2.TERM_CRITERIA_MAX_ITER,20,1.0)
_,lb,cn=cv2.kmeans(Z,3,None,crit,5,cv2.KMEANS_PP_CENTERS)
import collections
cc=collections.Counter(lb.ravel().tolist())
print("k-means (k=3) sobre los píxeles crudos de 'Alto':")
for j,c in enumerate(cn):
    print(f"  centro=({c[0]:.0f},{c[1]:.0f},{c[2]:.0f})  n={cc[j]}  dist a ALTO={np.linalg.norm(c-ALTO):.1f}")
# color de los pixeles COMIDOS (lineas) vs los que SOBREVIVEN
print(f"\nRGB medio de los píxeles COMIDOS   = {a[comido].mean(0).round(0)}  (n={comido.sum()})")
print(f"RGB medio de los píxeles QUE QUEDAN = {a[limpia].mean(0).round(0)}  (n={limpia.sum()})")
print(f"  distancia entre esos dos centros = {np.linalg.norm(a[comido].mean(0)-a[limpia].mean(0)):.1f}")
