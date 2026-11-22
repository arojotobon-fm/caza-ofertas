# Diagnóstico técnico · Cazadores de Ofertas

Revisión del repositorio en la rama `main` (commit `859082b`, publicado el 21 nov 2026).

## 1. Cómo funciona hoy

| Componente | Archivo | Qué hace realmente |
|---|---|---|
| Página | `index.html` (59 KB, todo en un archivo) | HTML + CSS + JS sin framework. Carga `data/ofertas.json`, `data/historial.json` y `/api/reportes`. Calcula en el navegador el radar, la oferta destacada, el top, el comparador (filtros por texto, subcategoría, tienda, tipo de oferta), favoritos (localStorage) y los votos de la comunidad. |
| Catálogo | `data/ofertas.json` (564 KB) | Lista **plana** de 868 registros. Cada registro mezcla producto, publicación, vendedor (solo dentro del texto `nota`), precio y clasificación. |
| Historial | `data/historial.json` (106 KB) | `{id: {n, t, p: {fecha: precio}}}`. 855 registros con un solo día (21 nov). Solo guarda precio de contado. |
| Reportes | `netlify/functions/reportes.mjs` | GET devuelve resumen; POST `{id, voto: si/no, precio?}`. Netlify Blobs con lectura consistente. Retención 72 h, una huella (hash de IP + id + sal) por producto cada 6 h. **No guarda IP.** |
| Configuración | `netlify.toml`, `package.json` | Publica la raíz, funciones en `netlify/functions`, dependencia `@netlify/blobs`. Cada push a `main` publica en producción automáticamente. |
| Generación de datos | **fuera del repositorio** | El script que lee las tiendas y arma `ofertas.json` estaba solo en el entorno de trabajo de Claude. Ya quedó copiado como `scripts/legacy_build_v1.py`. |

## 2. Auditoría de datos (`data/ofertas.json`)

| Dato | Valor |
|---|---|
| Productos | 868 (Falabella 320 · Alkosto 328 · Éxito 220) |
| Con comparación | 54 (37 con 2 tiendas · 17 con 3 tiendas) |
| Clasificación | sin 814 · justo 28 · vitrina 15 · buena 11 |
| Registros que son "variante con tarjeta" | 13 (todos en el top) |
| Vendedor externo identificado en la nota | **284** (Falabella 166 · Éxito 118) |
| Vendedor de Alkosto | **No se capturó** en ningún producto |

## 3. Brechas frente a las reglas aprobadas

Lo publicado hoy **incumple** varias reglas. No se corrige en producción sin aprobación.

1. **Vendedores (regla 3.2):** 284 productos de vendedores externos siguen en el catálogo y **1 está en el top** (#13, audífonos Lenovo en Éxito). Además, ningún producto de Alkosto tiene vendedor identificado.
2. **Condiciones de pago (3.5):** 12 de las 15 ofertas del top son **precio con tarjeta de la tienda** comparado contra **precio de contado** de las otras tiendas. Aunque la tarjeta muestra el aviso "Solo pagando con…", el "ahorro real" mezcla condiciones.
3. **Comparación de 3 comercios (3.3):** 10 de las 15 del top se comparan con una sola tienda más (2 comercios). Se presentan como "oferta real" sin decir que la comparación es limitada.
4. **Coincidencias aproximadas (3.3):** el emparejamiento por código de modelo acepta prefijos (`AF141` = `AF141LAA`). Puede ser el mismo producto con sufijo regional, pero hoy se agrupa sin revisión.
5. **Umbrales sin aprobación (5.D):** los cortes 30 % / 15 % / 8 % / 50 % los propuso Claude y nunca se documentaron para aprobación.
6. **Textos:** el frontend dice `DESCUENTO INFLADO` y `POSIBLE ERROR`; los aprobados son `DESCUENTO DE VITRINA` y `POSIBLE ERROR DE PRECIO`. *(Corregido en esta rama.)*
7. **Reportes:** el voto "Ya no / cambió" agrupa dos casos ("ya no está" y "precio cambiado"). El backend no los distingue, aunque guarda el precio visto cuando la persona lo escribe.
8. **Historial:** guarda un precio por registro sin condición de pago ni comercio separados; no permite mínimo/máximo por comercio.
9. **Procedencia del dato:** el generador estaba fuera del repositorio; no había forma de reproducir cómo se calculó cada oferta.

## 4. Lo que sí está bien y se conserva

- La identidad visual y el panel aprobados.
- La función de reportes (privacidad, enfriamiento de 6 h, retención de 72 h).
- Los identificadores de producto: los reportes de la comunidad están ligados a ellos, así que la migración **los conserva**.
- La advertencia de 12 horas.
- No se encontraron precios inválidos ni identificadores duplicados.
