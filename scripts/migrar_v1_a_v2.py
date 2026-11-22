"""Migración sin pérdida: data/ofertas.json (v1, lista plana) -> data/v2/* (modelo separado).

- No modifica ni borra data/ofertas.json ni data/historial.json (la página publicada sigue usándolos).
- Usa los respaldos crudos de la lectura del 21 nov para recuperar el vendedor y los precios por condición.
- Conserva los identificadores v1: los reportes de la comunidad están ligados a ellos.
- Validación de vendedores según la opción B aprobada (scripts/validacion.py): solo coincidencia EXACTA
  entre el vendedor del listado y el comercio valida automáticamente; se guarda evidencia y fecha.
- Comparabilidad técnica (mismo producto) y elegibilidad pública (se puede mostrar) se calculan por separado.
- Clasificación: estructura aprobada, umbrales NO activos (data/v2/config_clasificacion.json).

- Evidencia corporativa del canal (decisión 22 nov): con --chequeo, las publicaciones sin vendedor identificado
  se validan contra data/v2/identidades_corporativas.json y la revisión de cada ficha; las excepciones quedan pendientes.

Uso:  python3 scripts/migrar_v1_a_v2.py [--salida DIR] [--chequeo data/v2/chequeos/alkosto-2026-11-22.json]
      --salida permite un ensayo sin tocar data/v2.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from normalizar import canonical_brand, model_codes, norm_text, specs  # noqa: E402
from comparador import agrupar, comparar_precios, comercios_independientes  # noqa: E402
from validacion import (cargar_identidades, clasificar_vendedor, elegibilidad_publica,  # noqa: E402
                        estado_publicacion, validar_por_canal)

ROOT = os.path.join(os.path.dirname(__file__), "..")
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
RESP = P("data", "respaldo", "2026-11-21")
OUT = P("data", "v2")
ORIGEN = "v1-2026-11-21"
COMERCIO_ID = {"Falabella": "falabella", "Alkosto": "alkosto", "Éxito": "exito"}
# Referencias con duda de equivalencia (decisión 21 nov: DuraPro y AF141LAA fuera hasta revisión humana).
REFERENCIAS_EN_REVISION = [re.compile(r"BLBD\s*-?\s*210", re.I), re.compile(r"AF141LAA", re.I)]
FUENTE_CRUDA = "lectura del listado de la tienda (respaldo crudo)"


def h(*parts, n=12):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:n]


def identidad_id(val):
    return "colombiana-de-comercio" if val.get("vendedor_real", {}).get("nit") == "890.900.943-1" else h(val["vendedor_real"]["razon_social"], n=10)


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def dump(name, data):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def main():
    global OUT, RESP, ORIGEN, FUENTE_CRUDA
    ap = argparse.ArgumentParser()
    ap.add_argument("--salida", default=OUT)
    ap.add_argument("--chequeo", action="append", default=[])
    ap.add_argument("--respaldo-dir", default=RESP)
    ap.add_argument("--catalogo-v1", default=P("data", "ofertas.json"))
    ap.add_argument("--historial-v1", default=P("data", "historial.json"))
    ap.add_argument("--origen", default=ORIGEN)
    ap.add_argument("--fecha-verificacion",
                    default=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-5))).date().isoformat(),  # hora de Colombia
                    help="Fecha real de esta actualización (AAAA-MM-DD); no reutiliza chequeos de otros días.")
    args = ap.parse_args()
    OUT = args.salida
    RESP = os.path.abspath(args.respaldo_dir)
    ORIGEN = args.origen
    FUENTE_CRUDA = "lectura del listado de la tienda (respaldo crudo " + os.path.basename(RESP) + ")"
    identidades = cargar_identidades()
    chequeos = {}
    for ruta in args.chequeo:
        c = load(ruta)
        for path, ficha in c["fichas"].items():
            chequeos[(c["comercio_id"], path)] = dict(ficha, fecha=c["fecha"], fuente=os.path.relpath(ruta, ROOT))
    v1 = load(args.catalogo_v1)
    hist_v1 = load(args.historial_v1)
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

    def vendedor_para(comercio_id, nombre_vendedor, marca, fecha, url=None, condicion=None):
        """Valida al vendedor de una publicación (opción B + evidencia del canal) y lo registra como entidad."""
        val = clasificar_vendedor(comercio_id, nombre_vendedor, marca, fecha, FUENTE_CRUDA, identidades)
        vid = f"desconocido@{comercio_id}" if not nombre_vendedor else h(comercio_id, norm_text(nombre_vendedor), n=10)
        if not nombre_vendedor and chequeos:
            path = re.sub(r"^https?://[^/]+", "", url or "")
            ch = chequeos.get((comercio_id, path))
            if ch:
                val = validar_por_canal(comercio_id, ch, identidades, args.fecha_verificacion, condicion)
                if val["estado_validacion"] == "validado":
                    vid = f"{identidad_id(val)}@{comercio_id}"
        if vid not in vendedores:
            vendedores[vid] = {"id": vid, "nombre": nombre_vendedor or (val.get("vendedor_real") or {}).get("razon_social"), "comercio_id": comercio_id,
                               "tipo": val["tipo"], "estado_validacion": val["estado_validacion"],
                               "metodo_validacion": val["metodo"], "validado_en": val["validado_en"],
                               "motivo": val["motivo"], "nivel_evidencia": val.get("nivel_evidencia"),
                               "revalidar_antes_de": val.get("revalidar_antes_de"),
                               "vendedor_real": val.get("vendedor_real"), "evidencias": []}
        v = vendedores[vid]
        if len(v["evidencias"]) < 5:   # muestra de evidencias; la evidencia completa queda en cada publicación
            v["evidencias"].append(val["evidencia"])
        v["publicaciones"] = v.get("publicaciones", 0) + 1
        return vid, val

    norm_pubs = []
    for r in base:
        cid = COMERCIO_ID[r["tienda"]]
        ev = crudo.get(r["link"], {})
        marca = canonical_brand(r.get("marca"), r["nombre"])
        sp = specs(r["nombre"])
        vid, val = vendedor_para(cid, ev.get("vendedor"), marca, r["verificado"], r["link"], sp.get("condicion_producto"))
        estado, motivo = estado_publicacion(val, sp.get("condicion_producto"))
        pub_rec = {
            "id": r["id"], "producto_id": None, "comercio_id": cid, "vendedor_id": vid,
            "titulo": r["nombre"], "marca_publicada": r.get("marca") or None, "url": r["link"], "imagen": r.get("img"),
            "categoria": r.get("categoria"), "subcategoria": r.get("sub"),
            "disponibilidad": "desconocida", "estado_validacion": estado, "motivo_estado": motivo,
            "condicion_producto": sp.get("condicion_producto", "nuevo"),
            "validacion_vendedor": val, "verificado_en": r["verificado"], "origen": ORIGEN,
        }
        ok, motivos = elegibilidad_publica(pub_rec, val)
        pub_rec["elegibilidad_publica"] = {"elegible": ok, "motivos": motivos}
        publicaciones.append(pub_rec)
        mapa_ids[r["id"]] = {"publicacion_id": r["id"], "condicion": "contado"}
        precios.append({"id": h(r["id"], "contado"), "publicacion_id": r["id"], "condicion": "contado", "detalle": None,
                        "monto": r["precio"], "precio_anunciado_antes": r.get("precio_antes"),
                        "verificado_en": r["verificado"], "fuente": ORIGEN})
        if ev.get("tarjeta") and ev["tarjeta"] < r["precio"]:
            precios.append({"id": h(r["id"], "tarjeta"), "publicacion_id": r["id"], "condicion": "tarjeta",
                            "detalle": ev["tarjeta_nombre"], "monto": ev["tarjeta"], "precio_anunciado_antes": None,
                            "verificado_en": r["verificado"], "fuente": "respaldo crudo " + os.path.basename(RESP)})
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
            "estado_referencia": ("en_revision" if any(rx.search(pub_idx[i]["titulo"] + " " + pub_idx[i]["url"]) for i in ids for rx in REFERENCIAS_EN_REVISION)
                                  else "agrupada_automatica" if len(ids) > 1 else "sin_verificar"),
            "metodo_agrupacion": "comparador v1: marca + código exacto + especificaciones sin conflicto" if len(ids) > 1 else None,
            "verificacion_humana": None,   # {por, fecha, notas}: solo una persona puede pasarla a 'verificada'
            "publicaciones": ids,
        })
        for i in ids:
            pub_idx[i]["producto_id"] = pid

    # ---- comparaciones de contado ----
    # técnica: todas las publicaciones NO rechazadas (incluye pendientes) -> sirve para revisar y priorizar validaciones.
    # pública: solo publicaciones elegibles -> lo único que puede llegar al Radar.
    precio_contado = {p["publicacion_id"]: p["monto"] for p in precios if p["condicion"] == "contado"}
    comparaciones = []
    for prod in productos:
        tecnicas = [i for i in prod["publicaciones"] if pub_idx[i]["estado_validacion"] != "rechazado"]
        if len({pub_idx[i]["comercio_id"] for i in tecnicas}) < 2:
            continue
        publicas = [i for i in tecnicas if pub_idx[i]["elegibilidad_publica"]["elegible"]]
        if prod["estado_referencia"] == "en_revision":
            publicas = []                 # la referencia no se compara en público hasta que una persona la revise
        mk = lambda ids: [{"publicacion_id": i, "comercio_id": pub_idx[i]["comercio_id"], "condicion": "contado",
                           "monto": precio_contado[i]} for i in ids]
        filas_t = comparar_precios(mk(tecnicas), comercios, "contado")
        filas_p = comparar_precios(mk(publicas), comercios, "contado") if publicas else []
        estado_p = filas_p[0]["estado_comparacion"] if filas_p else "sin_comparacion"
        for f in filas_p:
            f["etiqueta"] = None          # umbrales no aprobados: se muestran diferencias, sin etiqueta
            f["apta_radar"] = f["estado_comparacion"] in ("completa", "limitada")
        comparaciones.append({
            "producto_id": prod["id"], "condicion": "contado",
            "estado_referencia": prod["estado_referencia"],
            "tecnica": {"estado": "candidata", "comercios_independientes": comercios_independientes({pub_idx[i]["comercio_id"] for i in tecnicas}, comercios),
                        "estado_comparacion": filas_t[0]["estado_comparacion"], "filas": filas_t,
                        "pendientes": [i for i in tecnicas if not pub_idx[i]["elegibilidad_publica"]["elegible"]]},
            "publica": {"comercios_independientes": filas_p[0]["comercios_independientes"] if filas_p else len({pub_idx[i]["comercio_id"] for i in publicas}),
                        "estado_comparacion": estado_p, "filas": filas_p},
            "excluidas_por_vendedor": [i for i in prod["publicaciones"] if i not in tecnicas],
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
    for c in comparaciones:
        for f in c["publica"]["filas"]:
            if not pub_idx[f["publicacion_id"]]["elegibilidad_publica"]["elegible"]:
                errores.append(f"publicación no elegible en comparación pública: {f['publicacion_id']}")
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

    for c in comparaciones:
        if c["estado_referencia"] == "en_revision" and c["publica"]["filas"]:
            errores.append(f"referencia en revisión con comparación pública: {c['producto_id']}")
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
        "vendedores_por_estado": dict(Counter(v["estado_validacion"] for v in vendedores.values())),
        "vendedores_validados_automaticamente": sorted(f"{v['nombre'] or v['id']}@{v['comercio_id']} ({v['metodo_validacion']})" for v in vendedores.values() if v["metodo_validacion"]),
        "publicaciones_por_nivel_evidencia": dict(Counter(str(p["validacion_vendedor"].get("nivel_evidencia")) for p in publicaciones if p["estado_validacion"] == "validado")),
        "publicaciones_elegibles_publico": sum(1 for p in publicaciones if p["elegibilidad_publica"]["elegible"]),
        "referencias_por_estado": dict(Counter(p["estado_referencia"] for p in productos)),
        "comparaciones_tecnicas": dict(Counter(c["tecnica"]["estado_comparacion"] for c in comparaciones)),
        "comparaciones_publicas": dict(Counter(c["publica"]["estado_comparacion"] for c in comparaciones)),
        "filas_aptas_radar": sum(1 for c in comparaciones for f in c["publica"]["filas"] if f.get("apta_radar")),
        "pares_candidatos_para_revision": len(cand), "observaciones_historial": len(historial),
        "errores_verificacion": errores,
    }
    dump("informe_migracion.json", informe)
    print(json.dumps(informe, ensure_ascii=False, indent=1))
    if errores:
        raise SystemExit(f"{len(errores)} errores de verificación")


if __name__ == "__main__":
    main()
