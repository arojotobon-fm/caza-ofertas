# Especificación Técnica: Comparador Multitienda Simétrico (Enfoque en Oferta Real vs. Oferta Inflada)

## 1. Objetivo y Regla de Alcance
Evolucionar el modelo `data/v2/` (`productos.json`, `publicaciones.json`, `precios.json`, `historial.json`, `comercios.json`, `vendedores.json`, `identidades_corporativas.json`, `comparaciones.json` y `config_clasificacion.json`) hacia un **comparador simétrico de todos contra todos (N contra N)** para Colombia[cite: 2], centrado estrictamente en determinar **si un descuento favorece realmente al comprador (oferta real) o si es una oferta inflada**[cite: 1].

* **Fuera de alcance — No rastrear stock ni inventario:** El sistema **no** debe capturar ni validar disponibilidad de unidades (`disponible` vs. `agotado`) ni inventarios por talla. El usuario verificará la existencia del producto directamente en la tienda de destino a través del enlace de la publicación.
* **Modelo neutral sin tienda ancla:** Ningún comercio es el centro fijo del sistema; Falabella funciona solo como ejemplo referencial de cruce[cite: 2] y cada ítem en `productos.json`[cite: 1] actúa como nodo maestro para enfrentar en igualdad de condiciones a todos los comercios[cite: 2].
* **Continuidad con el repositorio actual:** Conservar compatibilidad con los respaldos históricos (`alk`, `exi`, `fal`, `jum`, `ktr`, `oli`)[cite: 1], las reglas de canal corporativo (`docs/REVISION_ALKOSTO_CANAL.md`, `tests/test_canal_corporativo.py`)[cite: 1], el motor de veredictos (`oferta-real`, `descuento-dudoso`, `cazamos-mentira`, `hagamos-cuentas`, `sin-pruebas`)[cite: 1] y las funciones de Netlify (`buscar.mjs`, `verificar.mjs`, `reportes.mjs` y `netlify/functions/lib/`)[cite: 1].

---

## 2. Comercios Objetivo y Tipos de Canal (`data/v2/comercios.json`)
Actualizar `comercios.json`[cite: 1] para registrar los comercios con catálogo virtual y compra en línea en Colombia según su tipo de canal y cobertura referencial[cite: 2] (manteniendo también los comercios ya integrados como Jumbo y Olímpica[cite: 1]):

| Comercio | Dominio | Tipo de canal | Categorías referenciales del catálogo | Tráfico mensual (sep 2026) |
| :--- | :--- | :--- | :--- | :--- |
| **Falabella**[cite: 2] | `falabella.com.co` (referencia)[cite: 2] | Retail / Marketplace[cite: 2] | Celulares, TV, computadores, consolas, audífonos, electrodomésticos, patinetas/cámaras/drones, calzado, belleza, muebles, accesorios moda[cite: 2] | Comercio base de ejemplo[cite: 2] |
| **Mercado Libre**[cite: 2] | `mercadolibre.com.co`[cite: 2] | Marketplace[cite: 2] | Todas: celulares, TV, computadores, audífonos, electrodomésticos, calzado, belleza, muebles, cámaras y drones[cite: 2] | 14,42 M (Semrush)[cite: 2] |
| **Amazon**[cite: 2] | `amazon.com`[cite: 2] | Marketplace internacional[cite: 2] | Electro, tecnología, consolas, audífonos, belleza[cite: 2] | Top 3 Similarweb (ago 2026)[cite: 2] |
| **Temu**[cite: 2] | `temu.com`[cite: 2] | Marketplace internacional[cite: 2] | Accesorios, electrónicos económicos, hogar[cite: 2] | 13,51 M (Semrush)[cite: 2] |
| **AliExpress**[cite: 2] | `aliexpress.com`[cite: 2] | Marketplace internacional[cite: 2] | Celulares, audífonos, relojes inteligentes, accesorios[cite: 2] | 9,26 M (Semrush)[cite: 2] |
| **Homecenter**[cite: 2] | `homecenter.com.co`[cite: 2] | Retail hogar[cite: 2] | Muebles, closets y armarios, electrodomésticos[cite: 2] | 7,18 M (Semrush)[cite: 2] |
| **Éxito**[cite: 2] | `exito.com`[cite: 2] | Retail / supermercado[cite: 2] | Electro, electrodomésticos, calzado, belleza, muebles[cite: 2] | 6,00 M (Semrush)[cite: 2] |
| **Alkosto**[cite: 2] | `alkosto.com`[cite: 2] | Retail electro[cite: 2] | Celulares, televisores, computadores, neveras, lavadoras, consolas, colchones[cite: 2] | 5,81 M (Semrush)[cite: 2] |
| **Shein**[cite: 2] | `shein.com`[cite: 2] | Moda online[cite: 2] | Accesorios moda, calzado[cite: 2] | 5,15 M (Semrush)[cite: 2] |
| **Ktronix**[cite: 2] | `ktronix.com`[cite: 2] | Retail tecnología[cite: 2] | Celulares, computadores, televisores, consolas[cite: 2] | 2,30 M (Semrush)[cite: 2] |
| **Adidas Colombia**[cite: 2] | `adidas.co`[cite: 2] | Marca directa[cite: 2] | Calzado: tenis mujer y hombre[cite: 2] | 2,29 M (Semrush)[cite: 2] |
| **Samsung**[cite: 2] | `samsung.com`[cite: 2] | Marca directa[cite: 2] | Celulares, televisores, electrodomésticos, neveras, lavadoras[cite: 2] | 3,36 M (Semrush)[cite: 2] |
| **Cruz Verde**[cite: 2] | `cruzverde.com.co`[cite: 2] | Droguería / belleza[cite: 2] | Dermocosmética, skincare, perfumes[cite: 2] | 3,06 M (Semrush)[cite: 2] |

