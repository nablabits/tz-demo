## Trapuzarrak app registro de cambios
***
### v62, Ene31
  * **Nuevo:** página de inicio renovada con un montón de datos útiles.
  * **Nuevo:** el menu se encuentra ahora en la parte superior.
  * **Nuevo:** muchos iconos añadidos para mejorar la comprensión.
  * **Nuevo:** página de facturación y banco que refleja los movimientos entre
    ambos

### v61, Ene 19
  * **Nuevo:** nuevo módulo de gastos (accesible solo por *superusers*).
  * **Mejora:** al añadir clientes, la ciudad se puede dejar en blanco. Se ha
    mejorado visualmente el formulario de añadir/editar cliente también.
  * **Mejora:** se han normalizado las etiquetas de las prendas a través de la
    *app.*
  * **Mejora:** las prendas producidas están ahora escondidas detrás de un
    botón.
  * **Mejora:** hay pequeños cambios en el *look* de la vista del pedido.
  * **Mejora:** pequeñas mejoras en el funcionamiento y visuales.
  * **Bug:** se ha corregido el error al añadir prendas a la producción y la
    manipulación general de las prendas. Tampoco se muestran ya las prendas con
    nombre *descuento.*
  * **Bug:** ya no se pueden borrar prendas que estén en algún pedido.

### v60, Ene 13
  * **Nuevo:** Nueva vista de filtro para los tickets y el editor de prendas.
  * **Nuevo:** Vista de la cola de producción para la tablet.
  * **Nuevo:** ahora al hacer click en una factura se ve el ticket de la misma.

### v59, Ene 8
  * **Nuevo:** las vista de las facturs ahora es más completa.
  * **Mejora:** ahora *kaiku* se llama *jakea.*

### v58, Ene 6
  * **Nuevo:** Los pedidos regulares ya se pueden facturar también.
  * **Nuevo:** nueva tabla para movimientos del banco (accesible desde la vista
     admin).
  * **Nuevo:** ya se puede fijar el precio de las prendas al enviarlas a un
    ticket.
  * **Nuevo:** Número de pedidos en las pestañas.
  * **Nuevo:** añadido tipo de prenda *varios.*
  * **Mejora:** Las ventas rápidas se han rediseñado incluyendo un selector de
    prendas y una caja de búsqueda.
  * **Bug:** al mandar una prenda al ticket ya se pueden añadir los decimales.
  * **Bug:** al editar una prenda la descripción desaparecía, ahora ya no.
  * **Bug:** Mejorada la efectividad de prendas duplicadas.

#### v56-57, Ene 4
  * **Nuevo:** añadidos nuevos tipos de prenda.

#### v55, Dic 31
  * **Nuevo:** Cola de producción.
  * **Nuevo:** Módulo de ventas.
  * **Bug:** aún más refinado el duplicado de prendas.
  + **Bug:** pequeño error en la vista  de previsión con el cambio de año.

#### v54, Dic 15
  * **Nuevo:** las prendas en los pedidos tienen un nuevo atributo, *Stock*,
    para diferenciarlas de producción nueva.
  * **Mejora:** se ha añadido la cuenta de tiempos registrados en cada tarjeta
    de la vista de previsión.
  * **Mejora:** varias mejoras en el funcionamiento interno de la *app*
  * **Bug:** refinado el duplicado de prendas.

#### v53, Dic 9
  * **Nuevo:** ahora se muestra un icono de *trabajando en segundo plano*
    mientras se procesan los datos.
  * **Mejora:** se han volcado todos los tiempos al nuevo modelo y se ha borrado
    el antiguo
  * **Mejora:** La previsión por semanas ahora muestra los pedidos de TZ.
    Se ha eliminado la vista de lista de pedidos activos también.
  * **Bug:** Ahora se muestra la confirmación al eliminar algún elemento.
  * **Bug:** Se vuelven a mostrar los tiempos añadidos en la lista de pedidos.
  * **Bug:** Mejorada la efectividad de pedidos duplicados.
  * **Bug:** Tampoco se pueden duplicar clientes ahora.
  * **Bug:** Los mensajes de error al editar o añadir datos no se mostraban
    correctamente, ahora sí.

#### v52, Dic 1
  * **Bug:** Ya no se pueden duplicar prendas.
  * **Bug:** El icono de enviar prenda a pedido solía desaparecer, ahora se
    queda en su sitio.

#### v51, Nov 29
  * **Nuevo:** añadida barra de progreso a la lista de pedidos.
  * **Bug:** ya no se pueden crear pedidos duplicados.
  * **Bug:** Corregido el error en los estados dentro de cada pedido.
  * **Bug:** Los pedidos de stock no se ordenaban correctamente, ahora sí.

