// Lectores de las tiendas para el buscador en vivo. Cada uno devuelve ofertas normalizadas:
// { tienda, nombre, marca, link, img, precio (contado), precio_tarjeta, precio_antes, vendedor, propio }
// "propio" = lo vende la tienda misma (no un tercero del marketplace).

const num = v => { const n = Number(String(v ?? "").replace(/[^\d]/g, "")); return Number.isFinite(n) ? n : 0; };

export function leerVtex(tienda, base, json) {
  const out = [];
  for (const p of json || []) {
    const it = (p.items || [])[0]; if (!it) continue;
    for (const s of it.sellers || []) {
      const co = s.commertialOffer || {};
      if (!(co.Price > 0) || !(co.AvailableQuantity > 0)) continue;
      out.push({ tienda, nombre: p.productName, marca: p.brand, link: p.link || (base + "/" + p.linkText + "/p"),
        img: (it.images || [])[0]?.imageUrl || "", precio: Math.round(co.Price), precio_tarjeta: null,
        precio_antes: co.ListPrice > co.Price ? Math.round(co.ListPrice) : null, vendedor: s.sellerName, propio: String(s.sellerId) === "1", ean: it.ean ? String(it.ean).replace(/^0+/, "") : null });
    }
  }
  return out;
}

export function leerFalabella(tienda, html) {
  const m = String(html).match(/<script id="__NEXT_DATA__" type="application\/json"[^>]*>([\s\S]*?)<\/script>/);
  if (!m) throw new Error("sin __NEXT_DATA__");
  const res = JSON.parse(m[1])?.props?.pageProps?.results || [];
  return res.map(p => {
    const pr = Object.fromEntries((p.prices || []).map(x => [x.type, num((x.price || [])[0])]));
    const contado = pr.internetPrice || pr.eventPrice || (!(p.prices || []).find(x => x.type === "normalPrice")?.crossed ? pr.normalPrice : 0);
    return { tienda, nombre: p.displayName, marca: p.brand, link: p.url, img: (p.mediaUrls || [])[0] || "",
      precio: contado, precio_tarjeta: pr.cmrPrice || null, precio_antes: pr.normalPrice && pr.normalPrice > contado ? pr.normalPrice : null,
      vendedor: p.sellerName, propio: /^falabella/i.test(p.sellerId || "") || /^falabella$/i.test(p.sellerName || "") };
  }).filter(o => o.precio > 0);
}

const VTEX = (tienda, base) => ({ tienda, url: q => `${base}/api/catalog_system/pub/products/search?ft=${encodeURIComponent(q)}&_from=0&_to=29`,
  leer: (txt) => leerVtex(tienda, base, JSON.parse(txt)) });
export const TIENDAS = [
  VTEX("Éxito", "https://www.exito.com"),
  VTEX("Olímpica", "https://www.olimpica.com"),
  VTEX("Jumbo", "https://www.jumbocolombia.com"),
  { tienda: "Falabella", url: q => `https://www.falabella.com.co/falabella-co/search?Ntt=${encodeURIComponent(q)}`, leer: txt => leerFalabella("Falabella", txt) },
];
