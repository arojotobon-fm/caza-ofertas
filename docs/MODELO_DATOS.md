# Modelo de datos v2 · Cazadores de Ofertas

Carpeta: `data/v2/`. Archivos JSON (la página sigue siendo estática; no hace falta base de datos todavía).
La versión v1 (`data/ofertas.json`, `data/historial.json`) **sigue intacta** y es la que usa la página publicada.

## 1. Entidades y relaciones

```
grupos_empresariales 1──* comercios 1──* publicaciones *──1 productos (referencias)
                                           │  └──* precios (uno por condición de pago)
                                           │  └──* historial (observaciones de precio)
                                           │  └──* reportes (Netlify Blobs, por id de publicación)
                         vendedores 1──────┘
comparaciones: calculadas por producto a partir de publicaciones + precios (no se editan a mano)
```

| Archivo | Qué guarda | Clave |
|---|---|---|
| `comercios.json` | Comercios y **grupos empresariales** (Alkosto, Ktronix y Alkomprar = `colcomercio`). Estado de admisión. | `id` |
| `vendedores.json` | Quién vende realmente: nombre, **tipo**, comercio donde aparece, estado y evidencia. | `id` |
| `productos.json` | La **referencia** única (marca, códigos de modelo, especificaciones). Una referencia aparece una sola vez aunque esté en varias tiendas. | `id` (`prod-…`) |
| `publicaciones.json` | Cada producto **en un comercio**: enlace, imagen, comercio, vendedor, estado de validación, fecha de verificación. Conserva el `id` de v1. | `id` |
| `precios.json` | Un precio por **condición**: `contado`, `tarjeta`, `medio_pago`, `financiado`, `plan`. El "antes" tachado se guarda como `precio_anunciado_antes`, **no** como prueba de descuento. | `id` |
| `historial.json` | Observaciones `{publicacion_id, condicion, fecha, monto}`. Permite mínimo/máximo por comercio y condición. | — |
| `comparaciones.json` | Resultado del comparador: comercios independientes, estado (`completa` ≥ 3 · `limitada` = 2 · `sin_comparacion`), diferencia y ahorro por publicación, y qué publicaciones se excluyeron por vendedor. | `producto_id` |
| `candidatas_revision.json` | Pares que **podrían** ser el mismo producto y necesitan revisión humana. | — |
| `mapa_ids_v1.json` | Id v1 → publicación y condición. Mantiene ligados los reportes de la comunidad. | id v1 |
| `informe_migracion.json` | Conteos y verificación de no pérdida. | — |

## 2. Estados y tipos

**Vendedor · tipo:** `retailer` · `subsidiaria_verificada` · `tienda_oficial_fabricante` · `tercero_marketplace`.
**Vendedor y publicación · estado:** `validado` · `pendiente` · `rechazado`.
**Referencia · estado:** `sin_verificar` (una sola publicación) · `agrupada_automatica` (el comparador la unió) · `verificada` (revisada por una persona).

Una publicación solo podrá entrar al Radar cuando: vendedor `validado` de un tipo permitido **y** publicación `validado` **y** precio verificado hace menos de 12 h (si no, se muestra la advertencia aprobada).

## 3. Reglas del comparador (implementadas en `scripts/comparador.py`)

1. Misma marca canónica (se unifican alias como BLACK & DECKER = BLACK+DECKER).
2. Mismo **código de modelo exacto**. Si solo coincide por prefijo (AF141 ↔ AF141LAA), queda como **candidata**; nunca se agrupa sola.
3. Ninguna especificación en conflicto: pulgadas, RAM, almacenamiento, capacidad, combo, producto no nuevo. Si una publicación no informa un dato, el par queda **candidato**.
4. Los procesadores (Ryzen 5 7520U, Core 3 100U…) **no** cuentan como referencia.
5. Comercios del mismo grupo empresarial cuentan como **uno**.
6. Solo se comparan precios de la **misma condición**. El precio de referencia de una publicación es la mediana del mejor precio de *cada otro* grupo empresarial.
7. Las publicaciones con vendedor rechazado no entran en la comparación (quedan anotadas en `excluidas_por_vendedor`).

## 4. Validación: decisión pendiente de aprobación

La migración **no valida nada automáticamente**. Para el vendedor guarda la evidencia del listado (por ejemplo, *"vendido por Falabella"*), pero lo deja en `pendiente`.

**Impacto:** con esta regla, el Radar v2 quedaría vacío hasta que alguien valide vendedores. Hay dos opciones:
- **A (más estricta):** validación humana de cada vendedor. Sería un trabajo de una sola vez por vendedor, no por producto, porque son solo 2 retailers y 7 posibles tiendas oficiales.
- **B:** validar automáticamente cuando el listado dice explícitamente que vende el propio comercio, y dejar en revisión humana solo las tiendas oficiales de fabricante.

## 5. Panel administrativo (propuesta, no implementado)

- **Acceso:** página `/admin` servida por Netlify, con acciones protegidas por una función (`netlify/functions/admin-*.mjs`). La sesión se valida en el servidor con una contraseña guardada como **variable de entorno de Netlify** (solo su huella), una cookie firmada `HttpOnly` y un límite de intentos. **Nada secreto en el frontend.**
- **Escritura:** la función hace commits al repositorio con un token de GitHub de alcance mínimo (solo `caza-ofertas`), también guardado como variable de entorno. Cada cambio queda en el historial y es reversible.
- **Pantallas de la primera versión:** cola de vendedores pendientes · pares candidatos (unir / no unir) · aprobar o rechazar publicaciones · consulta de reportes.
- Alternativa que hay que evaluar: un CMS sobre GitHub (tipo Decap) con inicio de sesión de GitHub. Es menos código, pero menos adaptado a este flujo.
