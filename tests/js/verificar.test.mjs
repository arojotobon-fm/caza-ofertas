// Pruebas del Verificador. Correr: node --test tests/js/verificar.test.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { verificar } from "../../netlify/functions/lib/verificar.mjs";
import { leerFichaFalabella } from "../../netlify/functions/lib/producto.mjs";

const of = (tienda, precio, extra = {}) => ({ tienda, precio, propio: true, link: "https://x/" + tienda, nombre: "Freidora Ninja AF141", ...extra });
const grupo = (...t) => ({ tiendas: t });
const HOY = "2026-11-27";

test("información insuficiente: una sola tienda y sin historial → no afirmamos nada", () => {
  const o = of("Falabella", 399900, { precio_antes: 599900 });
  const r = verificar(o, grupo(o), [], HOY);
  assert.equal(r.estado, "insuficiente");
});

test("precio anterior inflado frente al mercado: dos tiendas más lo confirman", () => {
  const o = of("Falabella", 699900, { precio_antes: 1099900 });
  const r = verificar(o, grupo(o, of("Éxito", 699900), of("Jumbo", 719900)), [], HOY);
  assert.equal(r.estado, "precio_inflado");
  assert.ok(r.pruebas.some(p => p.tipo === "antes_mercado"));
});

test("con UNA sola tienda para comparar, el 'antes' alto no basta para '¡Cazamos una mentira!': queda dudoso con la prueba", () => {
  const o = of("Falabella", 699900, { precio_antes: 1099900 });
  const r = verificar(o, grupo(o, of("Éxito", 699900)), [], HOY);
  assert.equal(r.estado, "dudosa");
  assert.ok(r.pruebas.some(p => p.tipo === "antes_mercado"));
});

test("precio anterior inflado según nuestro historial (Black Friday): lo subieron y luego lo 'rebajaron'", () => {
  const o = of("Jumbo", 579900, { precio_antes: 799900 });
  const hist = [["2026-11-17", 579900], ["2026-11-20", 579900], ["2026-11-24", 699900], ["2026-11-26", 699900]].map(([fecha, precio]) => ({ fecha, precio }));
  const r = verificar(o, grupo(o), hist, HOY);
  assert.equal(r.estado, "precio_inflado");
  assert.ok(r.pruebas.some(p => p.tipo === "subida"));
  assert.ok(r.pruebas.some(p => p.tipo === "antes_historial"));
});

test("oferta real: misma referencia más barata que en las otras tiendas, con el tope aprobado", () => {
  const o = of("Olímpica", 2219630, { precio_antes: 2618000 });
  const r = verificar(o, grupo(o, of("Jumbo", 2618000)), [], HOY);
  assert.equal(r.estado, "oferta_real");
});

test("dudosa: anuncian descuento pero cuesta lo mismo en otras tiendas", () => {
  const o = of("Éxito", 399500, { precio_antes: 443900 });
  const r = verificar(o, grupo(o, of("Falabella", 399900)), [], HOY);
  assert.equal(r.estado, "dudosa");
});

test("dudosa: en otra tienda cuesta bastante menos", () => {
  const o = of("Jumbo", 2618000);
  const r = verificar(o, grupo(o, of("Olímpica", 2219630)), [], HOY);
  assert.equal(r.estado, "dudosa");
});

test("con 30 días de historial: si estuvo más barato este mes, no es oferta histórica", () => {
  const o = of("Olímpica", 2219630);
  const hist = Array.from({ length: 31 }, (_, i) => ({ fecha: new Date(Date.parse(HOY) - (31 - i) * 86400000).toISOString().slice(0, 10), precio: i === 10 ? 1999000 : 2219630 }));
  const r = verificar(o, grupo(o, of("Jumbo", 2618000)), hist, HOY);
  assert.equal(r.estado, "dudosa");
  assert.ok(r.pruebas.some(p => p.tipo === "historial" && p.signo === "0"));
});

test("ficha de Falabella: modelo, precio de contado, tarjeta y 'antes'", () => {
  const pd = { name: "Freidora de aire NINJA Pro 4.7 Litros AF141", brandName: "NINJA", attributes: { specifications: [{ name: "Modelo", value: "AF141" }, { name: "Condicion del producto", value: "Nuevo" }] },
    variants: [{ offerings: [{ sellerId: "FALABELLA_COLOMBIA", sellerName: "FALABELLA" }], medias: [], prices: [
      { type: "cmrPrice", price: ["369.900"] }, { type: "internetPrice", price: ["399.900"] }, { type: "normalPrice", price: ["599.900"], crossed: true }] }] };
  const o = leerFichaFalabella(`<script id="__NEXT_DATA__" type="application/json">${JSON.stringify({ props: { pageProps: { productData: pd } } })}</script>`, "https://www.falabella.com.co/falabella-co/product/73646009/x?y=1");
  assert.deepEqual([o.modelo, o.precio, o.precio_tarjeta, o.precio_antes, o.propio, o.link], ["AF141", 399900, 369900, 599900, true, "https://www.falabella.com.co/falabella-co/product/73646009/x"]);
});

test("falso positivo real del 22 nov: Remington D5000 empata con Falabella → no es oferta real", () => {
  const o = of("Jumbo", 109900, { precio_antes: 169900 });
  const r = verificar(o, grupo(o, of("Falabella", 109900), of("Olímpica", 169900)), [], HOY);
  assert.notEqual(r.estado, "oferta_real");
  assert.equal(r.estado, "dudosa");
});

test("más barato pero con un 'antes' sin respaldo: no es '¡Oferta real!', es dudoso", () => {
  const o = of("Olímpica", 2219630, { precio_antes: 3999000 });
  const r = verificar(o, grupo(o, of("Jumbo", 2618000)), [], HOY);
  assert.equal(r.estado, "dudosa");
  assert.ok(r.pruebas.some(p => p.tipo === "antes_respaldo" && p.signo === "0"));
});

test("¡Oferta real! con evidencia: más barato y el 'antes' lo cobra otra tienda hoy", () => {
  const o = of("Olímpica", 2219630, { precio_antes: 2618000 });
  const r = verificar(o, grupo(o, of("Jumbo", 2618000)), [], HOY);
  assert.equal(r.estado, "oferta_real");
  assert.ok(r.pruebas.some(p => p.tipo === "antes_respaldo" && p.signo === "+"));
});
