// Lee UN producto a partir de su enlace (Falabella, Olímpica, Jumbo). Éxito bloquea las consultas desde el servidor.
import { leerVtex } from "./tiendas.mjs";
const num = v => Number(String(v ?? "").replace(/[^\d]/g, "")) || 0;

export const TIENDA_POR_HOST = { "www.falabella.com.co": "Falabella", "www.olimpica.com": "Olímpica", "www.jumbocolombia.com": "Jumbo",
  "www.exito.com": "Éxito", "tienda.exito.com": "Éxito", "www.alkosto.com": "Alkosto", "www.ktronix.com": "Ktronix", "www.homecenter.com.co": "Homecenter", "www.flamingo.com.co": "Flamingo", "flamingo.com.co": "Flamingo" };
export const SE_PUEDE_LEER = new Set(["Falabella", "Olímpica", "Jumbo", "Flamingo"]);

export function leerFichaFalabella(html, url) {
  const m = String(html).match(/<script id="__NEXT_DATA__" type="application\/json"[^>]*>([\s\S]*?)<\/script>/);
  if (!m) throw new Error("sin __NEXT_DATA__");
  const pd = JSON.parse(m[1])?.props?.pageProps?.productData; if (!pd) throw new Error("sin productData");
  const v = (pd.variants || [])[0] || {}, of = (v.offerings || [])[0] || {};
  const pr = Object.fromEntries((v.prices || []).map(x => [x.type, num((x.price || [])[0])]));
  const precio = pr.internetPrice || pr.eventPrice || pr.normalPrice;
  const attrs = Object.fromEntries(((pd.attributes || {}).specifications || []).map(a => [a.name, a.value]));
  return { tienda: "Falabella", nombre: pd.name, marca: pd.brandName, modelo: attrs["Modelo"] || "", link: url.split("?")[0],
    img: (v.medias || [])[0]?.url || "", precio, precio_tarjeta: pr.cmrPrice || null,
    precio_antes: pr.normalPrice && pr.normalPrice > precio ? pr.normalPrice : null,
    vendedor: of.sellerName || "", propio: /^falabella/i.test(of.sellerId || "") || /^falabella$/i.test(of.sellerName || ""),
    condicion: attrs["Condicion del producto"] || "" };
}

export function leerFichaVtex(tienda, base, json, url) {
  const p = (json || [])[0]; if (!p) throw new Error("producto no encontrado");
  const ofertas = leerVtex(tienda, base, [p]);
  const o = ofertas.find(x => x.propio) || ofertas.sort((a, b) => a.precio - b.precio)[0];
  if (!o) throw new Error("sin precio disponible");
  // productReference a veces es un código interno de la tienda (solo números): ahí no sirve como modelo.
  const ref = String(p.productReference || "");
  return { ...o, modelo: /[a-z]/i.test(ref) && /\d/.test(ref) ? ref : "", link: url.split("?")[0] };
}

export function urlFichaVtex(base, url) {
  const slug = new URL(url).pathname.replace(/^\/+|\/p\/?$/g, "");
  return `${base}/api/catalog_system/pub/products/search/${slug}/p`;
}
