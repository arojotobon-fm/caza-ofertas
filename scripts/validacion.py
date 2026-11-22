"""Validación de vendedores y elegibilidad pública (decisión aprobada: opción B con controles).

Reglas aprobadas (22 nov 2026):
- Se valida AUTOMÁTICAMENTE solo cuando la publicación identifica expresamente al vendedor y su nombre
  coincide EXACTAMENTE (tras normalizar mayúsculas/tildes/espacios) con el nombre oficial del comercio
  donde está publicada. Una coincidencia aproximada NO basta: queda pendiente de revisión humana.
- Se conserva la evidencia (texto del listado, fuente) y la fecha.
- Alkosto sin vendedor identificado: pendiente.
- Tiendas oficiales de fabricante: pendiente hasta validación humana de su oficialidad.
- Terceros de marketplace: rechazados.

Comparabilidad técnica (¿es el mismo producto?) y elegibilidad comercial (¿se puede mostrar al público?)
son decisiones distintas: este módulo solo decide la segunda.
"""
import datetime
import json
import os
import re

from normalizar import norm_text

# Nombres oficiales con los que el comercio se identifica como vendedor en su propio listado.
# Solo coincidencia exacta con alguno de estos textos normalizados valida automáticamente.
NOMBRES_OFICIALES = {
    "falabella": {"FALABELLA"},
    "exito": {"EXITO"},
    "alkosto": {"ALKOSTO"},
    "ktronix": {"KTRONIX"},
    "alkomprar": {"ALKOMPRAR"},
}

TIPOS_PERMITIDOS = {"retailer", "subsidiaria_verificada", "tienda_oficial_fabricante", "distribuidor_autorizado"}
METODO_AUTO = "automatica_coincidencia_exacta"
METODO_CANAL = "evidencia_corporativa_del_canal"
NIVEL_PUBLICACION = "publicacion"          # la ficha identifica expresamente al vendedor
NIVEL_CANAL = "canal_corporativo"          # contrato/términos del canal + revisión de la ficha
RX_SECCION_ESPECIAL = re.compile(r"REACONDICIONAD|EXHIBICION|OPEN ?BOX|USADO|SEGUNDA MANO|MERCADO TIENDAS FISICAS|PINES|NETFLIX|VIAJES|SEGUROS|GARANTIA EXTENDIDA|INSTALACION")

_IDENT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "v2", "identidades_corporativas.json")


