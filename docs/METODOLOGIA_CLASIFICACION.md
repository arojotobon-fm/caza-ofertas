# Metodología de clasificación · ESTRUCTURA APROBADA (22 nov 2026) · UMBRALES NO ACTIVOS

> Decisión: se aprueban las 6 etiquetas y la estructura conceptual. No se activa ningún porcentaje hasta tener historial suficiente por categoría. Mientras tanto se muestran las diferencias reales en pesos y porcentaje, sin etiqueta.

La transferencia pide no inventar umbrales. Esta es la **estructura** que propongo. Los números son **parámetros por aprobar**; ninguno queda fijo en el código hasta que Ana los apruebe.

## Requisitos para clasificar (si no se cumplen → `Sin comparar`)
1. Publicación y vendedor validados.
2. Comparación **completa**: el mismo producto en ≥ 3 comercios independientes, en la **misma condición de pago**.
   - Con 2 comercios se muestra la diferencia como **"Comparación limitada"**, sin etiqueta de oferta.
3. Precio verificado hace menos de 12 h (si no, se clasifica, pero con la advertencia aprobada).

## Ahorro real
`ahorro_real = (referencia − precio) ÷ referencia`, donde `referencia` = mediana del mejor precio de contado de cada **otro** grupo empresarial. El "antes" tachado nunca entra en el cálculo.

## Etiquetas (parámetros por aprobar: P1 < P2 < P3)
| Etiqueta | Criterio propuesto |
|---|---|
| **Gangazo** | ahorro_real ≥ P2 **y** (cuando haya historial suficiente) precio ≤ mínimo de los últimos N días |
| **Buena oferta** | P1 ≤ ahorro_real < P2 |
| **Precio justo** | \|ahorro_real\| < P1 (precio igual al del mercado, aunque la tienda anuncie descuento) |
| **Descuento de vitrina** | la tienda anuncia un descuento ≥ D frente a su "antes", pero ahorro_real < P1 |
| **Posible error de precio** | ahorro_real ≥ P3. **No se publica como oferta** hasta que una persona lo confirme. |
| **Sin comparar** | no cumple los requisitos |

## Cómo propongo fijar los parámetros
No con cifras de intuición: medirlos con los datos propios durante 2 a 4 semanas de historial (distribución real de diferencias entre comercios por categoría) y fijar P1 y P2 por categoría, porque un 10 % en un televisor no equivale a un 10 % en una licuadora. Mientras tanto, el Radar puede mostrar el **ahorro real en pesos y en porcentaje** sin etiqueta.

## Hallazgo con los datos actuales
Con las reglas nuevas (vendedores externos excluidos, misma condición y coincidencia exacta), hoy hay **1 comparación completa** (cafetera Ninja ES601: el mismo precio en las 3 tiendas, es decir, precio justo) y **11 limitadas**, con diferencias de contado entre 0 % y 5,6 %. Las "ofertas" del radar actual venían casi todas de precios con tarjeta.