*Nota de verificación:* La columna de categorías es referencial; el pipeline debe validar la presencia real de cada categoría o marca en cada sitio[cite: 2].

---

## 3. Dimensiones de Análisis para Evaluar el Beneficio Real al Comprador
Ampliar `precios.json`, `publicaciones.json`, `vendedores.json` e `identidades_corporativas.json`[cite: 1] enfocándose exclusivamente en los factores que determinan si el precio anunciado es un ahorro genuino o una oferta engañosa:

1. **Precio y referencia histórica (`data/v2/precios.json` y `data/v2/historial.json`):**[cite: 1]
   * Contrastar el precio de lista tachado contra el precio con descuento para exactamente el mismo modelo y contra su histórico propio y del mercado[cite: 1, 2], detectando alzas previas artificiales ("oferta inflada").
   * Clasificar por rangos de precio, aplicando los 5 rangos definidos en la categoría de celulares[cite: 2].
2. **Condiciones de descuento y letra pequeña (`data/v2/precios.json` y `netlify/functions/lib/verificar.mjs`):**[cite: 1]
   * Calcular el porcentaje real de descuento[cite: 2] frente al historial (`historial.json`)[cite: 1].
   * Separar el precio a todo medio de pago del precio exclusivo con tarjeta de la tienda o aliados, además de registrar cuotas sin interés y cupones aplicables[cite: 2] (alimentando el veredicto `hagamos-cuentas`[cite: 1]).
3. **Costo total con envío e instalación (`data/v2/publicaciones.json`):**[cite: 1, 2]
   * Capturar costo de envío (incluyendo envíos internacionales en plataformas como Amazon, Temu, AliExpress o Shein)[cite: 2], tiempo estimado de entrega, recogida en tienda[cite: 2] y cobros adicionales de instalación en electrodomésticos o muebles[cite: 2] para evitar descuentos aparentes que se pierden en el flete.
4. **Tipo de vendedor y originalidad (`data/v2/vendedores.json` e `identidades_corporativas.json`):**[cite: 1]
   * Identificar si vende el comercio propio / marca directa (1P) o un tercero en marketplace (3P)[cite: 2] para comparar peras con peras y respaldar la autenticidad en categorías sensibles (audífonos/relojes, belleza y accesorios de moda)[cite: 2].
5. **Garantía y devoluciones (`data/v2/publicaciones.json`):**[cite: 1, 2]
   * Registrar si la garantía es directa del fabricante o de la tienda y las condiciones de devolución[cite: 2], claves al comparar precios entre tiendas locales y plataformas internacionales[cite: 2].
6. **Surtido y experiencia del catálogo (`data/v2/productos.json` y `publicaciones.json`):**[cite: 1]
   * Medir presencia de marcas ancla por categoría[cite: 2] y calidad de la ficha (filtros, fotos, especificaciones técnicas, calificación promedio y reseñas)[cite: 2] para detectar publicaciones ambiguas o sin respaldo (`sin-pruebas`[cite: 1]).

---

## 4. Matriz de Categorías, Marcas Clave y Grupos de Competencia (`scripts/taxonomia.py` y `data/v2/config_clasificacion.json`)
Reestructurar la taxonomía (`img/cat/` y `scripts/taxonomia.py`)[cite: 1] en las 9 categorías siguientes, definiendo en `config_clasificacion.json`[cite: 1] qué atributos extraer y qué comercios se cruzan entre sí en cada grupo[cite: 2]:

