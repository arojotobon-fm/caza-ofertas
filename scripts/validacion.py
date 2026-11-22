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

TIPOS_PERMITIDOS = {"retailer", "subsidiaria_verificada", "tienda_oficial_fabricante"}
METODO_AUTO = "automatica_coincidencia_exacta"


def _parece_tienda_oficial(nombre_n, marca_producto):
    if "OFICIAL" in nombre_n:
        return True
    tokens = set(re.findall(r"[A-Z0-9+]+", nombre_n))
    # solo la marca DEL PRODUCTO publicado; una marca cualquiera en el nombre (p. ej. "Tecno optima") no basta
    return bool(marca_producto) and (marca_producto in tokens or nombre_n.startswith(marca_producto + " "))


def clasificar_vendedor(comercio_id, nombre_listado, marca_producto, fecha_evidencia, fuente):
    """Devuelve el registro de validación del vendedor de UNA publicación.

    Siempre incluye la evidencia; 'validado_en' solo se llena cuando la validación es efectiva.
    """
    evidencia = {"texto_listado": nombre_listado, "fuente": fuente, "fecha": fecha_evidencia}
    if not nombre_listado or not str(nombre_listado).strip():
        return {"tipo": None, "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "El listado no identifica al vendedor.", "evidencia": evidencia}
    n = norm_text(nombre_listado)
    oficiales = NOMBRES_OFICIALES.get(comercio_id, set())
    if n in oficiales:
        return {"tipo": "retailer", "estado_validacion": "validado", "metodo": METODO_AUTO, "validado_en": fecha_evidencia,
                "motivo": f"El listado identifica expresamente a '{nombre_listado}' como vendedor y coincide exactamente con el comercio.",
                "evidencia": evidencia}
    if any(o in n for o in oficiales):
        return {"tipo": None, "estado_validacion": "pendiente", "metodo": None, "validado_en": None,
                "motivo": "Nombre parecido al del comercio, pero no idéntico: requiere revisión humana.", "evidencia": evidencia}
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
    if publicacion.get("condicion_producto") == "no_nuevo":
        motivos.append("producto no nuevo")
    return (not motivos), motivos


def estado_publicacion(vendedor, condicion_producto=None):
    """Estado de validación de la publicación a partir de su vendedor (y de si el producto es nuevo)."""
    if condicion_producto == "no_nuevo":
        return "rechazado", "producto no nuevo"
    if vendedor["estado_validacion"] == "rechazado":
        return "rechazado", vendedor["motivo"]
    if vendedor["estado_validacion"] == "validado":
        return "validado", "vendedor validado: " + vendedor["metodo"]
    return "pendiente", vendedor["motivo"]
