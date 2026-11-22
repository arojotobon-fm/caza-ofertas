#!/usr/bin/env python3
"""Captura selectiva de fichas públicas de Alkosto.

No modifica el catálogo ni publica información. La captura es una candidata
para revisión humana; los datos ausentes no se infieren.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

TIENDA = "Alkosto"
DOMINIOS_PERMITIDOS = {"alkosto.com", "www.alkosto.com"}
PATRON_CODIGO = re.compile(r"\bCódigo\s*:?\s*</?[^>]*>\s*([A-Z0-9][A-Z0-9._/-]{2,})", re.I)


class DatosHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.json_ld = []
        self.textos = []
        self._leyendo_json = False
        self._bloque_json = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag.lower() == "meta":
            clave = attrs.get("property") or attrs.get("name")
            contenido = attrs.get("content")
            if clave and contenido:
                self.meta[clave.lower()] = contenido.strip()
        if tag.lower() == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self._leyendo_json = True
            self._bloque_json = []

    def handle_data(self, data):
        if self._leyendo_json:
            self._bloque_json.append(data)
        if data.strip():
            self.textos.append(data.strip())

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._leyendo_json:
            contenido = "".join(self._bloque_json).strip()
            if contenido:
                try:
                    self.json_ld.append(json.loads(contenido))
                except json.JSONDecodeError:
                    pass
            self._leyendo_json = False
            self._bloque_json = []


def validar_url(url):
    partes = urlsplit(url)
    if partes.scheme != "https" or (partes.hostname or "").lower() not in DOMINIOS_PERMITIDOS:
        raise ValueError("Solo se permiten URL HTTPS de Alkosto.")
    if not partes.path or partes.path == "/":
        raise ValueError("Debes indicar la URL directa de un producto.")
    return url


def buscar_producto(datos):
    encontrados = []

    def recorrer(obj):
        if isinstance(obj, dict):
            tipo = obj.get("@type", "")
            tipos = tipo if isinstance(tipo, list) else [tipo]
            if any(str(t).lower().rsplit("/", 1)[-1] == "product" for t in tipos):
                encontrados.append(obj)
            for valor in obj.values():
                recorrer(valor)
        elif isinstance(obj, list):
            for elemento in obj:
                recorrer(elemento)

    for bloque in datos:
        recorrer(bloque)
    return encontrados[0] if encontrados else {}


def extraer_codigo(textos):
    texto = " ".join(textos)
    coincidencia = PATRON_CODIGO.search(texto)
    return coincidencia.group(1).strip() if coincidencia else None


def capturar(url):
    validar_url(url)
    solicitud = Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; CazaOfertas/1.0)",
        "Accept-Language": "es-CO,es;q=0.9",
    })
    with urlopen(solicitud, timeout=20) as respuesta:
        url_final = respuesta.geturl()
        validar_url(url_final)
        html = respuesta.read().decode("utf-8", errors="replace")

    parser = DatosHTML()
    parser.feed(html)
    producto = buscar_producto(parser.json_ld)
    ofertas = producto.get("offers", {})
    if isinstance(ofertas, list):
        ofertas = ofertas[0] if ofertas else {}
    if not isinstance(ofertas, dict):
        ofertas = {}
    marca = producto.get("brand")
    if isinstance(marca, dict):
        marca = marca.get("name")

    codigo = extraer_codigo(parser.textos)
    return {
        "tienda": TIENDA,
        "url_solicitada": url,
        "url_final": url_final,
        "fecha_captura_utc": datetime.now(timezone.utc).isoformat(),
        "nombre": producto.get("name") or parser.meta.get("og:title") or parser.meta.get("twitter:title"),
        "marca": marca,
        "modelo": producto.get("model"),
        "mpn": producto.get("mpn"),
        "gtin": producto.get("gtin13") or producto.get("gtin12") or producto.get("gtin14") or producto.get("gtin"),
        "sku": producto.get("sku"),
        "codigo_publicado": codigo,
        "tipo_codigo": "pendiente_de_confirmar" if codigo else None,
        "precio": ofertas.get("price"),
        "moneda": ofertas.get("priceCurrency"),
        "disponibilidad": ofertas.get("availability"),
        "fuente_identificacion": "JSON-LD" if producto else "metadatos",
        "requiere_revision_humana": True,
        "nota": "La tienda puede cargar datos mediante JavaScript; los campos nulos requieren revisión manual.",
    }


def main():
    parser = argparse.ArgumentParser(description="Captura selectiva de una ficha de producto de Alkosto.")
    parser.add_argument("url", help="URL HTTPS directa de un producto de Alkosto")
    parser.add_argument("--capturar", action="store_true", help="Autoriza la consulta de la URL indicada")
    parser.add_argument("--salida", help="Ruta opcional para guardar el resultado JSON")
    args = parser.parse_args()
    if not args.capturar:
        print("Modo seguro: no se consultó ninguna página. Usa --capturar para autorizar la captura.")
        return 0
    try:
        resultado = capturar(args.url)
    except (ValueError, HTTPError, URLError, TimeoutError) as error:
        print(f"No fue posible capturar la ficha: {error}", file=sys.stderr)
        return 1
    texto = json.dumps(resultado, ensure_ascii=False, indent=2)
    if args.salida:
        with open(args.salida, "w", encoding="utf-8") as archivo:
            archivo.write(texto + "\n")
        print(f"Resultado guardado en: {args.salida}")
    else:
        print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
