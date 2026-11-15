# riesgomapas

Visor abierto de exposición a inundaciones para La Araucanía. Proyecto personal de
Nicolás Mendoza y Roberto Laregla, sin respaldo institucional.

## Traspaso

**El traspaso de este proyecto vive en [`docs/PROXIMA_SESION.md`](docs/PROXIMA_SESION.md).**
Un traspaso nuevo se agrega arriba y el anterior se degrada a histórico: nunca se
borra, porque saber qué se creía antes es lo que caza los falsos positivos.

Leer también, en este orden: [`REGLAS.md`](REGLAS.md), [`README.md`](README.md),
[`docs/INVENTARIO_FUENTES.md`](docs/INVENTARIO_FUENTES.md).

## Las reglas que no se negocian

Están completas en [`REGLAS.md`](REGLAS.md). Las tres que más se rompen por descuido:

1. **Las capas de evidencia nunca se fusionan.** A normativo, A derivado, B observado,
   C modelado, D operacional e inventario viajan separadas y etiquetadas. Un plan
   regulador con efecto legal y un modelo global de 1 km no dicen lo mismo, y
   promediarlos destruye lo único que hace defendible el dato. Lo valida un `assert`
   en `comun.procedencia()`.
2. **Ningún número sin su error declarado.** Un polígono derivado de una lámina lleva
   su RMSE en metros. Una geometría sin error declarado se lee como si fuera exacta.
3. **Auditar no es arreglar.** Un informe de auditoría es hipótesis, no veredicto: se
   mide antes de tocar. Mover un umbral hasta que el número quede bonito es el error
   que la auditoría viene a cazar.

## Auditorías

Los instrumentos van en `tools/auditoria/`, se commitean el mismo día, y cada uno
declara **sus dos preguntas**: qué mide, y cómo sabría que se equivoca. Todos llevan
`--control`, que fabrica el defecto y exige que el instrumento lo denuncie. Un
instrumento sin línea base roja no prueba nada.

Antes de lanzar auditores, leer `GUIA_MAESTRA_AUDITORIAS.md` del workspace.

## Estilo del texto que se entrega

**Sin guiones largos ni medios** en ningún `.md`, `.docx` ni texto proyectado. Antes
de entregar un documento: `grep -c "—" archivo.md` tiene que dar 0. Español de Chile,
formas de tú, «computador» y «celular».

Los documentos del paquete del practicante arrastran guiones largos de antes de esta
regla. Es deuda conocida, anotada en el traspaso.

## Cómo se corre

Orden completo en [`scripts/ORDEN.md`](scripts/ORDEN.md). Los dos comandos de uso diario:

```bash
python -m pytest tests/ -q
python scripts/20_paquete_practicante.py --provincia Malleco
```

Los datos crudos de `data/raw/` **no se modifican nunca**. Solo derivados.
