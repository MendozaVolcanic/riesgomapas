# Reglas del proyecto

> Estas reglas no son estilo. Cada una está acá porque **ya se rompió algo** por
> no seguirla, y al lado de cada una está qué se rompió. Si alguna te parece
> exagerada, lee el caso: probablemente el síntoma fue mudo.

Aplican a los dos autores y a cualquiera que trabaje en el repositorio,
practicante incluido.

---

## 1. Sobre el dato

### 1.1 Nunca inventar un valor

Ni una coordenada, ni un año, ni una clase. Si la fuente no lo declara, va
**«no declarado por la fuente»** y el visor lo muestra así.

> *Por qué*: el año del plan y el año de su estudio de riesgo son cosas
> distintas. El PRC de Angol es de 2022 y su Estudio de Riesgo, de 2013. Rellenar
> uno con el otro habría hecho parecer moderna una cartografía de hace trece
> años, hecha sin hidráulica.

### 1.2 Todo dato publicado declara fuente, año, método e incertidumbre

Lo impone `comun.procedencia()`, que valida la capa de evidencia con un `assert`.
**Si un producto no puede declarar su procedencia, no se publica.**

### 1.3 Las cuatro capas de evidencia nunca se fusionan

**A** normativo · **B** observado · **C** modelado · **D** operacional. Nunca se
promedian, ni se unen, ni se saca una capa «síntesis».

`inventario` es una quinta categoría de procedencia y **no es una capa de
evidencia**: habla de lo que sabemos del territorio, no del territorio. Existe
separada justamente para que «acá no hay cartografía» no pueda leerse jamás como
«acá no se inunda».

### 1.4 Distinguir el fenómeno, no sólo la amenaza

Inundación fluvial y anegamiento por drenaje son fenómenos distintos: otra
física, otra mitigación, otro servicio responsable.

> *Por qué*: se puede medir. Contra la huella satelital, los puntos de desborde
> dan ×2,1 de enriquecimiento y los de colector ×1,0 — azar puro. Mezclarlos
> diluyó la verificación de nuestra propia capa de ×2,8 a ×1,7. Y aun sabiéndolo,
> la capa A publicaba 3 polígonos de anegamiento, 1 de napa y 2 de inundación
> litoral bajo el titular «área de riesgo por inundación».

### 1.5 Distinguir el peso legal

**Vigente** rige hoy. **Anteproyecto** es una propuesta en tramitación que no
obliga a nadie. **Derivado** es geometría que construimos nosotros desde una
figura impresa: el contenido es de la fuente, la ubicación es nuestra.

Va escrito en el dato (`estado_tramite`) y visible en pantalla con **texto,
no sólo color**.

> *Por qué*: los 20 planos publicados son anteproyectos y se mostraban como
> «Plano original del Plan Regulador» bajo la capa que el sitio llama «la única
> con efecto jurídico».

### 1.6 `data/raw/` es de sólo lectura

Lo descargado no se modifica nunca. Todo derivado va a `data/processed/`, y lo
que consume el visor a `web/data/`.

---

## 2. Cuándo un script debe caerse

Ésta es la regla más valiosa del repositorio y la que más veces evitó un
desastre silencioso:

- **Dato AUSENTE → degradar y decirlo.** Si falta el censo, la población va en
  `None` y el visor muestra «sin dato».
- **Dato INCOHERENTE → `raise SystemExit` con instrucción.** Una causa sin
  clasificar, un nombre de comuna que no existe, dos escalas distintas en un
  mismo plano, un índice previo ilegible.

> *Por qué*: lo contrario produce el peor modo de falla de este proyecto — un
> resultado plausible y equivocado. Cinco causas de SENAPRED se estaban yendo al
> grupo equivocado en silencio hasta que el pipeline empezó a caerse.

**Un índice previo ilegible es motivo para parar, no para reescribirlo.**

---

## 3. Los índices agregados se FUSIONAN, no se sobrescriben

Cualquier script que escriba un índice y acepte un filtro (`--comuna`, `--id`,
`--limite`) tiene que leer lo previo, fusionar por una clave estable y escribir
la unión.

> *Por qué*: **pasó cuatro veces.** La última, `07_buscar_laminas_riesgo.py`
> truncaba el índice a 40 documentos en su corrida NORMAL —`--limite` vale 40 por
> omisión y hay 173— y con él el catálogo público. Sin error, sin aviso: comunas
> enteras desaparecían del visor.

---

## 4. Sobre las pruebas

### 4.1 Función nueva, comprobación nueva

Si se agrega una capa o una funcionalidad, hay que agregarle comprobaciones. Su
verde no significa nada si nadie la mira.

> *Por qué*: al integrar la capa B la auditoría daba **108/108 sin haberla mirado
> ni una vez**.

### 4.2 Una comprobación tiene que poder fallar

Antes de dar por buena una prueba, verificar que **falla cuando debe**.

> *Por qué*: la prueba de fuga de planos comprobaba «0 capas → 0 capas» a un zoom
> donde ningún plano llega a cargarse. Pasaba siempre. Al endurecerla apareció
> una fuga real — y además, que el arreglo original no funcionaba.

### 4.3 Cada bloque deja el estado que necesita

No heredar la pestaña abierta, el zoom ni las capas encendidas del bloque
anterior. Si el orden de las comprobaciones cambia el resultado, la auditoría es
frágil y miente.

