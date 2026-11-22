// Verificador: GET /api/verificar?url=<enlace del producto>
// Lee el producto en su tienda, busca la MISMA referencia en las otras tiendas, revisa nuestro historial
// y responde: oferta_real | dudosa | precio_inflado | insuficiente, siempre con las pruebas.
import { createHash } from "node:crypto";
import { TIENDAS } from "./lib/tiendas.mjs";
import { compararOfertas, normTexto } from "./lib/comparar.mjs";
import { verificar } from "./lib/verificar.mjs";
import { TIENDA_POR_HOST, SE_PUEDE_LEER, leerFichaFalabella, leerFichaVtex, urlFichaVtex } from "./lib/producto.mjs";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36";
const HIST_URL = "https://raw.githubusercontent.com/arojotobon-fm/caza-ofertas/historial/precios.json";
const BASE = { "Olímpica": "https://www.olimpica.com", "Jumbo": "https://www.jumbocolombia.com" };
const limpio = l => String(l || "").split("?")[0].split("#")[0].replace(/\/+$/, "").toLowerCase();
const resp = (data, status = 200, cache = true) => new Response(JSON.stringify(data), { status, headers: {
  "content-type": "application/json; charset=utf-8", "cache-control": "public, max-age=0, must-revalidate",
  ...(cache ? { "netlify-cdn-cache-control": "public, durable, s-maxage=900, stale-while-revalidate=300", "netlify-vary": "query=url" } : {}) } });

async function traer(url, tipo = "text", ms = 8000) {
  const ctrl = new AbortController(), t = setTimeout(() => ctrl.abort(), ms);
  try {
    const r = await fetch(url, { signal: ctrl.signal, headers: { "user-agent": UA, "accept-language": "es-CO,es;q=0.9" } });
    if (!r.ok && r.status !== 206) throw new Error("HTTP " + r.status);
    return tipo === "json" ? await r.json() : await r.text();
  } finally { clearTimeout(t); }
}

async function historialDe(origen, sitio) {
  const out = {};
  const sumar = (fecha, precio, antes) => { if (precio > 0) out[fecha] = { fecha, precio, antes: antes || null }; };
  // 1) Lectura diaria automática (rama "historial" del repositorio)
  try { const h = await traer(HIST_URL, "json", 4000); const e = h[limpio(origen.link)];
    if (e) for (const [f, v] of Object.entries(e.p || {})) sumar(f, v, (e.a || {})[f]); } catch {}
  // 2) Historial del catálogo publicado en la página
  try { const h = await traer(sitio + "/data/historial.json", "json", 4000);
    const id = createHash("sha1").update(origen.link.split("?")[0] + "|").digest("hex").slice(0, 12);
    const e = h[id]; if (e) for (const [f, v] of Object.entries(e.p || {})) if (!out[f]) sumar(f, v); } catch {}
  return Object.values(out);
}

export default async (req) => {
  const u = new URL(req.url), url = (u.searchParams.get("url") || "").trim();
  let host; try { host = new URL(url).host; } catch { return resp({ ok: false, msg: "Pega el enlace completo del producto (empieza por https://)." }, 400, false); }
  const tienda = TIENDA_POR_HOST[host];
  if (!tienda) return resp({ ok: false, msg: "Todavía no revisamos esa tienda. Por ahora: Falabella, Olímpica y Jumbo." }, 422, false);
  if (!SE_PUEDE_LEER.has(tienda)) return resp({ ok: false, msg: `Por ahora ${tienda} no nos deja leer sus productos desde aquí. Escribe el nombre y la referencia del producto en el buscador.` }, 422, false);

  let origen;
  try {
    origen = tienda === "Falabella" ? leerFichaFalabella(await traer(url), url)
      : leerFichaVtex(tienda, BASE[tienda], await traer(urlFichaVtex(BASE[tienda], url), "json"), url);
  } catch { return resp({ ok: false, msg: `No pudimos leer ese producto en ${tienda}. Revisa el enlace o intenta en un minuto.` }, 502, false); }

  // Buscar la misma referencia en las tiendas: con el modelo si lo hay, si no con el nombre.
  const q = origen.modelo ? `${origen.marca} ${origen.modelo}` : normTexto(origen.nombre).split(" ").slice(0, 6).join(" ");
  const consultas = await Promise.all(TIENDAS.map(async t => {
    try { return { tienda: t.tienda, ok: true, ofertas: t.leer(await traer(t.url(q), "text", 7000)) }; }
    catch { return { tienda: t.tienda, ok: false, ofertas: [] }; } }));
  const ofertas = [origen, ...consultas.flatMap(c => c.ofertas).filter(o => limpio(o.link) !== limpio(origen.link))];
  const grupos = compararOfertas(ofertas);
  const grupo = grupos.find(g => [...g.tiendas, ...g.externas].some(o => limpio(o.link) === limpio(origen.link))) || { tiendas: [], externas: [], similares: [] };
  const historial = await historialDe(origen, u.origin);
  const v = verificar(origen, grupo, historial, new Date(Date.now() - 5 * 3600000).toISOString().slice(0, 10));
  return resp({ ok: true, consultado: new Date().toISOString(), origen, ...v, historial,
    tiendas: grupo.tiendas, externas: grupo.externas.slice(0, 5), similares: grupo.similares || [],
    consultadas: consultas.map(c => ({ tienda: c.tienda, ok: c.ok })) });
};

export const config = { path: "/api/verificar" };