#### v50, Nov 29
  * **Nuevo:** Nueva vista por semanas para prever la carga de trabajo.
  * **Nuevo:** ahora hay una barra de progreso que muestra gráficamente el
    estado
  * **Nuevo:** la lista de pedidos ahora muestra un color en función de la
    fecha de entrega.
  * **Mejora:** se han renombrado los estados posibles (entre paréntesis el progreso):
    * Preparando -> Corte (25%).
    * En proceso-> Confección (50%).
    * Acabado -> Remate (75%).
  * **Mejora:** Se ha añadido el número de pedido activos.
  * **Mejora:** He reducido el tamaño de la cabecera y el menu lateral para que
    haya más sitio para la información importante.
  * **Mejora:** Cuando el filtro no devuelve resultados, ahora se muestra un
    mensaje.

#### v48, Nov 24
  * **Nuevo:** Las prendas que se añaden a un pedido ahora tienen un atributo
    *arreglo* para diferenciarlas de las nuevas.
  * **Mejora:** cada prenda en la lista de prendas añadidas a un pedido ahora
    tiene un icono con detalles relativos a esa prenda.
  * **Mejora:** el desplegable de añadir prendas dentro de un pedido ahora
    ordena las prendas por tipo de prenda.
  * **Mejora:** ahora el editor de prendas muestra un icono en cada prenda
    externa.
  * **Mejora:** el editor de prendas indica si hay un filtro activo en la vista.
  * **Bug:** arreglos menores en fallos.

#### v47, Nov 23
  * **Nuevo:** ahora se pueden enviar prendas directamente a pedidos (solo
    activos).
  * **Mejora:** el filtro añadido en la v43 ahora se puede aplicar a más campos
    (tipo de prenda y acabado).
  * **Mejora:** font awesome pro y varias mejoras visuales.
  * **Mejora:** los detalles de las prendas en el editor de prendas ahora
    aparecen en un desplegable.
  * **Mejora:** ahora se muestra un mensaje de éxito al crear o editar
    elementos (clientes, pedidos, prendas...) por si falla el cierre de la
    ventana.
  * **Mejora:** el desplegable de añadir prendas dentro de un pedido ahora
    ordena las prendas por nombre.
  * **Mejora:** la página de prendas ahora se llama editor de prendas.
  * **Bug:** La lista de clientes no mostraba el número de pedidos hechos por
    cada cliente.
  * **Bug:** los clientes no se eliminaban de forma correcta.
  * **Bug:** Solucionado el problema al añadir comentarios.
  * **Bug:** los nuevos pedidos no redirigían correctamente al nuevo pedido.

#### v46, Nov 20
  * **Bug:** la lista de pedidos entregados mostraba más de 10 elementos, ahora
    ya no.
  * **Mejora:** El desplegable de la v45, ahora se abre al hacer click en
    cualquier punto de la vista.
  * **Mejora:** pequeñas mejoras en la unificación de vistas.

#### v45, Nov 16
  * **Nuevo:** El editor de prendas tiene un nuevo atributo, *externo*, que
    las excluye de la producción de trapuzarrak.
  * **Nuevo:** Desplegable con los detalles de cada prenda en cada pedido
    (tiempos y descripción).
  * **Nuevo:** El editor de prendas tiene un nuevo cuadro de ayuda.

#### v44, Nov 14
  * **Bug:** las tallas de las prendas ahora admiten hasta 6 caracteres.
  * **Bug:** los pedidos entregados se ordenan por fecha de entrega de más reciente hacia
    atrás.
  * **Bug:** la caja de búsqueda en prendas era inútil y se ha eliminado.
  * **Bug:** arreglos menores en fallos.
  * **Mejora:** varias mejoras visuales.

#### v43, Nov 13
  * **Bug:** corregido el error en guardado de las prendas en los pedidos.
  * **Mejora:** mejoras en el tamaño y los botones.
  * **Nuevo:** ahora se puede filtrar por nombre el listado de prendas (pronto
    se podrá por tipo de prenda).

#### v42, Nov 12
  * **Nuevo:** vista de administrador más completa.

#### v41, Nov 11
  * **Nuevo:** Este *Changelog*.
  * **Nuevo:** las prendas se definen independientemente.
  * **Nuevo:** ahora cada prenda en un pedido lleva sus propios tiempos.
  * **Actualización:** Font awesome 5.5
  * **Mejora:** el tamaño de algunas fuentes se ha reducido para que haya más
    información en la pantalla.
