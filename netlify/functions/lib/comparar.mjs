// Comparador para el buscador en vivo. Es el mismo criterio de scripts/normalizar.py y scripts/comparador.py:
// solo se agrupa la MISMA marca con el MISMO código de modelo y sin especificaciones en conflicto.
// Este archivo no usa nada de Node: también se puede probar pegándolo en la consola del navegador.

const ALIAS = { "BLACK+DECKER": "BLACK+DECKER", "BLACK & DECKER": "BLACK+DECKER", "BLACK&DECKER": "BLACK+DECKER",
  "BLACK AND DECKER": "BLACK+DECKER", "SAMSUNG ELECTRONICS": "SAMSUNG", "LG ELECTRONICS": "LG", "APPLE INC": "APPLE",
  "XIAOMI MI": "XIAOMI", "REDMI": "XIAOMI" };
const MARCAS = ["SAMSUNG","LG","SONY","XIAOMI","HUAWEI","APPLE","MOTOROLA","LENOVO","HP","ASUS","ACER","DELL","TCL","HISENSE",
  "KALLEY","CHALLENGER","PANASONIC","PHILIPS","OSTER","NINJA","IMUSA","HOLSTEIN","BLACK+DECKER","ELECTROLUX","WHIRLPOOL","MABE",
  "HACEB","SAMURAI","UMCO","INSTANT","CUISINART","JBL","SOUNDCORE","ANKER","BOSE","AMAZFIT","GARMIN","REMINGTON","CONAIR","GAMA",
  "BABYLISS","NINTENDO","PLAYSTATION","XBOX","MICROSOFT","ROBOROCK","IROBOT","DREAME","ECOVACS","NESPRESSO","TOSHIBA","HONOR",
  "OPPO","REALME","VIVO","ZTE","INFINIX","TECNO","NIKE","ADIDAS","PUMA"].sort((a, b) => b.length - a.length);
const COLORES = new Set("NEGRO NEGRA BLANCO BLANCA GRIS PLATEADO PLATEADA AZUL ROJO ROJA VERDE ROSADO ROSADA MORADO MORADA LILA DORADO DORADA CREMA BEIGE AMARILLO VIOLETA GRAFITO TITANIO NARANJA CAFE INOX ACERO".split(" "));

export const normTexto = s => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/[^\x00-\x7F]/g, "").toUpperCase().replace(/\s+/g, " ").trim();
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

export function marcaCanonica(campo, nombre) {
  const b = normTexto(campo), n = normTexto(nombre);
  if (b) for (const [a, c] of Object.entries(ALIAS)) if (b === a || b.startsWith(a + " ")) return c;
  for (const [a, c] of Object.entries(ALIAS)) if (n.includes(a)) return c;
  if (b && MARCAS.includes(b.split(" ")[0])) return b.split(" ")[0];
  for (const k of MARCAS) if (new RegExp("(?<![A-Z0-9])" + esc(k) + "(?![A-Z0-9])").test(n)) return k;
  return b ? b.split(" ")[0] : "";
}

const UNIDAD = /^\d+(\.\d+)?(L|LT|LTS|LITROS|GB|TB|W|WATTS|MAH|HZ|MP|PULGADAS|PULG|CM|MM|ML|OZ|V|K|P|G|PCS|PZ|PIEZAS|X\d+)$/;
const GENERICO = /^(RTX|GTX|RAM|SSD|HDD|DDR|LPDDR|USB|IP|IPS|BT|WIFI|HDMI|QLED|OLED|UHD|FHD|LED|CORE|RYZEN|SERIE|SERIES|GEN|ANC|TWS|NFC|AMOLED|SLIM|PRO|MAX|PLUS|ULTRA|LITE|MINI|AIR|EDGE|NOTE|FE|BUDS|WATCH|PS|SWITCH)\d*[A-Z]?$/;
const CPU = /^(I[3579]\d{3,5}[A-Z]*|\d{3,5}(U|H|HS|HX|K|KF|G|P)|N\d{3,4}|R[3579]\d{4}[A-Z]*|M[1-4](PRO|MAX)?|SNAPDRAGON\d*|HELIO[A-Z]?\d+|DIMENSITY\d+)$/;

