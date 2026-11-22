#!/usr/bin/env python3
"""Lectura diaria automática de precios para el historial (la corre GitHub Actions una vez al día).

Lee el precio de HOY de cada producto del catálogo en las tiendas que dejan consultar desde un servidor
(Falabella, Olímpica y Jumbo; Éxito se intenta y, si bloquea, se anota). Guarda por producto:
  p = precio de contado por fecha, a = precio "antes" que anuncia la tienda, c = precio con tarjeta.
No inventa nada: si una lectura falla, ese día queda sin dato.

Uso: python3 scripts/historial_diario.py --catalogo data/ofertas.json --historial historial/precios.json [--fecha AAAA-MM-DD]
Solo usa la biblioteca estándar de Python.
"""
import argparse, datetime as dt, json, re, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
VTEX = {"www.olimpica.com": "Olímpica", "www.jumbocolombia.com": "Jumbo", "www.exito.com": "Éxito", "tienda.exito.com": "Éxito"}
num = lambda v: int(re.sub(r"[^\d]", "", str(v or "")) or 0)


def limpio(link):
    return link.split("?")[0].split("#")[0].rstrip("/").lower()


def traer(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "es-CO,es;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def precio_vtex(json_txt):
    """Devuelve (contado, antes, tarjeta) del vendedor de la tienda (sellerId 1) en la respuesta de VTEX."""
    data = json.loads(json_txt)
    if not data:
        return None
    for s in (data[0].get("items") or [{}])[0].get("sellers", []):
        co = s.get("commertialOffer") or {}
        if str(s.get("sellerId")) == "1" and co.get("Price", 0) > 0 and co.get("AvailableQuantity", 0) > 0:
            p, lp = round(co["Price"]), round(co.get("ListPrice") or 0)
            return p, (lp if lp > p else None), None
    return None


def precio_falabella(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        return None
    pd = (json.loads(m.group(1)).get("props", {}).get("pageProps", {}) or {}).get("productData") or {}
    v = (pd.get("variants") or [{}])[0]
    pr = {x.get("type"): num((x.get("price") or [None])[0]) for x in v.get("prices", [])}
    contado = pr.get("internetPrice") or pr.get("eventPrice") or pr.get("normalPrice")
    if not contado:
        return None
    antes = pr.get("normalPrice") if pr.get("normalPrice", 0) > contado else None
    return contado, antes, pr.get("cmrPrice")


def leer(prod):
    link = prod["link"]
    host = urlparse(link).netloc
    try:
        if host == "www.falabella.com.co":
            return prod, precio_falabella(traer(link))
        if host in VTEX:
            base = "https://" + host
            slug = re.sub(r"/p$", "", urlparse(link).path.strip("/"))
            return prod, precio_vtex(traer(f"{base}/api/catalog_system/pub/products/search/{slug}/p"))
    except Exception as e:  # bloqueo, tiempo agotado, producto retirado
        return prod, ("error", type(e).__name__)
    return prod, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalogo", required=True)
    ap.add_argument("--historial", required=True)
    ap.add_argument("--fecha", default=(dt.datetime.utcnow() - dt.timedelta(hours=5)).strftime("%Y-%m-%d"))
    a = ap.parse_args()

    catalogo = json.load(open(a.catalogo, encoding="utf-8"))["productos"]
    try:
        hist = json.load(open(a.historial, encoding="utf-8"))
    except FileNotFoundError:
        hist = {}
    vistos, objetivo = set(), []
    for p in catalogo:
        if p.get("condicion") or p.get("oculto"):
            continue
        h = urlparse(p["link"]).netloc
        if (h == "www.falabella.com.co" or h in VTEX) and limpio(p["link"]) not in vistos:
            vistos.add(limpio(p["link"]))
            objetivo.append(p)

    resumen = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for prod, r in ex.map(leer, objetivo):
            t = prod["tienda"]
            resumen.setdefault(t, {"leidos": 0, "sin_precio": 0, "errores": 0})
            if r is None:
                resumen[t]["sin_precio"] += 1
                continue
            if r[0] == "error":
                resumen[t]["errores"] += 1
                continue
            contado, antes, tarjeta = r
            e = hist.setdefault(limpio(prod["link"]), {"n": prod["nombre"], "t": t, "p": {}, "a": {}, "c": {}})
            e["n"] = prod["nombre"]
            e["p"][a.fecha] = contado
            if antes:
                e["a"][a.fecha] = antes
            if tarjeta:
                e["c"][a.fecha] = tarjeta
            resumen[t]["leidos"] += 1
            time.sleep(0.05)

    with open(a.historial, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, separators=(",", ":"))
    print(json.dumps({"fecha": a.fecha, "por_tienda": resumen, "productos_en_historial": len(hist)}, ensure_ascii=False))
    if not any(v["leidos"] for v in resumen.values()):
        sys.exit("Ninguna tienda respondió: no se guarda nada nuevo.")


if __name__ == "__main__":
    main()
