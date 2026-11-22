"""Taxonomía aprobada por Ana Marcela (22 nov 2026).

Clasifica cada producto en grupo y subcategoría a partir de su nombre.
Lo que no encaja se marca como oculto (no se borra de los datos).
"""
import re

GRUPOS = {
    "Tecnología": ["Computación", "TV y video", "Zona gamer", "Cámaras y drones", "Audio",
                   "Smartwatch y anillos", "Consolas", "Smart home", "Movilidad"],
    "Celulares y accesorios": ["Celulares y accesorios"],
    "Electrohogar": ["Refrigeración", "Electrodomésticos de cocina", "Cocina", "Lavado y planchado",
                     "Climatización", "Tecnobelleza", "Aspirado y limpieza"],
    "Tenis y zapatos": ["Zapatos de mujer", "Zapatos de niña", "Zapatos de niño", "Zapatos de hombre"],
    "Belleza y salud": ["Perfumes", "Maquillaje", "Cuidado capilar", "Cuidado de la piel", "Skincare coreano"],
}
# Marcas de belleza y salud aprobadas (lista enviada por Ana, 22 nov 2026).
MARCAS_BELLEZA = ["Benefit", "Carolina Herrera", "Chanel", "Clinique", "Dior", "Dolce&Gabbana", "Estee Lauder",
                  "Eucerin", "Fenty", "Isdin", "Kerastase", "La Roche Posay", "Lancome", "Loreal professionel",
                  "MAC Cosmetics", "Medicube", "Montblanc", "Olaplex", "Rabanne", "The Ordinary", "Vichy", "Versace"]

R = lambda s: re.compile(s, re.I)
# El orden importa: lo más específico primero.
REGLAS = [
    (None, "Medicamentos y alimentos", R(r"tabletas|jarabe|ibuprofeno|acetaminof|naproxeno|galletas|vita ?c\b|noraver|tiamina|complejo b|alerfast")),
    ("Celulares y accesorios", "Celulares y accesorios", R(r"^\W*(celular|smartphone|tel[eé]fono celular)\b|\biphone \d|galaxy [asz]\d+ ")),
    ("Tecnología", "Smart home", R(r"robot aspirador|smart home|alexa|echo dot|google home|\bnest\b|bombillo inteligente|enchufe inteligente|cerradura inteligente|c[aá]mara de seguridad")),
    ("Electrohogar", "Aspirado y limpieza", R(r"aspirador|aspiradora|trapeador|hidrolavadora|limpiador a vapor|mopa")),
    (None, "Mascotas", R(r"bebedero|comedero|mascota|\bperros?\b|\bgatos?\b")),
    (None, "Juguetes", R(r"\blego\b|mu[ñn]eca|peluche|hot ?wheels|barbie|juguete|rompecabezas|juego de mesa|bloques|playmobil|\bnerf\b|figura de acci|set de construcci|nave espacial|para niñ[oa]s")),
    ("Tecnología", "Consolas", R(r"\bconsola\b|playstation ?5 (slim|pro|digital)|nintendo switch|\bswitch (2|oled|1\.1|lite)|xbox series|steam deck")),
    ("Tecnología", "Zona gamer", R(r"gamer|gaming|\bps[2-5]\b|play ?station|xbox|nintendo|\bwii\b|\bpsp\b|joystick|dualsense|videojuego|pin google play|\bswitch\b")),
    ("Tecnología", "Smartwatch y anillos", R(r"smartwatch|reloj inteligente|smart ?band|\bwatch\b|anillo inteligente|galaxy ring|amazfit|mi band|fitbit|forerunner|vivoactive|venu|instinct|\breloj\b")),
    ("Tecnología", "Audio", R(r"aud[ií]fono|parlante|altavoz|\bbuds|airpods|freebuds|diadema|torre de sonido|micr[oó]fono|tocadiscos|equipo de sonido|sistema de audio|barra de sonido|soundbar")),
    ("Tecnología", "Computación", R(r"port[aá]til|laptop|computador|macbook|ipad|\btablet\b|idea ?tab|monitor|impresora|teclado|mouse|disco (duro|s[oó]lido)|\bssd\b|router|chromebook|all in one|stylus|memoria usb")),
    ("Tecnología", "TV y video", R(r"televisor|\btv\b|qled|oled|proyector|roku|chromecast|fire tv|soporte para televisor|control remoto")),
    ("Tecnología", "Cámaras y drones", R(r"c[aá]mara|\bdrones?\b|gopro|insta360|\bdji\b")),
    ("Tecnología", "Movilidad", R(r"patineta|scooter|bicicleta el[eé]ctrica|monopat[ií]n|hoverboard")),
    ("Celulares y accesorios", "Celulares y accesorios", R(r"celular|smartphone|iphone|galaxy [asz]\d|redmi|xiaomi|motorola|moto g|\bhonor\b|\boppo\b|\bvivo\b|tecno spark|\bzte\b|cargador|cable usb|lightning|power ?bank|forro|funda|protector de pantalla|vidrio templado|porta ?celular|soporte de celular|\b5g\b")),
    ("Electrohogar", "Refrigeración", R(r"nevera|refrigerador|congelador|nevec[oó]n|minibar|vinoteca")),
    ("Electrohogar", "Tecnobelleza", R(r"secador(?! de ropa)|plancha (de |para )?(cabello|pelo)|alisador|rizador|ondulador|estilizador|moldeador|airwrap|flexstyle|airstyle|afeitadora|m[aá]quina de afeitar|patillera|depiladora|recortadora|corta ?pelo|barbera|cepillo (dental )?el[eé]ctrico|oral-?b|irrigador|remington")),
    ("Electrohogar", "Climatización", R(r"ventilador|aire acondicionado|calentador|calefactor|purificador de aire|humidificador|deshumidificador|enfriador de aire")),
    ("Electrohogar", "Electrodomésticos de cocina", R(r"licuadora|freidora|air ?fryer|cafetera|horno|microondas|batidora|procesador|extractor|sanduchera|wafflera|arrocera|olla (el[eé]ctrica|multifuncional)|hervidor|tostadora|exprimidor|molino|chocolatera|dispensador de agua|nutribullet|\bninja\b|parrilla el[eé]ctrica|vaporera")),
    ("Electrohogar", "Lavado y planchado", R(r"lavadora|secadora de ropa|lavaseca|centr[ií]fuga|plancha|vaporizador")),
    ("Electrohogar", "Cocina", R(r"estufa|campana|cubiertos|\bollas?\b|sart[eé]n|bater[ií]a de cocina|cuchillo|vajilla")),
]
# Si el nombre no dice nada, se usa la subcategoría que traía la tienda.
POR_SUB = {"Televisores": ("Tecnología", "TV y video"), "Videojuegos": ("Tecnología", "Zona gamer"),
           "Celulares": ("Celulares y accesorios", "Celulares y accesorios")}


def clasificar(nombre, sub_tienda=None):
    """Devuelve (grupo, subcategoria). grupo None = no entra al catálogo (se oculta)."""
    nombre = nombre or ""
    if re.search(r"oferta destacada", nombre, re.I):
        return None, "Sin nombre de producto"
    for grupo, sub, rx in REGLAS:
        if rx.search(nombre):
            return grupo, sub
    return POR_SUB.get(sub_tienda, (None, "Sin clasificar"))


def aplicar(rec):
    grupo, sub = clasificar(rec.get("nombre"), rec.get("sub"))
    rec["grupo"], rec["subcat"] = grupo, sub
    rec["oculto"] = grupo is None
    return rec
