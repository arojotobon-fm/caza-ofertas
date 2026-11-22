// Pruebas del buscador en vivo con respuestas reales de las tiendas (capturadas el 22 nov 2026, recortadas).
// Correr: node --test tests/js/buscar.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { leerVtex, leerFalabella } from "../../netlify/functions/lib/tiendas.mjs";
import { compararOfertas, codigosModelo, valeLaPena } from "../../netlify/functions/lib/comparar.mjs";

const vtex = (nombre, marca, linkText, precio, antes, sellerId, sellerName, ean) => ({ productName: nombre, brand: marca, link: "https://x.co/" + linkText + "/p",
  items: [{ ean, images: [], sellers: [{ sellerId, sellerName, commertialOffer: { Price: precio, ListPrice: antes || precio, AvailableQuantity: 5 } }] }] });
const fala = (displayName, brand, url, sellerId, sellerName, prices) =>
  ({ displayName, brand, url, sellerId, sellerName, mediaUrls: [], prices: prices.map(([type, price, crossed]) => ({ type, price: [price], crossed: !!crossed })) });
const html = results => `<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ props: { pageProps: { results } } })}</script>`;

const EXITO = leerVtex("Éxito", "https://www.exito.com", [
  vtex("Freidora De Aire NINJA 7.6LT Digital Negro DZ201", "NINJA", "freidora-aire-doble-76-lt-ninja-dz201-3089542", 699900, 799900, "1", "exito", "0622356320603"),
  vtex("Freidora De Aire NINJA 4.7 L Digital NEGRO AF141", "NINJA", "freidora-de-aire-ninja-47-l-digital-negro-af141-3241073", 399500, 443900, "1", "exito", "0622356309844"),
  vtex("Apple Airpods Pro 3", "APPLE", "apple-airpods-pro-3-104868628-mp", 858785, 1502902, "17306", "magic marketplace", "0195950543742"),
]);
const FALABELLA = leerFalabella("Falabella", html([
  fala("Freidora de Aire Doble Canasta 7.6 Lt Air Fryer DZ201", "NINJA", "https://www.falabella.com.co/falabella-co/product/73719063/freid-aire-doble-cesta-dz201laa", "FALABELLA_COLOMBIA", "Falabella", [["internetPrice", "699.900"], ["normalPrice", "1.099.900", true]]),
  fala("Freidora de aire Pro 4.7 Litros AF141", "NINJA", "https://www.falabella.com.co/falabella-co/product/73646009/freidora-aire-pro4en1-af141laa", "FALABELLA_COLOMBIA", "Falabella", [["cmrPrice", "369.900"], ["internetPrice", "399.900"], ["normalPrice", "599.900", true]]),
  fala("Freidora Profesional Crispi Vidrio 3.78 L", "NINJA", "https://www.falabella.com.co/falabella-co/product/152145474/freidora-profesional-ninja-crispi", "SC1", "Jesucristo Electro", [["internetPrice", "889.900"], ["normalPrice", "1.799.900", true]]),
]));
const OLIMPICA = leerVtex("Olímpica", "https://www.olimpica.com", [
  vtex("Computador Portátil Lenovo Slim 3 15,6 Pulgadas AMD Ryzen 5 512 GB SSD 8 GB RAM", "Lenovo", "portatil-lenovo-slim3-ryzen-5-8g-512g-15-pulgadas", 2099400, 3499000, "1", "Olimpica", "196804839998"),
]);
const JUMBO = leerVtex("Jumbo", "https://www.jumbocolombia.com", [
  vtex("Computador Portátil Lenovo Ideapad Slim3 15AMN8 - AMD Ryzen 5 7520U - RAM 8GB - 512GB SSD - Gris - 15,6\"", "LENOVO", "computador-portatil-lenovo-ideapad-slim3-15amn8-3592322", 2099900, 4199000, "1", "Cencosud - Colombia", "196804839998"),
  vtex("Freidora de Aire Ninja Crispi 4 En 1 FN101GY LAA", "NINJA", "freidora-de-aire-ninja-crispi-4-en-1-fn101gy-laa-455344", 579900, 799900, "1", "Cencosud - Colombia", "622356356121"),
]);
const TODAS = [...EXITO, ...FALABELLA, ...OLIMPICA, ...JUMBO];
const buscar = cod => compararOfertas(TODAS).find(p => p.tiendas.some(t => t.nombre.toUpperCase().includes(cod)));