def cargar_identidades(path=_IDENT_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def identidad_por_nombre(nombre, identidades):
    """Identidad corporativa cuyo nombre (razón social o alias documentado) coincide EXACTAMENTE con 'nombre'."""
    n = norm_text(nombre)
    if not n:
        return None, None
    for ident in identidades["identidades"]:
        if norm_text(ident["razon_social"]) == n:
            return ident, {"nombre": ident["razon_social"], "tipo": "razon_social"}
        for a in ident["alias"]:
            if norm_text(a["nombre"]) == n:
                return ident, a
    return None, None


def identidad_del_comercio(comercio_id, identidades):
    for ident in identidades["identidades"]:
        if any(a.get("comercio_id") == comercio_id for a in ident["alias"]):
            return ident
    return None


def canal_validado(comercio_id, identidades, hoy):
    """Evidencia corporativa del canal, si está validada y vigente (revalidación cada 90 días)."""
    ident = identidad_del_comercio(comercio_id, identidades)
    if not ident:
        return None, None
    for c in ident.get("canales", []):
        if c["comercio_id"] == comercio_id and c["estado"] == "validado":
            if c.get("revalidar_antes_de") and hoy > c["revalidar_antes_de"]:
                return ident, None   # vencida: hay que revalidar antes de usarla
            return ident, c
    return ident, None


def validar_por_canal(comercio_id, chequeo, identidades, hoy, condicion_producto=None):
    """Validación de UNA publicación con evidencia corporativa del canal (decisión 22 nov).

    chequeo = revisión de la ficha: {fecha, status, has_main, banner_txt, banner_img, seller_text, h1, crumbs}.
    - Ficha ilegible o sin datos  -> pendiente
    - Otro vendedor/proveedor      -> pendiente (salvo que el nombre sea un alias exacto de la misma identidad)
    - Banner principal con contenido -> pendiente (el contrato dice que ahí se indicaría otro proveedor)
    - Reacondicionado / exhibición / sección especial -> pendiente para revisión individual
    - Si no, retailer validado con nivel 'canal_corporativo'
    """
    ident, canal = canal_validado(comercio_id, identidades, hoy)
    base = {"tipo": None, "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
            "nivel_evidencia": None, "evidencia": {"chequeo_ficha": chequeo}}
    if not ident or not canal:
        return dict(base, motivo="No hay evidencia corporativa del canal vigente para este comercio.")
    if not chequeo or chequeo.get("error") or chequeo.get("status") != 200 or not chequeo.get("has_main"):
        return dict(base, motivo="No se pudo leer la ficha del producto: no se puede determinar quién vende.")
    # La ficha se revisa en cada actualización; no se reutiliza evidencia de días anteriores.
    if chequeo.get("fecha") != hoy:
        return dict(base, motivo="La revisión de esta ficha no corresponde a la fecha de actualización; se requiere una lectura nueva.")
    st = chequeo.get("seller_text")
    if st:
        m = re.search(r"(?:vendido\s+(?:y\s+despachado\s+)?por|proveedor:?|vendedor:?)\s+([A-Za-zÁÉÍÓÚáéíóúÑñ0-9 .&+-]{2,60})", st, re.I)
        nombre = m.group(1).strip() if m else None
        otro, _ = identidad_por_nombre(nombre, identidades) if nombre else (None, None)
        if not (otro and otro["id"] == ident["id"]):
            return dict(base, motivo=f"La ficha menciona otro vendedor o proveedor: «{st[:120]}».")
    if (chequeo.get("banner_txt") or "").strip() or (chequeo.get("banner_img") or "").strip():
        return dict(base, motivo="El banner principal del producto tiene contenido: revisar si indica otro proveedor.")
    if (chequeo.get("special") or condicion_producto == "no_nuevo"
            or RX_SECCION_ESPECIAL.search(norm_text((chequeo.get("h1") or "") + " " + " ".join(chequeo.get("crumbs") or [])))):
        return dict(base, revision_individual=True, motivo="Reacondicionado, exhibición o sección especial: requiere revisión individual.")
    return {
        "tipo": "retailer", "estado_validacion": "validado", "metodo": METODO_CANAL,
        "nivel_evidencia": NIVEL_CANAL, "validado_en": hoy,
        "vendedor_real": {"razon_social": ident["razon_social"], "nit": ident["nit"]},
        "motivo": "La ficha no indica otro vendedor, el banner principal está vacío y es producto nuevo de venta ordinaria; "
                  "el contrato del canal nombra a la razón social como proveedor.",
        "evidencia": {"canal": canal["evidencia_principal"], "chequeo_ficha": chequeo},
    }


def _parece_tienda_oficial(nombre_n, marca_producto):
    if "OFICIAL" in nombre_n:
        return True
    tokens = set(re.findall(r"[A-Z0-9+]+", nombre_n))
    # solo la marca DEL PRODUCTO publicado; una marca cualquiera en el nombre (p. ej. "Tecno optima") no basta
    return bool(marca_producto) and (marca_producto in tokens or nombre_n.startswith(marca_producto + " "))


def clasificar_vendedor(comercio_id, nombre_listado, marca_producto, fecha_evidencia, fuente, identidades=None):
    """Devuelve el registro de validación del vendedor de UNA publicación cuando la ficha lo identifica.

    Siempre incluye la evidencia y el nivel; 'validado_en' solo se llena cuando la validación es efectiva.
    """
    evidencia = {"texto_listado": nombre_listado, "fuente": fuente, "fecha": fecha_evidencia}
    if identidades is None:
        identidades = cargar_identidades()
    r = _clasificar(comercio_id, nombre_listado, marca_producto, fecha_evidencia, evidencia, identidades)
    r.setdefault("nivel_evidencia", NIVEL_PUBLICACION if nombre_listado else None)
    return r


def _clasificar(comercio_id, nombre_listado, marca_producto, fecha_evidencia, evidencia, identidades):
    if not nombre_listado or not str(nombre_listado).strip():
        return {"tipo": None, "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "El listado no identifica al vendedor.", "evidencia": evidencia}
    n = norm_text(nombre_listado)
    oficiales = NOMBRES_OFICIALES.get(comercio_id, set())
    ident, alias = identidad_por_nombre(nombre_listado, identidades)
    if ident:
        propia = identidad_del_comercio(comercio_id, identidades)
        if propia and propia["id"] == ident["id"]:
            return {"tipo": "retailer", "estado_validacion": "validado", "metodo": METODO_AUTO, "validado_en": fecha_evidencia,
                    "vendedor_real": {"razon_social": ident["razon_social"], "nit": ident["nit"]},
                    "motivo": f"El listado identifica a '{nombre_listado}', alias documentado de {ident['razon_social']}, dueña del comercio.",
                    "evidencia": evidencia}
        return {"tipo": "distribuidor_autorizado", "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "vendedor_real": {"razon_social": ident["razon_social"], "nit": ident["nit"]},
                "motivo": f"Empresa identificada ({ident['razon_social']}) vendiendo en un marketplace ajeno: "
                          "requiere comprobar la autorización comercial para esta publicación.",
                "evidencia": evidencia}
    if n in oficiales:
        return {"tipo": "retailer", "estado_validacion": "validado", "metodo": METODO_AUTO, "validado_en": fecha_evidencia,
                "motivo": f"El listado identifica expresamente a '{nombre_listado}' como vendedor y coincide exactamente con el comercio.",
                "evidencia": evidencia}
    if any(o in n for o in oficiales):
        return {"tipo": None, "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "Nombre parecido al del comercio, pero no idéntico: requiere revisión humana.", "evidencia": evidencia}
    if re.search(r"\bDISTRIBUIDOR", n):
        return {"tipo": "distribuidor_autorizado", "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "Se presenta como distribuidor: requiere comprobar la autorización comercial y la identidad para esta publicación.",
                "evidencia": evidencia}
    if _parece_tienda_oficial(n, marca_producto):
        return {"tipo": "tienda_oficial_fabricante", "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "Posible tienda oficial del fabricante: requiere validación humana de su oficialidad.", "evidencia": evidencia}
    return {"tipo": "tercero_marketplace", "estado_validacion": "rechazado", "metodo": None, "validado_en": None,
            "motivo": "Vendedor externo de marketplace: excluido de ofertas aprobadas (política 3.2).", "evidencia": evidencia}


def elegibilidad_publica(publicacion, vendedor):
    """¿Puede mostrarse al público como oferta? Devuelve (elegible, motivos_de_no_elegibilidad)."""
    motivos = []
    if vendedor["estado_validacion"] != "validado":
        motivos.append(f"vendedor {vendedor['estado_validacion']}")
    elif vendedor["tipo"] not in TIPOS_PERMITIDOS:
        motivos.append(f"tipo de vendedor no permitido ({vendedor['tipo']})")
    if publicacion.get("estado_validacion") != "validado":
        motivos.append(f"publicación {publicacion.get('estado_validacion')}")
    if vendedor.get("tipo") == "distribuidor_autorizado" and not vendedor.get("validacion_humana"):
        if "vendedor pendiente" not in motivos:
            motivos.append("distribuidor sin validación humana")
    if publicacion.get("condicion_producto") == "no_nuevo":
        motivos.append("producto no nuevo")
    return (not motivos), motivos


def estado_publicacion(vendedor, condicion_producto=None):
    """Estado de validación de la publicación a partir de su vendedor (y de si el producto es nuevo)."""
    if condicion_producto == "no_nuevo":
        if vendedor.get("revision_individual"):
            return "pendiente", vendedor["motivo"]
        return "rechazado", "producto no nuevo"
    if vendedor["estado_validacion"] == "rechazado":
        return "rechazado", vendedor["motivo"]
    if vendedor["estado_validacion"] == "validado":
        return "validado", "vendedor validado: " + vendedor["metodo"] + " (nivel " + str(vendedor.get("nivel_evidencia")) + ")"
    return "pendiente", vendedor["motivo"]
