import argparse, json, re, statistics, unicodedata, datetime, os

def argumentos():
    ap = argparse.ArgumentParser(description="Construye catálogo v1 desde respaldos crudos, sin tocar producción.")
    ap.add_argument("--respaldo-dir", required=True)
    ap.add_argument("--fecha", required=True, help="AAAA-MM-DD")
    ap.add_argument("--salida", required=True, help="Directorio aislado de salida")
    ap.add_argument("--historial-base")
    return ap.parse_args()

ARGS = argumentos()
RESP = os.path.abspath(ARGS.respaldo_dir)
SALIDA = os.path.abspath(ARGS.salida)
os.makedirs(SALIDA, exist_ok=True)
NOW = datetime.datetime.fromisoformat(ARGS.fecha + "T12:00:00-05:00").isoformat()
SUB = {"freidora":"Electrodomésticos","licuadora":"Electrodomésticos","cafetera":"Electrodomésticos","aspiradora":"Hogar",
       "televisor":"Televisores","audifonos":"Tecnología","parlante":"Tecnología","smartwatch":"Tecnología","celular":"Celulares",
       "portatil":"Tecnología","tablet":"Tecnología","consola":"Videojuegos","lego":"Juguetes","secador":"Belleza y cuidado"}
CAT = {
    "freidora": "Electrodomésticos", "licuadora": "Electrodomésticos", "cafetera": "Electrodomésticos",
    "aspiradora": "Electrodomésticos", "televisor": "Tecnología", "audifonos": "Tecnología",
    "parlante": "Tecnología", "smartwatch": "Tecnología", "celular": "Tecnología", "portatil": "Tecnología",
    "tablet": "Tecnología", "consola": "Juguetes y regalos", "lego": "Juguetes y regalos",
    "secador": "Hogar y belleza",
}
SKIP = re.compile(r"reacondicionad|usado|open ?box|funda|carcasa|protector|vidrio templado|repuesto|filtro de|correa para|estuche", re.I)


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return s.upper()


UNIT = re.compile(r"^\d+(\.\d+)?(L|LT|LTS|LITROS|GB|TB|W|WATTS|MAH|HZ|MP|PULGADAS|PULG|CM|MM|ML|OZ|V|K|P|G|PCS|PZ|PIEZAS|X\d+)$")


def models(name):
    toks = re.findall(r"[A-Z0-9][A-Z0-9\-/\.]{2,}", norm(name))
    out = set()
    for t in toks:
        t2 = re.sub(r"[\-/\.]", "", t)
        if len(t2) < 4 or not re.search(r"\d", t2) or not re.search(r"[A-Z]", t2):
            continue
        if UNIT.match(t) or UNIT.match(t2):
            continue
        if re.match(r"^(RTX|GTX|RAM|SSD|DDR|USB|IP|BT|WIFI|HDMI|QLED|OLED|UHD|FHD|LED|CORE|RYZEN|SERIE|SERIES|GEN)\d*", t2) and len(t2) <= 6:
            continue
        out.add(t2)
    return out


def human_slug(url):
    slug = url.strip("/").split("/")[0]
    return slug.replace("-", " ").capitalize()


items = []
# Falabella: [q, name, brand, price, antes, cmr, path, img, seller(1=Falabella), rating, reviews]
for q, name, brand, price, antes, cmr, path, img, seller, rating, rev in json.load(open(os.path.join(RESP, "crudo-fal_rows.json"), encoding="utf-8")):
    if not price: continue
    items.append(dict(tienda="Falabella", q=q, nombre=name, marca=(brand or "").title(), precio=price,
                      precio_antes=antes, tarjeta=cmr, tarjeta_nombre="tarjeta CMR",
                      link="https://www.falabella.com.co/falabella-co/product/" + path,
                      img=("https://media.falabella.com.co/falabellaCO/%s/width=400,height=400,quality=80,format=webp,fit=pad" % img) if img else None,
                      vendedor="Falabella" if seller == 1 else seller, rating=rating, reviews=rev))
# Alkosto: [q, name, prices, path, img, rating, reviews]
for q, name, ps, path, img, rating, rev in json.load(open(os.path.join(RESP, "crudo-alk_rows.json"), encoding="utf-8")):
    if not ps or not path: continue
    if not name or not re.match(r"[A-Za-z0-9ÁÉÍÓÚáéíóú]", name):
        name = human_slug(path)
    brand = ""
    m = re.search(r"\b([A-Z][A-Z\+&]{1,}(?: [A-Z]{2,})?)\b", name)
    if m: brand = m.group(1).title()
    dist = sorted(set(ps))
    if len(dist) >= 3:   # [precio Tarjeta Alkosto, precio cualquier medio, antes]
        price, card = dist[1], dist[0]
    elif len(dist) == 2: price, card = dist[0], None
    else: price, card = dist[0], None
    items.append(dict(tienda="Alkosto", q=q, nombre=name, marca=brand, precio=price,
                      precio_antes=max(ps) if max(ps) > price else None, tarjeta=card, tarjeta_nombre="Tarjeta Alkosto",
                      link="https://www.alkosto.com" + path,
                      img=("https://cdn.dam.alkosto.com/products/" + img.replace("?w=310", "?w=400")) if img else None,
                      vendedor="Alkosto", rating=rating, reviews=rev,
                      nota_hoy=False))
