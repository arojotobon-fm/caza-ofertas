# Pendientes · Cazadores de Ofertas

Lista para próximas actualizaciones (se publican por bloques para ahorrar créditos de Netlify).

## Próxima actualización de datos
- [ ] Agregar búsquedas de **Deportes** (bicicletas, mancuernas, tenis deportivos…) y **Mercado** (café, aceite, detergente…) para que esas categorías tengan productos.
- [ ] Revisar primero los productos que la comunidad reportó como "Ya no".

## Recursos que enviará Ana
- [ ] Ícono de **Juguetes** con el mismo estilo de los otros 9 (hoy Juguetes solo aparece en el filtro).
- [ ] (Opcional) versión simplificada de la insignia para íconos pequeños (< 40 px).

## Funciones por construir
- [ ] Botón **"Encontré una oferta"** para que la comunidad suba ofertas (se verifican antes de publicarse).
- [ ] **Alertas de precio** (requiere cuentas o notificaciones; hoy aparece como "Pronto").
- [ ] Gráfica del **historial**: se activa sola cuando haya 2 o más días de datos; frase "precio más bajo en 30 días" cuando haya 30 días.
- [ ] Tarea programada de revisión 2–3 veces al día (necesita el PC de Ana encendido con Chrome).
- [ ] "Cazadores de la semana" (reconocimiento a quienes más reportan).

## Etapa 1 (rama etapa-1-modelo-datos) — decisiones que necesita Ana
- [ ] Validación de vendedores: opción A (humana) u opción B (automática cuando el listado dice que vende el propio comercio). Ver docs/MODELO_DATOS.md §4.
- [ ] Aprobar la estructura de clasificación y cómo fijar los parámetros. Ver docs/METODOLOGIA_CLASIFICACION.md.
- [ ] Decidir si se corrige YA el Radar publicado (quitar el vendedor externo del top y marcar las comparaciones de 2 tiendas como "limitadas").
- [ ] Confirmar grupos empresariales de Homecenter, Jumbo/Metro y Olímpica antes de admitirlos.
- [ ] Etapa 2: conectar la página al modelo v2 y construir el panel administrativo.

## Decisiones aplazadas
- [ ] API oficial de Mercado Libre (registro gratuito de desarrollador; revisar condiciones).
- [ ] Programas de afiliados (Falabella, Éxito, Alkosto, Amazon) y aviso de comisión en la página.
