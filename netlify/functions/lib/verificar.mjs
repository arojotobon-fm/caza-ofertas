// Verificador: dice si una oferta es real, dudosa, si el precio anterior está inflado o si no hay información suficiente.
// Regla del proyecto: sin evidencia suficiente NO se afirma nada; se dice "información insuficiente".
import { valeLaPena } from "./comparar.mjs";

const DIA = 86400000;
const cop = n => "$" + Math.round(n).toLocaleString("es-CO");
const mediana = a => { const s = [...a].sort((x, y) => x - y), m = Math.floor(s.length / 2); return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; };

/** historial: [{fecha:"2026-11-20", precio, antes?}] de la misma publicación, ordenado o no. hoy: "YYYY-MM-DD". */
export function verificar(origen, grupo, historial = [], hoy = new Date().toISOString().slice(0, 10)) {
  const pruebas = [];   // {tipo, signo: "+"|"-"|"0", texto}
  const otras = (grupo?.tiendas || []).filter(t => t.tienda !== origen.tienda);
  const hist = historial.filter(h => h.fecha < hoy && h.precio > 0).sort((a, b) => a.fecha.localeCompare(b.fecha));
  const diasHist = hist.length ? Math.round((Date.parse(hoy) - Date.parse(hist[0].fecha)) / DIA) : 0;
  let inflado = false, senalDebil = false;

  // 1. ¿Inflaron el precio? (a) contra el mercado de hoy
  if (origen.precio_antes && otras.length) {
    const maxOtras = Math.max(...otras.map(t => t.precio));
    if (origen.precio_antes > maxOtras * 1.15) {
      // Para "¡Cazamos una mentira!" basta con el mercado solo si al menos DOS tiendas más lo confirman.
      // Con una sola tienda la señal es débil: queda como prueba y el veredicto baja a "dudoso".
      if (otras.length >= 2) inflado = true; else senalDebil = true;
      pruebas.push({ tipo: "antes_mercado", signo: "-", texto: `${origen.tienda} dice que antes costaba ${cop(origen.precio_antes)}, pero hoy ninguna de las otras tiendas que consultamos lo cobra a ese precio (la más cara lo tiene en ${cop(maxOtras)}).` });
    }
  }
  // (b) contra nuestro propio historial
  if (origen.precio_antes && diasHist >= 7) {
    const ult30 = hist.filter(h => Date.parse(hoy) - Date.parse(h.fecha) <= 30 * DIA);
    const maxHist = Math.max(...ult30.map(h => h.precio));
    if (origen.precio_antes > maxHist * 1.05) {
      inflado = true;
      pruebas.push({ tipo: "antes_historial", signo: "-", texto: `En los últimos ${Math.min(diasHist, 30)} días nunca lo vimos a ${cop(origen.precio_antes)} en ${origen.tienda}: el precio más alto que registramos fue ${cop(maxHist)}.` });
    }
  }
  // (c) subida justo antes del "descuento"
  if (diasHist >= 3) {
    const ult14 = hist.filter(h => Date.parse(hoy) - Date.parse(h.fecha) <= 14 * DIA);
    const min14 = Math.min(...ult14.map(h => h.precio)), max14 = Math.max(...ult14.map(h => h.precio));
    const subida = ult14.find(h => h.precio === max14);
    if (max14 > min14 * 1.1 && origen.precio >= min14 * 0.99 && origen.precio_antes) {
      inflado = true;
      pruebas.push({ tipo: "subida", signo: "-", texto: `El ${subida.fecha} lo subieron a ${cop(max14)}; antes estaba en ${cop(min14)}. El "descuento" de hoy lo deja en ${cop(origen.precio)}, prácticamente donde ya estaba.` });
    }
  }

  // 2. ¿Está realmente más barato? (misma referencia en otras tiendas)
  let comparacion = "sin_datos";
  if (otras.length) {
    // "Más barato" es contra la tienda MÁS BARATA de las otras, no contra el promedio:
    // si otra tienda tiene el mismo precio, no hay ahorro (falso positivo real del 22 nov: Remington D5000).
    const masBarata = otras.reduce((a, b) => (b.precio < a.precio ? b : a));
    const ref = masBarata.precio, ahorro = ref - origen.precio, pct = ahorro / ref * 100;
    if (valeLaPena(ahorro, pct)) { comparacion = "mas_barato"; pruebas.push({ tipo: "comparacion", signo: "+", texto: `Es ${cop(ahorro)} (${pct.toFixed(1).replace(".", ",")} %) más barato que en la siguiente tienda más barata (${masBarata.tienda}, ${cop(ref)}), con la misma referencia.` }); }
    else if (valeLaPena(origen.precio - masBarata.precio, (origen.precio - masBarata.precio) / origen.precio * 100)) { comparacion = "mas_caro"; pruebas.push({ tipo: "comparacion", signo: "-", texto: `En ${masBarata.tienda} cuesta ${cop(masBarata.precio)}: ${cop(origen.precio - masBarata.precio)} menos.` }); }
    else { comparacion = "igual"; pruebas.push({ tipo: "comparacion", signo: "0", texto: `En ${masBarata.tienda} cuesta ${cop(ref)}: prácticamente lo mismo${origen.precio_antes ? ". El descuento anunciado no lo hace más barato que en otras tiendas" : ""}.` }); }
  } else pruebas.push({ tipo: "comparacion", signo: "0", texto: "No encontramos la misma referencia en otra tienda para comparar." });

  // 3. ¿Es una oferta histórica?
  let historica = null;
  if (diasHist >= 30) {
    const min30 = Math.min(...hist.filter(h => Date.parse(hoy) - Date.parse(h.fecha) <= 30 * DIA).map(h => h.precio));
    historica = origen.precio <= min30;
    pruebas.push({ tipo: "historial", signo: historica ? "+" : "0", texto: historica ? `Es su precio más bajo de los últimos 30 días.` : `En los últimos 30 días llegó a estar en ${cop(min30)}.` });
  } else pruebas.push({ tipo: "historial", signo: "0", texto: diasHist ? `Llevamos ${diasHist} día${diasHist === 1 ? "" : "s"} siguiendo este precio; necesitamos 30 para decir si es una oferta histórica.` : "Todavía no tenemos historial de este precio." });

  if (!origen.propio) pruebas.push({ tipo: "vendedor", signo: "-", texto: `Lo vende ${origen.vendedor || "un tercero"} dentro de ${origen.tienda}, no la tienda misma.` });

  // Veredicto
  let estado;
  if (inflado) estado = "precio_inflado";
  else if (comparacion === "mas_barato" && historica !== false) estado = "oferta_real";
  else if (comparacion === "mas_caro" || comparacion === "igual" || historica === false || senalDebil) estado = "dudosa";
  else estado = "insuficiente";
  return { estado, pruebas, diasHistorial: diasHist };
}
