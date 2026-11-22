// Reportes de la comunidad: "sigue vigente" / "ya no está".
// GET  /api/reportes  -> resumen de reportes de las últimas 72 h
// POST /api/reportes  -> { id, voto: "si" | "no", precio? }
import { getStore } from "@netlify/blobs";

const WINDOW = 72 * 3600e3;   // se guardan 72 horas
const COOLDOWN = 6 * 3600e3;  // una persona = un reporte por producto cada 6 horas

async function sha(text) {
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map(b => b.toString(16).padStart(2, "0")).join("").slice(0, 16);
}
const json = (data, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

export default async (req, context) => {
  const store = getStore({ name: "reportes", consistency: "strong" });

  if (req.method === "GET") {
    return json((await store.get("summary", { type: "json" })) || {});
  }
  if (req.method !== "POST") return json({ ok: false }, 405);

  let body;
  try { body = await req.json(); } catch { return json({ ok: false }, 400); }
  const id = String(body.id || "");
  const voto = body.voto === "si" ? "si" : body.voto === "no" ? "no" : null;
  if (!/^[a-f0-9]{12}$/.test(id) || !voto) return json({ ok: false }, 400);
  const p = Number(body.precio);
  const precio = Number.isFinite(p) && p >= 1000 && p <= 100000000 ? Math.round(p) : null;

  // No guardamos la IP: solo una huella irreversible para evitar reportes repetidos.
  const ip = context.ip || req.headers.get("x-nf-client-connection-ip") || "anon";
  const h = await sha(ip + "|" + id + "|" + (process.env.REPORT_SALT || "caza-ofertas"));

  const now = Date.now();
  const key = "p_" + id;
  const rec = (await store.get(key, { type: "json" })) || { votes: [] };
  rec.votes = rec.votes.filter(v => now - v.t < WINDOW);
  if (rec.votes.some(v => v.h === h && now - v.t < COOLDOWN)) {
    return json({ ok: false, msg: "Ya reportaste este producto hace poco. ¡Gracias!" }, 429);
  }
  rec.votes.push({ t: now, v: voto, p: precio, h });
  await store.setJSON(key, rec);

  const summary = (await store.get("summary", { type: "json" })) || {};
  for (const k of Object.keys(summary)) {
    summary[k].si = (summary[k].si || []).filter(t => now - t < WINDOW);
    summary[k].no = (summary[k].no || []).filter(x => now - x[0] < WINDOW);
    if (!summary[k].si.length && !summary[k].no.length) delete summary[k];
  }
  summary[id] = {
    si: rec.votes.filter(v => v.v === "si").map(v => v.t),
    no: rec.votes.filter(v => v.v === "no").map(v => [v.t, v.p]),
  };
  await store.setJSON("summary", summary);
  return json({ ok: true });
};

export const config = { path: "/api/reportes" };