# Exito: [q, l0, l1, prices, path, img, seller, rating, reviews]
for q, l0, l1, ps, path, img, seller, rating, rev in json.load(open(os.path.join(RESP, "crudo-exi_rows.json"), encoding="utf-8")):
    if not ps or not path: continue
    if l0 in ("Patrocinado", "Producto genérico"):
        name, brand = l1, ""
    else:
        name, brand = l0, l1
    if len(ps) == 1: price, antes, card = ps[0], None, None
    elif len(ps) == 2: antes, price, card = ps[0], ps[1], None
    else: antes, price, card = ps[0], ps[-1], ps[1]
    items.append(dict(tienda="Éxito", q=q, nombre=name, marca=(brand or "").title() if brand and len(brand) < 25 else "",
                      precio=price, precio_antes=antes if antes and antes > price else None,
                      tarjeta=card if card and card < price else None, tarjeta_nombre="tarjeta Éxito",
                      link="https://www.exito.com" + path,
                      img=("https://exitocol.vtexassets.com/arquivos/ids/" + img) if img else None,
                      vendedor=(seller or "").strip(), rating=rating, reviews=rev))

# dedupe by link
seen, uniq = set(), []
for it in items:
    if it["link"] in seen or SKIP.search(it["nombre"]): continue
    seen.add(it["link"]); it["categoria"] = CAT.get(it["q"], "Otros"); it["modelos"] = models(it["nombre"])
    uniq.append(it)
items = uniq

def bkey(it):
    b = norm(it.get("marca") or "").replace("+", " ").replace("&", " ").split()
    if b: return b[0]
    return ""

SIZE = re.compile(r"(\d{2,3})\s*(\"|”|''|PULGADAS|PULG)")
BUNDLE = re.compile(r"\+\s*(BARRA|AUDIF|PARLANTE|SOPORTE|BASE|MOUSE|TECLADO|MALETA|FORRO|VASO)|COMBO|KIT ", re.I)
def compatible(a, b):
    sa, sb = SIZE.search(norm(a["nombre"])), SIZE.search(norm(b["nombre"]))
    if sa and sb and sa.group(1) != sb.group(1): return False
    if bool(BUNDLE.search(a["nombre"])) != bool(BUNDLE.search(b["nombre"])): return False
    return True

def same_brand(a, b):
    if not compatible(a, b): return False
    x, y = bkey(a), bkey(b)
    if x and y and x != y:
        # brand may only appear in the other's name
        return x in norm(b["nombre"]) or y in norm(a["nombre"])
    if not x or not y:
        k = x or y
        return not k or (k in norm(a["nombre"]) and k in norm(b["nombre"])) or True
    return True

CPU = re.compile(r"^(I[3579]?\d{4,5}[A-Z]*|\d{4,5}(U|H|HS|HX|K|KF|G|P)|N\d{3,4}|R[3579]\d{4}[A-Z]*|M[1-4](PRO|MAX)?)$")

def same_model(a, b):
    a = {x for x in a if not CPU.match(x)}; b = {y for y in b if not CPU.match(y)}
    for x in a:
        for y in b:
            if x == y: return True
            if min(len(x), len(y)) >= 5 and (x.startswith(y) or y.startswith(x)) and abs(len(x)-len(y)) <= 3: return True
    return False

# cross-store matching by model code
for it in items:
    others = []
    for o in items:
        if o is it or o["tienda"] == it["tienda"]: continue
        if o["categoria"] == it["categoria"] and same_model(it["modelos"], o["modelos"]) and same_brand(it, o):
            others.append(o)
    # keep one (cheapest) per other store
    best = {}
    for o in others:
        if o["tienda"] not in best or o["precio"] < best[o["tienda"]]["precio"]:
            best[o["tienda"]] = o
    it["match"] = list(best.values())

def label(pct, it):
    low = (it.get("rating") is not None and it.get("rating") < 4 and (it.get("reviews") or 0) >= 3)
    reliable = not low and ((it["vendedor"] in ("Falabella", "Alkosto", "Exito", "Éxito")) or (it.get("rating") or 0) >= 4.3)
    if pct > 50: return "error"
    if pct >= 30 and reliable: return "gangazo"
    if pct >= 15: return "buena"
    if it.get("precio_antes") and (it["precio_antes"] - it["precio"]) / it["precio_antes"] >= 0.4 and pct < 5: return "vitrina"
    return "justo"