test("lectores: tienda propia vs terceros y precio con tarjeta aparte", () => {
  assert.equal(EXITO.find(o => o.nombre.includes("Airpods")).propio, false);
  const af = FALABELLA.find(o => o.nombre.includes("AF141"));
  assert.deepEqual([af.precio, af.precio_tarjeta, af.precio_antes, af.propio], [399900, 369900, 599900, true]);
  assert.equal(JUMBO[0].propio, true);
  assert.equal(JUMBO[0].ean, "196804839998");
});

test("código de modelo: quita el sufijo de región LAA", () => {
  assert.ok(codigosModelo("freid aire doble cesta dz201laa").has("DZ201"));
  assert.ok(codigosModelo("Freidora Crispi FN101GY LAA").has("FN101GY"));
});

test("mismo producto por código entre Éxito y Falabella (DZ201): mismo precio, 'antes' inflado en Falabella", () => {
  const p = buscar("DZ201");
  assert.deepEqual(p.tiendas.map(t => t.tienda).sort(), ["Falabella", "Éxito"]);
  assert.equal(p.veredicto, "igual");
  assert.equal(p.antesInflado[0].tienda, "Falabella");   // dice 'antes $1.099.900' y nadie lo cobra así hoy
});

test("mismo producto por código de barras entre Olímpica y Jumbo (Lenovo 15AMN8): diferencia irrisoria", () => {
  const p = buscar("LENOVO");
  assert.equal(p.n, 2);
  assert.equal(p.ahorro, 500);
  assert.equal(p.veredicto, "casi_igual");
});

test("AF141: $400 de diferencia no es 'más barato'; el precio con tarjeta no entra", () => {
  const p = buscar("AF141");
  assert.equal(p.ganador, "Éxito");
  assert.equal(p.veredicto, "casi_igual");
});

test("los terceros del marketplace se muestran aparte y no definen el veredicto", () => {
  const p = compararOfertas(TODAS).find(x => /airpods/i.test(x.nombre));
  assert.equal(p.n, 0);
  assert.equal(p.veredicto, "solo_terceros");
});

test("tope de ahorro aprobado", () => {
  assert.equal(valeLaPena(9999, 50), false);
  assert.equal(valeLaPena(15000, 6), true);
  assert.equal(valeLaPena(30000, 2), true);
  assert.equal(valeLaPena(15000, 3), false);
});

test("no une productos con códigos de barras distintos aunque Falabella (sin código de barras) parezca el puente", () => {
  const extra = leerVtex("Jumbo", "https://www.jumbocolombia.com", [
    vtex("Freidora De Aire NINJA 3.8 L Digital Gris FN101GY", "NINJA", "fn101gy-a", 579900, null, "1", "Cencosud - Colombia", "622356356121")]);
  const otra = leerVtex("Éxito", "https://www.exito.com", [
    vtex("Freidora De Aire NINJA 3.8 L Digital Gris FN101GY", "NINJA", "fn101gy-b", 579900, null, "1", "exito", "0622356654944")]);
  const puente = leerFalabella("Falabella", html([fala("Crispi Freidora 4 en 1", "NINJA", "https://www.falabella.com.co/x/73687168/freid-aire-crispi-fn101laagy", "FALABELLA_COLOMBIA", "Falabella", [["internetPrice", "579.900"]])]));
  const grupos = compararOfertas([...extra, ...otra, ...puente]);
  assert.ok(grupos.every(g => new Set(g.tiendas.map(t => t.ean).filter(Boolean)).size <= 1));
});
