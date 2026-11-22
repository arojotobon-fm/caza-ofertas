# Cómo revisar la Etapa 1

Rama: `etapa-1-modelo-datos` (no está publicada; `main` y el sitio no cambiaron).

## Ver los cambios
- En GitHub: https://github.com/arojotobon-fm/caza-ofertas/compare/main...etapa-1-modelo-datos
- **No abras un "Pull request" todavía**: Netlify crea una vista previa por cada PR y eso consume créditos.

## Qué revisar primero
1. `docs/DIAGNOSTICO.md`: estado actual y reglas que hoy se incumplen.
2. `docs/MODELO_DATOS.md`: modelo v2, validación opción B aprobada y separación técnica/pública.
3. `docs/METODOLOGIA_CLASIFICACION.md`: propuesta de clasificación con parámetros por aprobar.
4. `data/v2/informe_migracion.json`: conteos y verificación de no pérdida (`errores_verificacion: []`).
5. `data/v2/candidatas_revision.json`: pares que una persona debe decidir.

## Reproducir (opcional, en un computador con Python 3)
```
python3 -m unittest discover -s tests -v      # 37 pruebas: comparador, validación, pendientes, condiciones de pago y datos migrados
python3 scripts/migrar_v1_a_v2.py             # regenera data/v2 y verifica que no se pierda nada
```

## Único cambio visible en la página
Los textos de las etiquetas ahora son los aprobados: "DESCUENTO DE VITRINA" y "POSIBLE ERROR DE PRECIO". Solo se verán cuando se publique la rama.
