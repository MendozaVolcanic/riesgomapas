/* vA_campamentos_vs_titular.js : sonda del verificador (frente A) sobre web/app.js real via fA_harness_evaluar.js.
 * Dos preguntas: (1) si el fenomeno no existiera el resultado seria distinto (se imprime el nivel y titular real por caso, con puntos de contraste); (2) si el arnes estuviera muerto, cargar() lanza ARNES MUERTO en vez de imprimir ceros. */
const { cargar } = require('./fA_harness_evaluar.js');
(async()=>{const h=await cargar();
const n=h.run('estado.campamentos.features.length'); let dentro=0, sd=0, k=0;
for(let i=0;i<n;i++){ const f=h.run(`estado.campamentos.features[${i}]`); const g=f.geometry;
 let pts=[]; if(g.type==='Point') pts=[g.coordinates]; else { const an=g.type==='Polygon'?g.coordinates[0]:g.coordinates[0][0]; let lon=0,lat=0; for(const p of an){lon+=p[0];lat+=p[1];} pts=[[lon/an.length,lat/an.length]]; }
 const r=h.evaluar(pts[0][0],pts[0][1],null);
 const en=r.campamentos.length>0; if(en) dentro++; 
 console.log(f.properties.nombre,'|',f.properties.tipo_riesgo,'|',f.properties.hogares,'| dentro:',en,'|',r.nivel,'|',r.titulo.slice(0,60)); if(en&&r.nivel==='sindato') sd++; }
console.log('campamentos',n,'puntos dentro',dentro,'con titular sindato',sd);
})();
