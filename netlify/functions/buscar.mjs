// Buscador en vivo: GET /api/buscar?q=producto
// Consulta las tiendas en el momento, agrupa el MISMO producto y dice dónde está más barato y si vale la pena.
import { TIENDAS } from "./lib/tiendas.mjs";
import { compararOfertas, normTexto } from "./lib/comparar.mjs";

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36";
const json = (data, status = 200, cache = true) => new Response(JSON.stringify(data), { status, headers: {
  "content-type": "application/json; charset=utf-8",
  "cache-control": "public, max-age=0, must-revalidate",
  // La misma búsqueda se guarda 15 minutos en la CDN de Netlify: ahorra consultas a las tiendas y créditos.
  ...(cache ? { "netlify-cdn-cache-control": "public, durable, s-maxage=900, stale-while-revalidate=300", "netlify-vary": "query=q" } : {}) } });

async function consultar(t, q) {
  const ctrl = new AbortController(), timer = setTimeout(() => ctrl.abort(), 7000);
  try {
    const r = await fetch(t.url(q), { signal: ctrl.signal, headers: { "user-agent": UA, "accept-language": "es-CO,es;q=0.9", accept: "text/html,application/json;q=0.9,*/*;q=0.8" } });
    if (!r.ok && r.status !== 206) throw new Error("HTTP " + r.status);
    return { tienda: t.tienda, ok: true, ofertas: t.leer(await r.text()) };
  } catch (e) {
    return { tienda: t.tienda, ok: false, motivo: e.name === "AbortError" ? "no respondió a tiempo" : "no pudimos consultarla" };
  } finally { clearTimeout(timer); }
}

export default async (req) => {
  const q = (new URL(req.url).searchParams.get("q") || "").trim().slice(0, 80);
  if (q.length < 3) return json({ ok: false, msg: "Escribe al menos 3 letras." }, 400, false);
  const resultados = await Promise.all(TIENDAS.map(t => consultar(t, q)));
  const ofertas = resultados.flatMap(r => r.ofertas || []);
  const palabras = normTexto(q).split(" ").filter(w => w.length > 1);
  const relevancia = p => palabras.filter(w => normTexto(p.nombre).includes(w)).length / (palabras.length || 1);
  const productos = compararOfertas(ofertas)
    // Primero lo que más se parece a lo que escribió la persona; luego lo que está en más tiendas.
    .filter(p => relevancia(p) >= 0.6)
    .sort((a, b) => (relevancia(b) - relevancia(a)) || (b.n - a.n))
    .slice(0, 12);
  return json({ ok: true, q, consultado: new Date().toISOString(),
    tiendas: resultados.map(r => ({ tienda: r.tienda, ok: r.ok, motivo: r.motivo || null, n: (r.ofertas || []).length })), productos });
};

export const config = { path: "/api/buscar" };
