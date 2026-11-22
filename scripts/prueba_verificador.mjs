// Prueba del Verificador contra enlaces REALES, corrida desde un servidor (GitHub Actions), sin publicar.
// Toma 30 productos del catálogo (10 de Falabella, 10 de Olímpica, 10 de Jumbo, con precio "antes" cuando hay)
// y guarda el veredicto de cada uno para revisarlo a mano y buscar falsos positivos.
// Uso: node scripts/prueba_verificador.mjs data/ofertas.json salida.json
import { readFileSync, writeFileSync } from "node:fs";
import handler from "../netlify/functions/verificar.mjs";

const [, , catalogo, salida] = process.argv;
const prods = JSON.parse(readFileSync(catalogo, "utf8")).productos.filter(p => !p.oculto && !p.condicion);
const elegir = t => {
  const de = prods.filter(p => p.tienda === t);
  const conAntes = de.filter(p => p.precio_antes), sinAntes = de.filter(p => !p.precio_antes);
  const paso = a => a.filter((_, i) => i % Math.max(1, Math.floor(a.length / 8)) === 0);
  return [...paso(conAntes).slice(0, 8), ...paso(sinAntes).slice(0, 2)];
};
const muestra = [...elegir("Falabella"), ...elegir("Olímpica"), ...elegir("Jumbo")];
const out = [];
for (const p of muestra) {
  const t0 = Date.now();
  try {
    const r = await handler(new Request("https://cazadoresdeofertas.netlify.app/api/verificar?url=" + encodeURIComponent(p.link)));
    const j = await r.json();
    out.push({ url: p.link, tienda: p.tienda, status: r.status, ms: Date.now() - t0, estado: j.estado || null, msg: j.msg || null,
      origen: j.origen ? { nombre: j.origen.nombre, modelo: j.origen.modelo, precio: j.origen.precio, antes: j.origen.precio_antes, propio: j.origen.propio } : null,
      tiendas: (j.tiendas || []).map(t => [t.tienda, t.nombre, t.precio, t.ean || null]), pruebas: (j.pruebas || []).map(x => x.signo + " " + x.texto),
      consultadas: j.consultadas || [] });
  } catch (e) { out.push({ url: p.link, tienda: p.tienda, error: String(e) }); }
}
writeFileSync(salida, JSON.stringify(out, null, 1));
const cuenta = {};
for (const o of out) cuenta[o.estado || o.msg || o.error] = (cuenta[o.estado || o.msg || o.error] || 0) + 1;
console.log(JSON.stringify(cuenta));