out = []
extra = []
for it in items:
    rec = dict(nombre=it["nombre"], marca=it["marca"], categoria=it["categoria"], sub=SUB.get(it["q"], "Otros"), tienda=it["tienda"],
               precio=it["precio"], precio_antes=it["precio_antes"], link=it["link"], img=it["img"],
               verificado=NOW, top=False)
    notes = []
    if it["vendedor"] and it["vendedor"] not in ("Falabella", "Alkosto", "Exito", "Éxito"):
        notes.append("Vendedor externo: " + it["vendedor"] + ".")
    if it["match"]:
        ref = statistics.median([o["precio"] for o in it["match"]])
        # sanity: same product should be within 0.5x–1.8x
        if 0.5 <= it["precio"] / ref <= 1.8:
            pct = max(0, (ref - it["precio"]) / ref * 100)
            rec["precio_ref"] = int(ref)
            rec["clasificacion"] = label(pct, it)
            rec["comparado_en"] = [o["tienda"] for o in it["match"]]
            rec["comparativo"] = sorted([{"tienda": it["tienda"], "precio": it["precio"], "link": it["link"]}] +
                                        [{"tienda": o["tienda"], "precio": o["precio"], "link": o["link"]} for o in it["match"]], key=lambda x: x["precio"])
            notes.insert(0, "Comparado con " + ", ".join(f"{o['tienda']} ${o['precio']:,}".replace(",", ".") for o in it["match"]) + ".")
            rec["_pct"] = pct
    if "precio_ref" not in rec:
        rec["clasificacion"] = "sin"
        rec["_pct"] = -1
    if it.get("tarjeta"):
        notes.append(f"Con {it['tarjeta_nombre']}: ${it['tarjeta']:,}.".replace(",", "."))
    if it.get("nota_hoy"):
        notes.append("Precio especial del día en Alkosto.")
    if it.get("rating"):
        notes.append(f"{it['rating']}★ ({it['reviews']} opiniones).")
        if it["rating"] < 4 and (it.get("reviews") or 0) >= 3: notes.append("⚠️ Calificación baja: revisa opiniones antes de comprar.")
    if it.get("tarjeta") and "precio_ref" in rec:
        pct_t = max(0, (rec["precio_ref"] - it["tarjeta"]) / rec["precio_ref"] * 100)
        if pct_t > rec["_pct"] + 3:
            v = dict(rec); v["precio"] = it["tarjeta"]; v["condicion"] = "con " + it["tarjeta_nombre"]
            v["clasificacion"] = label(pct_t, dict(it, precio=it["tarjeta"])); v["_pct"] = pct_t; v["_variant"] = True
            v["nota"] = None
            extra.append((v, rec, it))
    rec["nota"] = " ".join(notes)
    out.append(rec)

for v, rec, it in extra:
    v["nota"] = "Precio pagando " + v["condicion"] + "; con otros medios de pago: $" + f"{rec['precio']:,}".replace(",", ".") + ". " + (rec["nota"] or "")
    out.append(v)

# Top 20: compared items, highest real %, one per model family, prefer reliable
cands = sorted([r for r in out if r["_pct"] >= 8 and r["clasificacion"] != "error" and "Calificación baja" not in (r["nota"] or "")], key=lambda r: -r["_pct"])
used, rank = set(), 0
for r in cands:
    key = frozenset(models(r["nombre"]))
    if key & used if isinstance(key, frozenset) and used else False:
        continue
    if any(k in used for k in key): continue
    rank += 1; r["top"] = True; r["rank"] = rank
    used |= set(key)
    if rank == 20: break

out = [r for r in out if not (r.get("_variant") and not r.get("top"))]
import hashlib
for r in out:
    r.pop("_pct", None); r.pop("_variant", None)
    r["id"] = hashlib.sha1((r["link"] + "|" + (r.get("condicion") or "")).encode()).hexdigest()[:12]
json.dump({"actualizado": NOW, "productos": out}, open(os.path.join(SALIDA, "ofertas.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("total", len(out), "comparados", sum(1 for r in out if r.get("precio_ref")), "top", rank)
for r in sorted([r for r in out if r["top"]], key=lambda r: r["rank"]):
    print(r["rank"], r["tienda"], r["nombre"][:70], r["precio"], r.get("precio_ref"), r["clasificacion"])
    mm=[it for it in items if it["link"]==r["link"]][0]["match"]
    for o in mm: print("     ~", o["tienda"], o["nombre"][:80], o["precio"])

# ---- Historial de precios (base para la analítica "cuándo comprar") ----
import os
HP = os.path.join(SALIDA, "historial.json")
hist = json.load(open(ARGS.historial_base, encoding="utf-8")) if ARGS.historial_base else {}
day = NOW[:10]
for r in out:
    if r.get("condicion"): continue
    h = hist.setdefault(r["id"], {"n": r["nombre"][:90], "t": r["tienda"], "p": {}})
    h["p"][day] = min(r["precio"], h["p"].get(day, 10**12))
json.dump(hist, open(HP, "w"), ensure_ascii=False, separators=(",", ":"))
print("historial:", len(hist), "productos")