export function codigosModelo(nombre) {
  const out = new Set();
  for (const tok of normTexto(nombre).match(/[A-Z0-9][A-Z0-9\-/.]{2,}/g) || []) {
    const t = tok.replace(/[-/.]/g, "");
    if (t.length < 4 || !/\d/.test(t) || !/[A-Z]/.test(t)) continue;
    if (UNIDAD.test(tok) || UNIDAD.test(t) || GENERICO.test(t) || CPU.test(t)) continue;
    // Sufijo de región del fabricante (DZ201LAA = DZ201 para Latinoamérica): se quita para comparar entre tiendas.
    out.add(t.replace(/(?<=\d)(LAA|LAX)/, ""));
  }
  return out;
}

export function especificaciones(nombre) {
  const n = normTexto(nombre), sp = {};
  let m = n.match(/(\d{2,3})(?:[.,](\d))?\s*("|''|PULGADAS|PULG\b|IN\b)/); if (m) sp.pantalla_pulgadas = parseFloat(m[1] + "." + (m[2] || 0));
  // Procesador: Intel y AMD nunca son el mismo producto.
  if (/\bINTEL\b|\bCORE\s*(I[3579]|[3579]|ULTRA)\b|\bCELERON\b|\bPENTIUM\b/.test(n)) sp.cpu = "INTEL";
  else if (/\bRYZEN\b|\bAMD\b|\bATHLON\b/.test(n)) sp.cpu = "AMD";
  else if (/\bSNAPDRAGON\b/.test(n)) sp.cpu = "QUALCOMM";
  m = n.match(/(\d{1,2})\s*GB\s*(DE\s*)?RAM|RAM\s*(DE\s*)?(\d{1,2})\s*GB/); if (m) sp.ram_gb = +(m[1] || m[4]);
  m = n.match(/(\d+(?:[.,]\d+)?)\s*TB\b/);
  if (m) sp.almacenamiento_gb = Math.round(parseFloat(m[1].replace(",", ".")) * 1024);
  else for (const g of n.matchAll(/(\d{2,4})\s*GB\b/g)) { const v = +g[1]; if (v >= 32 && v !== sp.ram_gb) { sp.almacenamiento_gb = v; break; } }
  m = n.match(/(\d+(?:[.,]\d+)?)\s*(L|LT|LTS|LITROS)\b/); if (m) sp.capacidad_l = parseFloat(m[1].replace(",", "."));
  if (/\+\s*(BARRA|AUDIF|PARLANTE|SOPORTE|BASE|MOUSE|TECLADO|MALETA|FORRO|VASO|CARGADOR|ESTUCHE)|\bCOMBO\b|\bKIT\b/.test(n)) sp.es_combo = true;
  if (/REACONDICIONAD|REPOTENCIAD|OPEN ?BOX|\bUSADO\b|EXHIBICION/.test(n)) sp.condicion_producto = "no_nuevo";
  return sp;
}
const ESTRICTAS = ["pantalla_pulgadas", "ram_gb", "almacenamiento_gb", "capacidad_l", "es_combo", "condicion_producto", "cpu"];

export function mismoProducto(a, b) {
  // Código de barras (EAN) igual = mismo producto, aunque una tienda no diga la marca (p. ej. Flamingo);
  // distinto = otra referencia o color. Sin EAN, se exige la misma marca y el mismo código de modelo.
  const eanIgual = a.ean && b.ean && a.ean === b.ean;
  if (a.ean && b.ean && !eanIgual) return false;
  if (!eanIgual && (!a.marca || a.marca !== b.marca)) return false;
  if (!eanIgual && ![...a.codigos].some(c => b.codigos.has(c))) return false;
  for (const k of ESTRICTAS) {
    const va = a.specs[k], vb = b.specs[k];
    if (va == null && vb == null) continue;
    if (va == null || vb == null) { if (k === "es_combo" || k === "condicion_producto") return false; continue; }
    if (va !== vb) return false;
  }
  return true;
}

// Tope de ahorro aprobado (22 nov 2026): al menos $10.000 y además 5 % o $20.000.
export const valeLaPena = (ahorro, pct) => ahorro >= 10000 && (pct >= 5 || ahorro >= 20000);
const mediana = a => { const s = [...a].sort((x, y) => x - y), m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };
// Alkosto, Ktronix y Alkomprar son un solo grupo; Falabella y Homecenter también.
export const GRUPO = { Alkosto: "corbeta", Ktronix: "corbeta", Alkomprar: "corbeta", Falabella: "falabella", Homecenter: "falabella" };
const grupo = t => GRUPO[t] || t;

/** Agrupa las ofertas de varias tiendas en productos y saca el veredicto de cada uno. */
export function compararOfertas(ofertas) {
  // El código de modelo se busca en el nombre y en el enlace (Falabella suele ponerlo solo en el enlace: ...-dz201laa).
  const slug = l => String(l || "").split("?")[0].split("/").filter(Boolean).slice(-2).join(" ").replace(/-/g, " ");
  const pubs = ofertas.map(o => ({ ...o, marca: marcaCanonica(o.marca, o.nombre), codigos: codigosModelo(o.nombre + " " + slug(o.link) + " " + (o.modelo || "")), specs: especificaciones(o.nombre) }));
  const padre = pubs.map((_, i) => i), raiz = i => (padre[i] === i ? i : (padre[i] = raiz(padre[i])));
  // Cada grupo guarda sus códigos de barras: nunca se unen dos grupos con códigos de barras distintos,
  // aunque una publicación sin código de barras (p. ej. Falabella) parezca el puente entre ellos.
  const eans = pubs.map(p => new Set(p.ean ? [p.ean] : []));
  // Una publicación sin código de barras que coincide con dos códigos de barras distintos es ambigua: queda sola.
  const ambigua = pubs.map((p, i) => !p.ean && new Set(pubs.filter((q, j) => j !== i && q.ean && mismoProducto(p, q)).map(q => q.ean)).size > 1);
  for (let i = 0; i < pubs.length; i++) for (let j = i + 1; j < pubs.length; j++) {
    if (!((pubs[i].codigos.size || pubs[i].ean) && mismoProducto(pubs[i], pubs[j]))) continue;
    if (ambigua[i] || ambigua[j]) continue;
    const ri = raiz(i), rj = raiz(j);
    if (ri === rj) continue;
    const u = new Set([...eans[ri], ...eans[rj]]);
    if (u.size > 1) continue;
    padre[ri] = rj; eans[rj] = u;
  }
  const grupos = {};
  pubs.forEach((p, i) => (grupos[raiz(i)] ||= []).push(p));

  const productos = Object.values(grupos).map(items => {
    const propias = items.filter(o => o.propio && o.precio > 0);
    const externas = items.filter(o => !o.propio && o.precio > 0).sort((a, b) => a.precio - b.precio);
    const mejor = {};   // mejor precio de contado por grupo empresarial (solo la tienda, no terceros)
    propias.forEach(o => { const g = grupo(o.tienda); if (!mejor[g] || o.precio < mejor[g].precio) mejor[g] = o; });
    const tiendas = Object.values(mejor).sort((a, b) => a.precio - b.precio);
    const base = tiendas[0] || externas[0];
    const r = { nombre: base.nombre, marca: base.marca, img: (tiendas.find(t => t.img) || base).img || "", codigo: [...base.codigos][0] || "",
      tiendas, externas, n: tiendas.length };
    if (tiendas.length >= 2) {
      // Contra la SEGUNDA más barata, no contra el promedio: un empate en el primer lugar no es "más barato".
      const barato = tiendas[0], ref = tiendas[1].precio;
      const ahorro = ref - barato.precio, pct = ahorro / ref * 100;
      r.ganador = barato.tienda; r.ahorro = ahorro; r.pct = Math.round(pct * 10) / 10;
      r.veredicto = ahorro <= 0 ? "igual" : valeLaPena(ahorro, pct) ? "mas_barato" : "casi_igual";
    } else r.veredicto = tiendas.length === 1 ? "una_tienda" : "solo_terceros";
    // "Antes" inflado: la tienda dice que antes costaba mucho más de lo que lo cobra cualquier otra tienda hoy.
    const maxHoy = Math.max(...tiendas.map(t => t.precio));
    r.antesInflado = tiendas.length >= 2 ? tiendas.filter(t => t.precio_antes && t.precio_antes > maxHoy * 1.15)
      .map(t => ({ tienda: t.tienda, antes: t.precio_antes, descuentoAnunciado: Math.round((1 - t.precio / t.precio_antes) * 100) })) : [];
    r._specs = base.specs; r._palabras = palabras(base.nombre);
    return r;
  });
  // Parecidos: misma marca y nombre muy parecido, pero NO confirmados como la misma referencia.
  // Se muestran aparte, sin veredicto, con las diferencias que se alcanzan a ver, para que la persona revise.
  for (const p of productos) {
    p.similares = productos.filter(q => q !== p && q.tiendas.length && q.marca === p.marca &&
        !q.tiendas.some(t => p.tiendas.some(u => u.tienda === t.tienda && u.link === t.link)) && parecido(p._palabras, q._palabras) >= 0.5)
      .slice(0, 3).map(q => ({ nombre: q.nombre, tienda: q.tiendas[0].tienda, precio: q.tiendas[0].precio, link: q.tiendas[0].link, diferencias: diferencias(p._specs, q._specs) }));
  }
  productos.forEach(p => { delete p._specs; delete p._palabras; });
  return productos;
}

// Para "parecido" solo cuentan las palabras del nombre comercial (IDEAPAD, SLIM, CRISPI…), no las especificaciones ni la marca.
const VACIAS = new Set(("DE LA EL Y CON PARA EN SIN LOS LAS UN UNA COMPUTADOR PORTATIL PANTALLA PULGADAS RAM SSD HDD INTEL CORE AMD RYZEN " +
  "WINDOWS NEGRO NEGRA BLANCO BLANCA GRIS AZUL ROJO VERDE PLATEADO DIGITAL LITROS ALMACENAMIENTO TACTIL TOUCH " + MARCAS.join(" ")).split(" "));
const palabras = n => new Set(normTexto(n).split(/[^A-Z0-9]+/).filter(w => w.length > 2 && !/\d/.test(w) && !VACIAS.has(w)));
const parecido = (a, b) => { const i = [...a].filter(w => b.has(w)).length; return i < 2 ? 0 : i / Math.min(a.size, b.size); };
const NOMBRE_SPEC = { pantalla_pulgadas: ["pantalla", v => String(v).replace(".", ",") + '"'], ram_gb: ["RAM", v => v + " GB"],
  almacenamiento_gb: ["almacenamiento", v => v + " GB"], capacidad_l: ["capacidad", v => String(v).replace(".", ",") + " L"], cpu: ["procesador", v => v === "INTEL" ? "Intel" : v === "AMD" ? "AMD" : v] };
function diferencias(a, b) {
  return Object.entries(NOMBRE_SPEC).filter(([k]) => a[k] != null && b[k] != null && a[k] !== b[k])
    .map(([k, [nom, f]]) => `${nom}: ${f(a[k])} vs ${f(b[k])}`);
}
