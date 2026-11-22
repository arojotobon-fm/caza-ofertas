"""Migración sin pérdida: data/ofertas.json (v1, lista plana) -> data/v2/* (modelo separado).

- No modifica ni borra data/ofertas.json ni data/historial.json (la página publicada sigue usándolos).
- Usa los respaldos crudos de la lectura del 21 nov para recuperar el vendedor y los precios por condición.
- Conserva los identificadores v1: los reportes de la comunidad están ligados a ellos.
- Nada queda 'validado' automáticamente: la validación es una decisión humana (docs/MODELO_DATOS.md §4).

Uso:  python3 scripts/migrar_v1_a_v2.py
"""
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from normalizar import canonical_brand, model_codes, norm_text, specs  # noqa: E402
from comparador import agrupar, comparar_precios, comercios_independientes  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
RESP = P("data", "respaldo", "2026-11-21")
OUT = P("data", "v2")
ORIGEN = "v1-2026-11-21"
COMERCIO_ID = {"Falabella": "falabella", "Alkosto": "alkosto", "Éxito": "exito"}
RETAILER_NAMES = {"falabella": {"FALABELLA"}, "exito": {"EXITO"}, "alkosto": {"ALKOSTO"}}


def h(*parts, n=12):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:n]


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(name, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    v1 = load(P("data", "ofertas.json"))
    hist_v1 = load(P("data", "historial.json"))
    com = load(P("data", "v2", "comercios.json"))
    comercios = {c["id"]: c for c in com["comercios"]}

    # ---- evidencia cruda por enlace (vendedor y precios por condición) ----
    crudo = {}
    for q, name, brand, price, antes, cmr, path, img, seller, rating, rev in load(os.path.join(RESP, "crudo-fal_rows.json")):
        crudo["https://www.falabella.com.co/falabella-co/product/" + path] = {
            "vendedor": "Falabella" if seller == 1 else (seller or None), "tarjeta": cmr, "tarjeta_nombre": "Tarjeta CMR Falabella"}
    for q, name, ps, path, img, rating, rev in load(os.path.join(RESP, "crudo-alk_rows.json")):
        if not path:
            continue
        dist = sorted(set(ps or []))
        crudo["https://www.alkosto.com" + path] = {"vendedor": None, "tarjeta": dist[0] if len(dist) >= 3 else None,
                                                   "tarjeta_nombre": "Tarjeta Alkosto"}
    for q, l0, l1, ps, path, img, seller, rating, rev in load(os.path.join(RESP, "crudo-exi_rows.json")):
        if not path:
            continue
        card = ps[1] if ps and len(ps) >= 3 and ps[1] < ps[-1] else None
        crudo["https://www.exito.com" + path] = {"vendedor": (seller or "").strip() or None, "tarjeta": card,
                                                 "tarjeta_nombre": "Tarjeta Éxito"}

    base = [r for r in v1["productos"] if not r.get("condicion")]
    variantes = [r for r in v1["productos"] if r.get("condicion")]
    base_por_link = {r["link"]: r for r in base}

    vendedores, publicaciones, precios, mapa_ids = {}, [], [], {}

    def vendedor_para(comercio_id, nombre_vendedor, marca):
        """Clasifica al vendedor según la evidencia del listado. Nunca valida por sí solo."""
        if not nombre_vendedor:
            vid = f"desconocido@{comercio_id}"
            vendedores.setdefault(vid, {"id": vid, "nombre": None, "tipo": None, "comercio_id": comercio_id,
                                        "estado_validacion": "pendiente",
                                        "evidencia": "El listado no informaba quién vende; hay que revisarlo en la página del producto.",
                                        "verificado_en": None})
            return vid
        n = norm_text(nombre_vendedor)
        vid = h(comercio_id, n, n=10)
        if vid in vendedores:
            return vid
        if n in RETAILER_NAMES.get(comercio_id, set()):
            tipo, estado, ev = "retailer", "pendiente", "El listado dice 'vendido por' el propio comercio. Falta confirmación humana."
        elif marca and (n.startswith(marca) or marca in n.split()):
            tipo, estado, ev = "tienda_oficial_fabricante", "pendiente", "El nombre del vendedor coincide con la marca; confirmar que es la tienda oficial."
        else:
            tipo, estado, ev = "tercero_marketplace", "rechazado", "Vendedor externo según el listado. Excluido de ofertas aprobadas (política 3.2)."
        vendedores[vid] = {"id": vid, "nombre": nombre_vendedor, "tipo": tipo, "comercio_id": comercio_id,
                           "estado_validacion": estado, "evidencia": ev, "verificado_en": None}
        return vid

    norm_pubs = []
    for r in base:
        cid = COMERCIO_ID[r["tienda"]]
        ev = crudo.get(r["link"], {})
        marca = canonical_brand(r.get("marca"), r["nombre"])
        sp = specs(r["nombre"])
        vid = vendedor_para(cid, ev.get("vendedor"), marca)
        v = vendedores[vid]
        if v["tipo"] == "tercero_marketplace":
            estado, motivo = "rechazado", "vendedor externo"
        elif sp.get("condicion_producto") == "no_nuevo":
            estado, motivo = "rechazado", "producto no nuevo"
        else:
            estado, motivo = "pendiente", "vendedor sin confirmar" if v["estado_validacion"] == "pendiente" else "pendiente de revisión"
        publicaciones.append({
            "id": r["id"], "producto_id": None, "comercio_id": cid, "vendedor_id": vid,
            "titulo": r["nombre"], "marca_publicada": r.get("marca") or None, "url": r["link"], "imagen": r.get("img"),
            "categoria": r.get("categoria"), "subcategoria": r.get("sub"),
            "disponibilidad": "desconocida", "estado_validacion": estado, "motivo_estado": motivo,
            "verificado_en": r["verificado"], "origen": ORIGEN,
        })
        mapa_ids[r["id"]] = {"publicacion_id": r["id"], "condicion": "contado"}
        precios.append({"id": h(r["id"], "contado"), "publicacion_id": r["id"], "condicion": "contado", "detalle": None,
                        "monto": r["precio"], "precio_anunciado_antes": r.get("precio_antes"),
                        "verificado_en": r["verificado"], "fuente": ORIGEN})
        if ev.get("tarjeta") and ev["tarjeta"] < r["precio"]:
            precios.append({"id": h(r["id"], "tarjeta"), "publicacion_id": r["id"], "condicion": "tarjeta",
                            "detalle": ev["tarjeta_nombre"], "monto": ev["tarjeta"], "precio_anunciado_antes": None,
                            "verificado_en": r["verificado"], "fuente": "respaldo crudo 2026-11-21"})
        norm_pubs.append({"id": r["id"], "marca": marca, "codigos": model_codes(r["nombre"]), "specs": sp,
                          "categoria": r.get("categoria")})

    # variantes con tarjeta de v1 -> precio 'tarjeta' de su publicación base (se conserva el id v1 para los reportes)
    for r in variantes:
        b = base_por_link.get(r["link"])
        if not b:
            raise SystemExit(f"Variante sin publicación base: {r['id']}")
        mapa_ids[r["id"]] = {"publicacion_id": b["id"], "condicion": "tarjeta", "detalle": r["condicion"]}
        if not any(p["publicacion_id"] == b["id"] and p["condicion"] == "tarjeta" for p in precios):
            precios.append({"id": h(b["id"], "tarjeta"), "publicacion_id": b["id"], "condicion": "tarjeta",
                            "detalle": r["condicion"].replace("con ", ""), "monto": r["precio"],
                            "precio_anunciado_antes": None, "verificado_en": r["verificado"], "fuente": ORIGEN})

    # ---- productos (referencias): agrupación exacta del comparador ----
    grupos, candidatas = agrupar(norm_pubs)
    idx = {p["id"]: p for p in norm_pubs}
    pub_idx = {p["id"]: p for p in publicaciones}
    productos = []
    for ids in grupos:
        ids = sorted(ids)
        first = idx[ids[0]]
        codes = sorted(set().union(*[idx[i]["codigos"] for i in ids]))
        merged = {}
        for i in ids:
            for k, v in idx[i]["specs"].items():
                if k != "color":
                    merged.setdefault(k, v)
        pid = "prod-" + h(*ids, n=10)
        productos.append({
            "id": pid, "marca": first["marca"] or None, "nombre_canonico": pub_idx[ids[0]]["titulo"],
            "categoria": pub_idx[ids[0]]["categoria"], "subcategoria": pub_idx[ids[0]]["subcategoria"],
            "codigos_modelo": codes, "especificaciones": merged, "fuente_especificaciones": "extraídas del nombre publicado",
            "estado_referencia": "agrupada_automatica" if len(ids) > 1 else "sin_verificar",
            "publicaciones": ids,
        })
        for i in ids:
            pub_idx[i]["producto_id"] = pid

    # ---- comparaciones de contado, solo con publicaciones no rechazadas ----
    precio_contado = {p["publicacion_id"]: p["monto"] for p in precios if p["condicion"] == "contado"}
    comparaciones = []
    for prod in productos:
        vivos = [i for i in prod["publicaciones"] if pub_idx[i]["estado_validacion"] != "rechazado"]
        if len({pub_idx[i]["comercio_id"] for i in vivos}) < 2:
            continue
        ofertas = [{"publicacion_id": i, "comercio_id": pub_idx[i]["comercio_id"], "condicion": "contado",
                    "monto": precio_contado[i]} for i in vivos]
        filas = comparar_precios(ofertas, comercios, "contado")
        comparaciones.append({"producto_id": prod["id"], "condicion": "contado",
                              "comercios_independientes": comercios_independientes({pub_idx[i]["comercio_id"] for i in vivos}, comercios),
                              "estado_comparacion": filas[0]["estado_comparacion"], "filas": filas,
                              "excluidas_por_vendedor": [i for i in prod["publicaciones"] if i not in vivos],
                              "calculado_en": v1["actualizado"]})

    # ---- historial: observaciones por publicación y condición ----
    historial = []
    for pid, rec in hist_v1.items():
        for fecha, monto in sorted(rec["p"].items()):
            historial.append({"publicacion_id": pid, "condicion": "contado", "fecha": fecha, "monto": monto, "fuente": ORIGEN})

    cand = [{"publicacion_a": a, "publicacion_b": b, "motivo": m, "estado_revision": "pendiente"} for a, b, m in candidatas]

    # ---- verificación de no pérdida ----
    errores = []
    precio_idx = defaultdict(list)
    for p in precios:
        precio_idx[(p["publicacion_id"], p["condicion"])].append(p["monto"])
    for r in v1["productos"]:
        m = mapa_ids.get(r["id"])
        if not m:
            errores.append(f"id v1 sin destino: {r['id']}")
            continue
        if r["precio"] not in precio_idx[(m["publicacion_id"], m["condicion"])]:
            errores.append(f"precio perdido: {r['id']} {m}")
        pub = pub_idx[m["publicacion_id"]]
        if pub["url"] != r["link"]:
            errores.append(f"enlace distinto: {r['id']}")
    if len(historial) != sum(len(v["p"]) for v in hist_v1.values()):
        errores.append("historial incompleto")

    os.makedirs(OUT, exist_ok=True)
    dump("vendedores.json", sorted(vendedores.values(), key=lambda v: (v["comercio_id"], v["tipo"] or "", v["nombre"] or "")))
    dump("productos.json", productos)
    dump("publicaciones.json", publicaciones)
    dump("precios.json", precios)
    dump("historial.json", historial)
    dump("comparaciones.json", comparaciones)
    dump("candidatas_revision.json", cand)
    dump("mapa_ids_v1.json", mapa_ids)

    vt = Counter((v["tipo"] or "desconocido") for v in vendedores.values())
    informe = {
        "origen": ORIGEN, "registros_v1": len(v1["productos"]), "publicaciones_v2": len(publicaciones),
        "variantes_tarjeta_v1_convertidas_en_precio": len(variantes), "ids_v1_mapeados": len(mapa_ids),
        "precios": dict(Counter(p["condicion"] for p in precios)),
        "publicaciones_por_estado": dict(Counter(p["estado_validacion"] for p in publicaciones)),
        "publicaciones_por_motivo": dict(Counter(p["motivo_estado"] for p in publicaciones)),
        "publicaciones_por_comercio_y_estado": {f"{c}/{e}": n for (c, e), n in Counter((p["comercio_id"], p["estado_validacion"]) for p in publicaciones).items()},
        "vendedores_por_tipo": dict(vt), "productos_referencia": len(productos),
        "productos_en_varias_tiendas": sum(1 for p in productos if len({pub_idx[i]["comercio_id"] for i in p["publicaciones"]}) > 1),
        "comparaciones_contado": dict(Counter(c["estado_comparacion"] for c in comparaciones)),
        "pares_candidatos_para_revision": len(cand), "observaciones_historial": len(historial),
        "errores_verificacion": errores,
    }
    dump("informe_migracion.json", informe)
    print(json.dumps(informe, ensure_ascii=False, indent=1))
    if errores:
        raise SystemExit(f"{len(errores)} errores de verificación")


if __name__ == "__main__":
    main()