### 4.4 Esperar por contenido, no por tiempo

`wait_for_function`, no `wait_for_timeout`. Una prueba que a veces pasa esconde
más de lo que descubre.

### 4.5 Antes de declarar algo arreglado, correr la auditoría

```bash
python -m pytest tests -q
python tests/auditoria_datos.py
python tests/auditoria_e2e.py
```

> *Por qué*: tres de los cuatro hallazgos del primer informe de auditoría eran
> bugs de la propia prueba.

---

## 5. Sobre las fuentes

### 5.1 Un 403, un 500 o «requiere credenciales» no significa cerrado

Antes de anotar una fuente como caída: reintentar con **encabezados de navegador
real**, y recorrer los espejos.

> *Por qué*: **ya van cuatro veces.** Sentinel-1 estaba «bloqueado por
> credenciales» y era propiedad de un proveedor, no del dato. El GORE daba 403.
> El SEIA daba 500. La DGA daba 403 a curl pelado y responde 200 con
> `User-Agent` y `Referer`. Y `doh.mop.gob.cl` «casi no publicaba» mientras el
> acervo real del MOP vivía en dos repositorios DSpace con API abierta.

### 5.2 Verificar leyendo bytes, no la existencia del registro

Que un catálogo liste un documento no significa que se pueda bajar.

### 5.3 Lo que NO rinde también se anota

`docs/INVENTARIO_FUENTES.md` §6b existe para que nadie repita el intento. Los
PEGH están ahí: existen, se bajan, y **no traen cartografía de inundación**
—contadas sus 307 figuras—.

---

### 5.4 El título de una lámina nombra su MARCO, no lo que mapea

Descubierto el 30-ago-2026 y caro: la lámina «Mapa Inundación Subcuenca Ríos
Malleco y Vergara» de la DGA (SIT N°449) se bajó y se vectorizó porque prometía
ser la única cartografía que alcanzara a Ercilla y Los Sauces.

Se georreferenció **perfecto** —escala verificada en ambos ejes con 0,09 % de
diferencia, y los puntos de SENAPRED caen exactos sobre cada pueblo— y aun así no
mapea **ni un solo polígono de riesgo** dentro de esa subcuenca: el rojo de la
leyenda está todo en el corredor del Biobío. La subcuenca era el marco del mapa,
no su contenido.

**Antes de invertir en georreferenciar, mirar dónde caen las clases de la
leyenda, no hasta dónde llega la hoja.** Y validar siempre contra algo que no
haya participado en la derivación: 0 de 77 puntos críticos a menos de 300 m, y
0,1 % de intersección con el modelo del GORE, lo dijeron sin ambigüedad.

## 6. Sobre el orden del repositorio

### 6.1 El número del script NO es el orden de ejecución

Del 01 al 10 coincide; del 11 en adelante el número es la fecha en que se
escribió. El orden real está en [`scripts/ORDEN.md`](scripts/ORDEN.md).

Cada script declara en su docstring **`Requiere:`** además de `Salida:`.

### 6.2 Convenciones de nombres

- `data/processed/` — guión bajo y ámbito: `senapred_puntos_criticos_araucania.geojson`
- `web/data/` — guión medio, sin ámbito, sin tildes: `puntos-criticos-inundacion.geojson`
- Todo en **EPSG:4326** en disco; se reproyecta al vuelo.

### 6.3 A `web/data/` va sólo el subconjunto que el visor consume

El universo completo se queda en `data/processed/`.

### 6.4 Lo regenerable y pesado no se versiona

`data/raw/` (2,8 GB), el censo (73 MB), las cachés y las capturas de auditoría.
Si un script valida sus propios totales, su salida no aporta nada en el
historial.

---

## 7. Sobre lo que se publica al público

### 7.1 Ausencia de dato no es ausencia de riesgo

Va escrito en el frontend, en el texto que se comparte y en cada archivo que se
entrega. No se quita «para que no asuste».

### 7.2 Nunca las palabras «alerta», «aviso», «pronóstico» ni «zona de evacuación»

El SAE es facultad exclusiva de SENAPRED. Tampoco sus colores ni sus logos.

### 7.3 El sitio dice quién lo hace y que espera dejar de hacer falta

Autoría explícita, sin respaldo institucional, y el objetivo de volverse
innecesario. No es adorno: es lo que separa un proyecto ciudadano de algo que se
puede leer como información oficial.

### 7.4 Subir `VERSION` en `web/sw.js` en cada cambio del frontend

Sin eso el service worker sirve la versión vieja y los arreglos no llegan.

### 7.5 No se registra nada del usuario

La consulta ocurre en el dispositivo. Sin analítica, sin cookies, sin logs de
dirección ni de coordenada. La Ley 21.719 rige desde el 1-dic-2026 y la
geolocalización es dato personal.

---

## 8. Al cerrar una sesión de trabajo

1. Correr las tres pruebas de §4.5.
2. Anotar en `docs/PROXIMA_SESION.md` **lo que no se pudo hacer y por qué**. Esa
   lista vale tanto como lo que sí salió: evita que la próxima persona repita el
   intento.
3. Si apareció una fuente nueva o una que no rinde, al inventario **en el
   momento**, no al final. La sesión se puede cortar.
