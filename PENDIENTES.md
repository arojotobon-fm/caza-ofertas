# Pendientes · Cazadores de Ofertas

Lista para próximas actualizaciones (se publican por bloques para ahorrar créditos de Netlify).

## Frecuencia de actualización del catálogo y de "¿Está barato hoy?" (decidida por Ana, 22 nov 2026)
- **Semana del Black Friday (23–29 nov):** actualizar **cada 2 días** (≈ 3 publicaciones, 45 créditos de Netlify). La primera publicación incluye la corrección del texto duplicado del Verificador (6c96110).
- **Después del Black Friday:** actualizar **una vez por semana, los viernes**.
- Cada actualización = lectura de las tiendas + publicación con autorización de Ana (15 créditos por publicación).
- El historial diario de precios es aparte: corre solo en GitHub a las 6:17 a. m. y no gasta créditos (pendiente confirmar su primera corrida automática el 23 nov).

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
- [x] Validación de vendedores: opción B con controles (aprobada 22 nov).
- [x] Estructura de clasificación aprobada; umbrales NO activos hasta tener historial por categoría.
- [ ] Revisar y aprobar la rama correccion-radar (corrección urgente del Radar publicado).
- [ ] Validación humana de 8 posibles tiendas oficiales y de los vendedores de Alkosto (320 publicaciones pendientes).
- [ ] Confirmar grupos empresariales de Homecenter, Jumbo/Metro y Olímpica antes de admitirlos.
- [ ] Etapa 2: conectar la página al modelo v2 y construir el panel administrativo.

## Decisiones aplazadas
- [ ] API oficial de Mercado Libre (registro gratuito de desarrollador; revisar condiciones).
- [ ] Programas de afiliados (Falabella, Éxito, Alkosto, Amazon) y aviso de comisión en la página.

## Hoja de ruta después del Black Friday (aprobada 22 nov 2026)
Fuente: `docs/ESPECIFICACION_COMPARADOR_MULTITIENDA.md` (comparador simétrico multitienda). Se hace **por etapas**, respetando `PRINCIPIOS.md`.
Las cifras de tráfico de ese documento no están verificadas: no se guardan como datos del proyecto sin fuente comprobada.

### Etapa A — Costo total real (primero)
- [ ] **Envío**: costo, tiempo de entrega y recogida en tienda por publicación; el ahorro se calcula con envío incluido.
- [ ] **Instalación**: cobros adicionales en electrodomésticos y muebles.
- [ ] **Garantía y devoluciones**: si es del fabricante o de la tienda, y condiciones de devolución.

### Etapa B — Mercado Libre, solo tiendas oficiales verificadas
- [ ] Revisar condiciones de la API oficial de Mercado Libre (registro de desarrollador).
- [ ] Admitir solo tiendas oficiales verificadas una por una (identidad, NIT y nombre del vendedor), igual que Corbeta, Olímpica, Jumbo y Flamingo.

### Etapas siguientes (cada una con aprobación)
- [ ] 5 rangos de precio en celulares.
- [ ] Calzado y belleza con tiendas oficiales verificadas (Adidas, Samsung, Cruz Verde…), una por una.
- [ ] Marketplaces internacionales (Amazon, Temu, AliExpress, Shein) solo cuando podamos calcular el costo total en pesos (dólares, envío e impuestos de importación).
- [ ] Permitir que la persona elija qué comercios comparar en cada categoría.

### Decisiones ya tomadas sobre ese documento
- Disponibilidad: no se guarda inventario, pero solo se comparan publicaciones **disponibles al momento** (evita "ofertas" que no se pueden comprar).
- ¡Hagamos Cuentas! es una herramienta complementaria, no un veredicto.


## Experiencia pública — decisiones aprobadas (22 nov 2026)
- [x] Conservar el panel principal, los personajes y la frase **«No cazamos descuentos. Cazamos la verdad detrás de los precios»**.
- [x] Mantener el buscador como entrada principal: el usuario solicita investigar un producto concreto.
- [x] Conservar **Explorar por categoría** como filtro de investigación, no como catálogo público.
- [x] Retirar de la navegación pública **«¿Está barato hoy? Mira dónde cuesta menos»**, el catálogo/listado masivo del Radar y la sección pública **Comparador**. La comparación multitienda permanece como proceso interno que sustenta los veredictos.
- [x] Retirar **«¿No está en la lista? Búscalo en todas las tiendas»** y sus enlaces de búsqueda externa.
- [x] Conservar el historial de precios, la comunidad **«Únete a los Cazadores que reportan»**, **«Apoya este proyecto»** y **«¡Hagamos Cuentas!»**.
- [x] Ajustar el flujo de categorías para que al elegir una categoría enfoque la búsqueda de un producto dentro de ella, sin desplegar listados de catálogo.
- [x] La vista previa de la rama quedó publicada por Netlify para revisión técnica; la validación visual final sigue pendiente si hay diferencias de navegador/dispositivo.
- **Regla:** no modificar main, no fusionar ni desplegar a producción sin aprobación expresa de Ana.


## Selección editorial semanal de la portada — decisión de Ana (22 nov 2026)
- [x] Eliminar los contadores públicos de productos «más baratos», «mismo precio» y «sin comparar» como métricas de volumen.
- [x] No mostrar listados generales ni catálogos de productos. Los productos sin comparación y los de mismo precio quedan fuera de las selecciones públicas.
- [ ] Mostrar una selección semanal de **15 productos**: gangazos reales demostrables y descuentos inflados demostrables («¡Cazamos una mentira!»). Cada ficha abre el detalle con el producto, el veredicto y las pruebas.
- [ ] Mostrar una segunda selección semanal de **mínimo 5 productos** cuya misma referencia esté comprobablemente más barata en otra tienda. Cada ficha abre su comparación y evidencia.
- [ ] Actualizar ambas selecciones una vez por semana. La selección debe ser editorial y revisada; no llenar cupos con productos sin pruebas.
- **Regla de evidencia:** no llamar «descuento inflado» a un precio solo porque el precio anterior no coincide con otras tiendas. Debe existir respaldo verificable (historial o evidencia equivalente). Si no lo hay, no se publica como mentira.
- **Regla de publicación:** los conteos de productos iguales o sin comparar no se muestran en portada ni generan secciones públicas.


### Estado de evidencia editorial revisado (22 nov 2026)
- El modelo v2 contiene 130 comparaciones: 4 completas, 31 limitadas y 95 sin comparación pública.
- De las 4 completas, tres muestran precios iguales entre comercios; una presenta una diferencia pequeña (0,8 %) y no alcanza por sí sola los criterios de una selección editorial de 5.
- Por tanto, las selecciones de 15 investigaciones y mínimo 5 comparaciones no se rellenan con datos incompletos ni se publican como si estuvieran verificadas. Se mantienen pendientes de evidencia suficiente.
