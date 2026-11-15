/* vA_clases_laminas_a_nivel.js : sonda del verificador (frente A) sobre web/app.js real via fA_harness_evaluar.js.
 * Dos preguntas: (1) si el fenomeno no existiera el resultado seria distinto (se imprime el nivel y titular real por caso, con puntos de contraste); (2) si el arnes estuviera muerto, cargar() lanza ARNES MUERTO en vez de imprimir ceros. */
const { cargar } = require('./fA_harness_evaluar.js');
(async()=>{const h=await cargar();
const n=h.run('estado.laminas.features.length'); const seen={};
for(let i=0;i<n;i++){ const f=h.run(`estado.laminas.features[${i}]`); const k=f.properties.comuna+'|'+f.properties.clase+'|'+!!f.properties.efecto_legal; if(seen[k]) continue;
 const g=f.geometry; const an=g.type==='Polygon'?g.coordinates[0]:g.coordinates[0][0];
 // centroide de 3 vertices que caiga dentro: probar promedio de vértices
 let lon=0,lat=0; for(const p of an){lon+=p[0];lat+=p[1];} lon/=an.length; lat/=an.length;
 let r=h.evaluar(lon,lat,null); if(!r.laminas.some(x=>x.properties.clase===f.properties.clase&&x.properties.comuna===f.properties.comuna)) continue;
 seen[k]=1; console.log(k,'->',r.nivel,'|',r.titulo,'| porQue:',h.porQue(r).replace(/<[^>]+>/g,' ').replace(/\s+/g,' ').slice(0,160)); }
})();
