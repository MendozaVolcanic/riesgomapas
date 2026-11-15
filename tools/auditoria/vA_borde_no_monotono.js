/* vA_borde_no_monotono.js : sonda del verificador (frente A) sobre web/app.js real via fA_harness_evaluar.js.
 * Dos preguntas: (1) si el fenomeno no existiera el resultado seria distinto (se imprime el nivel y titular real por caso, con puntos de contraste); (2) si el arnes estuviera muerto, cargar() lanza ARNES MUERTO en vez de imprimir ceros. */
const { cargar } = require('./fA_harness_evaluar.js');
(async()=>{const h=await cargar();
const lon=-72.95729860403075,lat=-38.7465676360515;
for (const m of [0,60,120]) { const r=h.evaluar(lon+m/(111320*Math.cos(lat*Math.PI/180)),lat,null); console.log(m,'m',r.nivel,'|',r.titulo,'| borde',r.borde?Math.round(r.borde.d):null,'graves300',r.cerca.filter(c=>c.d<=300&&['Muy Alto','Alto'].includes(c.f.properties.nivel)).length);} })();
