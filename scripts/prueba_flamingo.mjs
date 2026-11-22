// Prueba única: ¿Flamingo responde al buscador y al Verificador desde un servidor? (GitHub Actions, sin publicar)
import { writeFileSync } from "node:fs";
import buscar from "../netlify/functions/buscar.mjs";
import verificar from "../netlify/functions/verificar.mjs";
const out = { buscador: {}, verificador: [] };
for (const q of ["freidora de aire", "ps5 slim", "televisor challenger 43", "lavadora", "celular samsung a16"]) {
  const r = await buscar(new Request("https://cazadoresdeofertas.netlify.app/api/buscar?q=" + encodeURIComponent(q)));
  const j = await r.json();
  out.buscador[q] = { tiendas: j.tiendas, productos: (j.productos || []).slice(0, 8).map(p => ({ v: p.veredicto, n: p.n, nombre: p.nombre, tiendas: p.tiendas.map(t => [t.tienda, t.precio, t.ean || null, t.link]), ext: p.externas.length })) };
}
const links = Object.values(out.buscador).flatMap(b => b.productos.flatMap(p => p.tiendas.filter(t => t[0] === "Flamingo").map(t => t[3]))).slice(0, 8);
for (const url of links) {
  const r = await verificar(new Request("https://cazadoresdeofertas.netlify.app/api/verificar?url=" + encodeURIComponent(url)));
  const j = await r.json();
  out.verificador.push({ url, status: r.status, estado: j.estado || j.msg, origen: j.origen && [j.origen.nombre, j.origen.precio, j.origen.precio_antes, j.origen.vendedor, j.origen.ean], tiendas: (j.tiendas || []).map(t => [t.tienda, t.precio]), pruebas: (j.pruebas || []).map(p => p.signo + " " + p.texto) });
}
writeFileSync(process.argv[2], JSON.stringify(out, null, 1));
console.log(JSON.stringify(Object.fromEntries(Object.entries(out.buscador).map(([q, b]) => [q, b.tiendas.map(t => `${t.tienda}:${t.ok ? t.n : "X"}`).join(" ")]))));