| Categoría | Variables críticas para comparar precio y valor | Marcas prioritarias a detectar | Comercios sugeridos para cruce simétrico |
| :--- | :--- | :--- | :--- |
| **1. Celulares**[cite: 2] | Precio por rango (5 rangos), modelos exactos, cuotas sin interés[cite: 2] | Apple, Samsung[cite: 2] | Falabella, Mercado Libre, Alkosto, Ktronix, Éxito, Samsung[cite: 2] |
| **2. Televisores, computadores, consolas**[cite: 2] | Precio del mismo modelo, tamaño / especificaciones técnicas, garantía[cite: 2] | Modelos homologados por referencia[cite: 2] | Falabella, Alkosto, Ktronix, Mercado Libre, Éxito, Amazon[cite: 2] |
| **3. Audífonos, parlantes y relojes inteligentes**[cite: 2] | Precio, originalidad y verificación del vendedor (1P vs. 3P)[cite: 2] | Sonos, Apple, Samsung[cite: 2] | Falabella, Mercado Libre, Amazon, Alkosto, AliExpress[cite: 2] |
| **4. Electrodomésticos, neveras, lavadoras y secadoras**[cite: 2] | Capacidad, precio, costo de instalación y envío[cite: 2] | Shark, Dyson, Ninja[cite: 2] | Falabella, Alkosto, Homecenter, Éxito, Mercado Libre[cite: 2] |
| **5. Patinetas eléctricas, cámaras y drones**[cite: 2] | Surtido de referencias, precio, garantía[cite: 2] | Marcas del catálogo activo[cite: 2] | Falabella, Mercado Libre, Amazon, Alkosto[cite: 2] |
| **6. Calzado (tenis mujer y hombre)**[cite: 2] | Precio comparado contra la tienda oficial de la marca[cite: 2] | Adidas, Nike, Hoka, Puma, Veja, New Balance, On Running[cite: 2] | Falabella, Adidas Colombia, Mercado Libre, Éxito, Shein[cite: 2] |
| **7. Belleza (perfumes, dermocosmética, skincare coreano, maquillaje)**[cite: 2] | Precio, autenticidad / originalidad del vendedor[cite: 2] | Chanel, Dior, Kerastase, Carolina Herrera, La Roche Posay, The Ordinary, Rabanne[cite: 2] | Falabella, Cruz Verde, Éxito, Mercado Libre, Amazon[cite: 2] |
| **8. Muebles (sillas de oficina, colchones, closets y armarios)**[cite: 2] | Precio, medidas, materiales, costo de envío e instalación[cite: 2] | Catálogo por tipo de mueble[cite: 2] | Falabella, Homecenter, Alkosto, Éxito, Mercado Libre[cite: 2] |
| **9. Accesorios moda**[cite: 2] | Precio, marcas disponibles, originalidad del vendedor[cite: 2] | Tissot, Casio, Michael Kors, Pandora, Ray Ban, Guess, Tommy Hilfiger[cite: 2] | Falabella, Mercado Libre, Éxito, Amazon, Shein[cite: 2] |

---

## 5. Plan de Implementación en el Repositorio
Aplicar esta especificación respetando `PRINCIPIOS.md` y `METODOLOGIA_CLASIFICACION.md` en el siguiente orden[cite: 1]:

1. **Documentación y Esquema (`docs/MODELO_DATOS.md`):** Documentar los nuevos campos de `comercios.json`, `precios.json`, `publicaciones.json` y `config_clasificacion.json` manteniendo retrocompatibilidad con `data/v2/` y dejando explícita la exclusión de campos de stock[cite: 1].
2. **Catálogos y Configuración (`data/v2/comercios.json` y `data/v2/config_clasificacion.json`):** Registrar los nuevos comercios[cite: 2], sus tipos de canal[cite: 2], los 5 rangos de celulares[cite: 2], los diccionarios de marcas[cite: 2] y los grupos de tiendas comparables por categoría[cite: 2].
3. **Pipeline Python (`scripts/normalizar.py`, `scripts/taxonomia.py`, `scripts/comparador.py`, `scripts/validacion.py`):**[cite: 1]
   * Normalizar precios a COP, homologar marcas y extraer especificaciones técnicas clave (capacidad, medidas, referencias)[cite: 1, 2].
   * Calcular en `comparaciones.json`[cite: 1] el posicionamiento de precio real de cada tienda frente al histórico y frente al resto del mercado (precio general, precio con tarjeta, envío, garantía y calidad de ficha)[cite: 1, 2].
4. **Motor de Verificación, API y Frontend (`netlify/functions/lib/verificar.mjs`, `comparar.mjs` e `index.html`):**[cite: 1]
   * Integrar el cruce multitienda en la lógica de veredictos para detectar si una oferta es real frente al mercado o está inflada frente a su histórico/competencia, permitiendo al usuario seleccionar libremente qué comercios comparar en cada categoría[cite: 1, 2].
5. **Pruebas Automatizadas (`tests/` y `tests/js/`):** Actualizar `test_comercios_nuevos.py`, `test_comparador.py`, `test_taxonomia.py`, `test_validacion.py` y `buscar.test.mjs` para validar las nuevas reglas sin dependencias de inventario[cite: 1].