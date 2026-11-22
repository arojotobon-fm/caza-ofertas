"""Normalización de marcas, códigos de modelo y especificaciones a partir del nombre publicado.

Todo lo que sale de aquí es una *extracción automática* del texto de la tienda:
nunca se marca como verificado. Sirve para proponer coincidencias, no para aprobarlas.
"""
import re
import unicodedata

# --- marcas: alias -> forma canónica -------------------------------------------------
BRAND_ALIASES = {
    "BLACK+DECKER": "BLACK+DECKER", "BLACK & DECKER": "BLACK+DECKER", "BLACK&DECKER": "BLACK+DECKER",
    "BLACK AND DECKER": "BLACK+DECKER", "BLACKDECKER": "BLACK+DECKER",
    "HOLSTEIN HOUSEWARES": "HOLSTEIN", "SAMSUNG ELECTRONICS": "SAMSUNG", "LG ELECTRONICS": "LG",
    "APPLE INC": "APPLE", "XIAOMI MI": "XIAOMI", "REDMI": "XIAOMI",
}
KNOWN_BRANDS = sorted({
    "SAMSUNG", "LG", "SONY", "XIAOMI", "HUAWEI", "APPLE", "MOTOROLA", "LENOVO", "HP", "ASUS", "ACER", "DELL",
    "TCL", "HISENSE", "KALLEY", "CHALLENGER", "PANASONIC", "PHILIPS", "OSTER", "NINJA", "IMUSA", "HOLSTEIN",
    "BLACK+DECKER", "ELECTROLUX", "WHIRLPOOL", "MABE", "HACEB", "SAMURAI", "UMCO", "INSTANT", "CUISINART",
    "JBL", "SOUNDCORE", "ANKER", "BOSE", "AMAZFIT", "GARMIN", "REMINGTON", "CONAIR", "GAMA", "BABYLISS",
    "LEGO", "NINTENDO", "PLAYSTATION", "XBOX", "MICROSOFT", "ROBOROCK", "IROBOT", "DREAME", "ECOVACS",
    "NESPRESSO", "DOLCE GUSTO", "TOSHIBA", "HONOR", "OPPO", "REALME", "VIVO", "ZTE", "INFINIX", "TECNO",
}, key=len, reverse=True)

COLOR_WORDS = {
    "NEGRO", "NEGRA", "BLANCO", "BLANCA", "GRIS", "PLATEADO", "PLATEADA", "AZUL", "ROJO", "ROJA", "VERDE",
    "ROSADO", "ROSADA", "MORADO", "MORADA", "LILA", "DORADO", "DORADA", "CREMA", "BEIGE", "AMARILLO",
    "VIOLETA", "GRAFITO", "TITANIO", "NARANJA", "CAFE", "INOX", "ACERO",
}


def norm_text(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s.upper()).strip()


def canonical_brand(brand_field, name):
    """Marca canónica: primero el campo marca de la tienda, luego una marca conocida en el nombre."""
    b = norm_text(brand_field)
    if b:
        for alias, canon in BRAND_ALIASES.items():
            if b == alias or b.startswith(alias + " "):
                return canon
    n = norm_text(name)
    for alias, canon in BRAND_ALIASES.items():
        if alias in n:
            return canon
    if b and b.split()[0] in KNOWN_BRANDS:
        return b.split()[0]
    for k in KNOWN_BRANDS:
        if re.search(r"(?<![A-Z0-9])" + re.escape(k) + r"(?![A-Z0-9])", n):
            return k
    return b.split()[0] if b else ""


# --- códigos de modelo ---------------------------------------------------------------
_UNIT = re.compile(r"^\d+(\.\d+)?(L|LT|LTS|LITROS|GB|TB|W|WATTS|MAH|HZ|MP|PULGADAS|PULG|CM|MM|ML|OZ|V|K|P|G|PCS|PZ|PIEZAS|X\d+)$")
_GENERIC = re.compile(r"^(RTX|GTX|RAM|SSD|HDD|DDR|LPDDR|USB|IP|BT|WIFI|HDMI|QLED|OLED|UHD|FHD|LED|CORE|RYZEN|SERIE|SERIES|GEN|ANC|TWS|NFC|AMOLED)\d*[A-Z]?$")
_CPU = re.compile(r"^(I[3579]\d{3,5}[A-Z]*|\d{3,5}(U|H|HS|HX|K|KF|G|P)|N\d{3,4}|R[3579]\d{4}[A-Z]*|M[1-4](PRO|MAX)?|SNAPDRAGON\d*|HELIO[A-Z]?\d+|DIMENSITY\d+)$")


def model_codes(name):
    """Códigos alfanuméricos que parecen referencias del fabricante (sin unidades, CPU ni genéricos)."""
    out = set()
    for tok in re.findall(r"[A-Z0-9][A-Z0-9\-/\.]{2,}", norm_text(name)):
        t = re.sub(r"[\-/\.]", "", tok)
        if len(t) < 4 or not re.search(r"\d", t) or not re.search(r"[A-Z]", t):
            continue
        if _UNIT.match(tok) or _UNIT.match(t) or _GENERIC.match(t) or _CPU.match(t):
            continue
        out.add(t)
    return out


# --- especificaciones ----------------------------------------------------------------
def _num(x):
    return float(x.replace(",", "."))


def specs(name):
    """Especificaciones detectables en el nombre. Claves ausentes = no se pudo saber (no es lo mismo que 'no tiene')."""
    n = norm_text(name)
    sp = {}
    m = re.search(r"(\d{2,3})\s*(\"|''|”|PULGADAS|PULG\b|IN\b)", n)
    if m:
        sp["pantalla_pulgadas"] = int(m.group(1))
    m = re.search(r"(\d{1,2})\s*GB\s*(DE\s*)?RAM|RAM\s*(DE\s*)?(\d{1,2})\s*GB", n)
    if m:
        sp["ram_gb"] = int(m.group(1) or m.group(4))
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*TB\b", n)
    if m:
        sp["almacenamiento_gb"] = int(_num(m.group(1)) * 1024)
    else:
        for g in re.finditer(r"(\d{2,4})\s*GB\b", n):
            v = int(g.group(1))
            if v >= 32 and v != sp.get("ram_gb"):
                sp["almacenamiento_gb"] = v
                break
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(L|LT|LTS|LITROS)\b", n)
    if m:
        sp["capacidad_l"] = _num(m.group(1))
    if re.search(r"\+\s*(BARRA|AUDIF|PARLANTE|SOPORTE|BASE|MOUSE|TECLADO|MALETA|FORRO|VASO|CARGADOR|ESTUCHE)|\bCOMBO\b|\bKIT\b", n):
        sp["es_combo"] = True
    if re.search(r"REACONDICIONAD|OPEN ?BOX|\bUSADO\b|EXHIBICION", n):
        sp["condicion_producto"] = "no_nuevo"
    cols = sorted(w for w in re.findall(r"[A-Z]+", n) if w in COLOR_WORDS)
    if cols:
        sp["color"] = cols[0]
    return sp


# Especificaciones que, si difieren, hacen que NO sea el mismo producto.
SPEC_KEYS_STRICT = ("pantalla_pulgadas", "ram_gb", "almacenamiento_gb", "capacidad_l", "es_combo", "condicion_producto")
