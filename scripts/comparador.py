"""Comparador v1: agrupa publicaciones que son el MISMO producto y compara precios en condiciones equivalentes.

Reglas (docs/MODELO_DATOS.md y transferencia del proyecto, §3.3 y §3.5):
- Misma marca canónica.
- Mismo código de modelo exacto (normalizado). Un código que solo coincide por prefijo
  (p. ej. AF141 vs AF141LAA) queda como coincidencia CANDIDATA para revisión humana; nunca se agrupa solo.
- Ninguna especificación estricta en conflicto (pulgadas, RAM, almacenamiento, capacidad, combo, condición).
  Si una publicación no informa una especificación, no se considera conflicto, pero se anota.
- Comercios del mismo grupo empresarial cuentan como UNO para la regla de 3 comercios independientes.
- Solo se comparan precios de la misma condición (contado con contado, tarjeta con tarjeta del mismo emisor no aplica entre tiendas).
"""
from itertools import combinations
from statistics import median

from normalizar import SPEC_KEYS_STRICT

MIN_COMERCIOS_COMPLETA = 3   # regla editorial aprobada


def spec_conflicts(a, b):
    """Lista de especificaciones en conflicto y de especificaciones que solo una informa."""
    conflicts, missing = [], []
    for k in SPEC_KEYS_STRICT:
        va, vb = a.get(k), b.get(k)
        if va is None and vb is None:
            continue
        if va is None or vb is None:
            # combo / no nuevo: si una lo declara y la otra no, se asume distinto
            if k in ("es_combo", "condicion_producto"):
                conflicts.append(k)
            else:
                missing.append(k)
        elif va != vb:
            conflicts.append(k)
    return conflicts, missing


def code_relation(codes_a, codes_b):
    """'exacta' si comparten un código idéntico; 'prefijo' si uno es prefijo del otro (≥5 caracteres); None si nada."""
    if codes_a & codes_b:
        return "exacta", sorted(codes_a & codes_b)[0]
    for x in codes_a:
        for y in codes_b:
            if min(len(x), len(y)) >= 5 and (x.startswith(y) or y.startswith(x)) and abs(len(x) - len(y)) <= 3:
                return "prefijo", f"{x}~{y}"
    return None, None


def evaluar_par(a, b):
    """Decide si dos publicaciones son el mismo producto.

    a y b son dicts con: marca, codigos (set), specs (dict), categoria.
    Devuelve (estado, motivo) con estado en {'exacta', 'candidata', 'descartada'}.
    """
    if not a["marca"] or not b["marca"]:
        return "descartada", "marca desconocida"
    if a["marca"] != b["marca"]:
        return "descartada", "marca distinta"
    if a.get("categoria") and b.get("categoria") and a["categoria"] != b["categoria"]:
        return "descartada", "categoría distinta"
    rel, code = code_relation(a["codigos"], b["codigos"])
    if not rel:
        return "descartada", "sin código de modelo en común"
    conflicts, missing = spec_conflicts(a["specs"], b["specs"])
    if conflicts:
        return "descartada", "especificaciones distintas: " + ", ".join(conflicts)
    if rel == "prefijo":
        return "candidata", f"código parecido ({code}); revisar si es la misma referencia"
    if missing:
        return "candidata", f"mismo código {code}, pero falta confirmar: " + ", ".join(missing)
    return "exacta", f"mismo código {code}"


def agrupar(pubs):
    """Agrupa publicaciones por coincidencia EXACTA (componentes conexos con verificación de consistencia).

    pubs: lista de dicts con id, marca, codigos, specs, categoria.
    Devuelve (grupos, candidatas) donde grupos = lista de listas de ids y
    candidatas = lista de (id_a, id_b, motivo) para revisión humana.
    """
    idx = {p["id"]: p for p in pubs}
    parent = {p["id"]: p["id"] for p in pubs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    by_brand = {}
    for p in pubs:
        by_brand.setdefault(p["marca"], []).append(p)

    candidatas = []
    for brand, items in by_brand.items():
        if not brand:
            continue
        for a, b in combinations(items, 2):
            if not (a["codigos"] and b["codigos"]):
                continue
            estado, motivo = evaluar_par(a, b)
            if estado == "exacta":
                parent[find(a["id"])] = find(b["id"])
            elif estado == "candidata":
                candidatas.append((a["id"], b["id"], motivo))

    grupos = {}
    for p in pubs:
        grupos.setdefault(find(p["id"]), []).append(p["id"])
    # verificación de consistencia: dentro de un grupo nadie puede tener especificaciones en conflicto
    limpios = []
    for ids in grupos.values():
        ok = all(not spec_conflicts(idx[x]["specs"], idx[y]["specs"])[0] for x, y in combinations(ids, 2))
        if ok:
            limpios.append(ids)
        else:
            limpios.extend([[i] for i in ids])
    return limpios, candidatas


def comercios_independientes(comercio_ids, comercios):
    """Cuenta grupos empresariales distintos (Alkosto+Ktronix+Alkomprar = 1)."""
    return len({comercios[c]["grupo_empresarial"] for c in comercio_ids})


def estado_comparacion(n_independientes):
    if n_independientes >= MIN_COMERCIOS_COMPLETA:
        return "completa"
    if n_independientes == 2:
        return "limitada"
    return "sin_comparacion"


def comparar_precios(ofertas, comercios, condicion="contado"):
    """Compara el precio de una condición entre comercios independientes.

    ofertas: lista de dicts {publicacion_id, comercio_id, condicion, monto}. Solo entran las de la condición pedida.
    Para cada publicación: precio de referencia = mediana del mejor precio de CADA OTRO grupo empresarial.
    """
    filas = [o for o in ofertas if o["condicion"] == condicion]
    mejor_por_grupo = {}
    for o in filas:
        g = comercios[o["comercio_id"]]["grupo_empresarial"]
        if g not in mejor_por_grupo or o["monto"] < mejor_por_grupo[g]["monto"]:
            mejor_por_grupo[g] = o
    n = len(mejor_por_grupo)
    resultado = []
    for o in filas:
        g = comercios[o["comercio_id"]]["grupo_empresarial"]
        otros = [x["monto"] for gg, x in mejor_por_grupo.items() if gg != g]
        ref = median(otros) if otros else None
        resultado.append({
            "publicacion_id": o["publicacion_id"],
            "condicion": condicion,
            "monto": o["monto"],
            "referencia": ref,
            "diferencia": (ref - o["monto"]) if ref else None,
            "ahorro_pct": round((ref - o["monto"]) / ref * 100, 1) if ref else None,
            "comercios_independientes": n,
            "estado_comparacion": estado_comparacion(n),
        })
    return resultado
