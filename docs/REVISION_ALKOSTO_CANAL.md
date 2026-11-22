# Revisión de las 320 publicaciones de Alkosto: evidencia corporativa del canal (22 nov 2026)

Estado: **ensayo**. Los resultados en `data/v2/` NO se reescribieron. Para reproducir el ensayo:

```
python3 scripts/migrar_v1_a_v2.py --salida /tmp/v2ensayo --chequeo data/v2/chequeos/alkosto-2026-11-22.json
```

## Qué se hizo
1. `data/v2/identidades_corporativas.json`: la identidad maestra es Colombiana de Comercio S.A. (NIT 890.900.943-1). Sus alias documentados son Alkosto, Ktronix, Alkomprar, Corbeta S.A., Alkosto S.A. y Colombiana de Comercio. Cada alias tiene su fuente y su fecha. Solo se acepta coincidencia exacta.
2. Canal Alkosto: `validado` con nivel `canal_corporativo`. La base es la cláusula «Portafolio de productos» del contrato de compraventa, que nombra a Colombiana de Comercio como proveedor «salvo que se indique lo contrario en el banner principal del producto». Hay que revalidar antes del 2027-02-20.
3. Ktronix y Alkomprar quedan `pendiente`: falta verificar la misma cláusula en sus sitios. Hoy no tienen publicaciones en el catálogo.
4. Revisión de ficha por ficha (`data/v2/chequeos/alkosto-2026-11-22.json`). Las 320 fichas se leyeron desde el navegador. En cada una se revisaron tres cosas:
   - el banner principal (`.new-container__main-product__mini-banner`), en texto e imágenes;
   - si la ficha tiene texto de otro vendedor o proveedor;
   - si el producto es reacondicionado, de exhibición o de una sección especial (según el H1 y la ruta de categorías).

   Una de las fichas se comparó además con la página ya renderizada, y el resultado fue el mismo.
5. Reglas (`scripts/validacion.py`, `validar_por_canal`):

   | Situación en la ficha | Resultado |
   |---|---|
   | Otro vendedor o proveedor | pendiente |
   | Banner con contenido | pendiente |
   | Reacondicionado, exhibición o sección especial | pendiente, con revisión individual |
   | No se pudo leer la ficha | pendiente |
   | Evidencia del canal vencida | pendiente |
   | Ninguna de las anteriores | retailer validado, con nivel, fecha, fuente y revalidación |

6. `distribuidor_autorizado`: nunca se valida automáticamente. Sin `validacion_humana` no es elegible para el público. Una empresa del grupo que vende en un marketplace ajeno también queda como distribuidor pendiente.
7. Las referencias en revisión (DuraPro BLBD210 y AF141LAA) no se comparan en público. Esto alinea el modelo v2 con la decisión del 21 nov que ya aplica la página.

## Resultado del ensayo
- Publicaciones de Alkosto: 320 pasan a validadas y 0 quedan pendientes por excepción.
- En las 320 fichas no hubo banner con contenido, texto de otro vendedor, sección especial ni errores de lectura.
- Elegibles para el público: pasan de 251 a 571.
- Comparaciones públicas: antes había 3 limitadas y 9 sin comparación. Con el ensayo quedan 1 completa, 8 limitadas y 3 sin comparación.
- Filas aptas para el Radar: pasan de 6 a 19.
- Filas más baratas que la referencia: Éxito Purifry (0,8 %), Éxito LG 55" (2,6 %) y **Alkosto Ninja BN801 (3,6 %, nueva)**.
- Errores de verificación sin pérdida: ninguno.

## Límites
- Ninguna de las fichas revisadas mostró una excepción, así que el detector nunca se ha visto disparar con un caso real de Alkosto. Su comportamiento está cubierto con casos sintéticos en `tests/test_canal_corporativo.py`.
- La regla de «un solo grupo» (Alkosto, Ktronix y Alkomprar) está probada, pero hoy no cambia ninguna cifra porque el catálogo solo tiene publicaciones de Alkosto.
