## Trapuzarrak app registro de cambios
***
### v??, date
  * **Nuevo:** Ahora los pedidos aceptan un parámetro grupo para clientes
  particulares que hacen un pedido para su grupo.
  * **Nuevo:** ya podemos llevar el control de los prepagos y las facturas
  pendientes de cargo.
  * **Nuevo:** Ahora llevamos el control de las distintas fases de los pedidos.
  * **Nuevo:** Podemos añadir descuentos a los pedidos.
  * **Nuevo:** se puede añadir un numero de lote a las prendas de stock que vendamos
  que nos servirá para saber la estancia media.
  * **Nuevo:** se ha añadido un control de stock a las prendas
  * **Mejora:** Las fases dentro de los pedidos se han adaptado para cuadrar con
  la vista kanban.
  * **Mejora:** los tickets ahora imprimen la fecha y la hora.
  * **Mejora:** ahora el cuadro de diálogo de añadir/editar pedido tiene el campo
  notas colapsado para que se vea completo.
  * **Bug:** al editar un pedido ya no hay que volver a introducir el nombre del
  cliente.

### v83, Dic 6
  * **Mejora:** ya se pueden añadir clientes escribiendo el nombre directamente
  en la caja.

### v82a, Dic 3
  * **Mejora:** cuando no se están midiendo tiempos (usuario *voyeur*) el icono
  de usuario es un agente secreto.
  * **Bug:** se ha aumentado el margen de los tickets.
  * **Bug:** Traje de niña ahora es generico en lugar de generica como solia
  aparecer en los tickets.

### v82, Nov 25
  * **Nuevo:** ahora la vista principal muestra los ratios de tiempos registrados.
  * **Mejora:** Se pueden añadir notas a clientes y a prendas desde la vista de
  la tablet.
  * **Mejora:** se ha añadido un botón para seguir añadiendo prendas al ticket
  si se ha pulsado previamente facturar.
  * **Mejora:** la vista de administrador ahora filtra los clientes por nombre.
  * **Bug:** ahora los tiempos de producción excluyen de la cuenta las prendas
  de stock.
  * **Bug:**  ya funciona correctamente el checkbox de prendas externas del
  selector de prendas.
  * **Bug:** los pedidos de tz no pueden tener prendas de stock o externas.

### v81a, Nov 18
  * **Mejora:** ahora la vista de ticket se agranda al Facturar.
  * **Mejora:** añadido un botón para volver al inicio tras facturar un ticket.
  * **Mejora:** ahora hay más espacio en la parte inferior de la app para que la
  información no se quede escondida debajo de la barra.
  * **Bug:** ya aparecen todas las lineas en la impresión de tickets con muchos
  elementos.
  * **Bug:** las lineas adicionales en el ticket ahora aparecen donde deberían
  aparecer (a continuación).

### v81, Nov 13
  * **Nuevo:** Ahora podemos imprimir tickets de venta.
  * **Mejora:** La barra de progreso es más intuitiva ahora.
  * **Bug:** el objetivo anual se ha recalculado para que cuadre a 72.000€

### v80, Sept 29
  * **Bug:** el botón de prepago ha vuelto del más allá y además ahora se envia
  una copia oculta al mail de administración.
  * **Bug:** al editar tiempos de prenda, la app recuerda los tiempos que ya
  había introducidos.
  * **Bug:** el *link* al cliente dentro del pedido ya vuelve a funcionar como
  debe.

### v79, Sept 19
  * **Nuevo:** ahora tenemos una estimación del tiempo que nos va a llevar
    producir cada pedido.
  * **Nuevo:** ya se pueden editar los tiempos de trabajo directamente sobre las
    prendas.
  * **Nuevo:** los pedidos no confirmados se muestran aparte.
  * **Bug:** ahora al abrir un proyecto en todoist la pagina recarga correctamente
    la información.

### v78, Ago 18
  * **Nuevo:** Nueva vista detallada de pedido con integración con todoist.
  * **Nuevo:** Nueva vista con los últimos horarios registrados.
  * **Mejora:** La barra de gastos ahora muestra la cantidad gastada en lugar de
    la diferencia.
  * **Nuevo:** Nuevo API endpoint para los horarios.

### v77, Jun 11
  * **Nuevo:** Barra de *status* para comprobar la hora de inicio de sesión.
  * **Mejora:** Algunos mensajes se han traducido al español.
  * **Bug:** ahora la hora de cierre se muestra correctamente.

### v76, Jun 3
  * **Nuevo:** ahora se puede hacer *logout* desde la cola de produccion en la tablet.
  *  **Bug:** ya no pueden añadir por error horas por debajo de 15 minutos.

### v75, May27
  * **Nuevo:** *frontend* para apuntar las horas diarias.

### v74, May 17
  * **Nuevo:** nuevo modelo para registrar las horas laborales.

### v73, May 11
  * **Nuevo:** ahora se pueden añadir comentarios exprés desde la vista kanban.
  * **Mejora:** añadido un *spinner* mienras se procesan los cambios de status.
  * **Bug:** la vista por defecto ahora es kanban (para todos los botones).
  * **Bug:** testeadas las nuevas características al completo.

### v73.beta1, May 9
  * **Mejora:** añadido un *spinner* mientras se procesan los cambios de fecha.

### v73.beta, May 1
  * **Nuevo:** nueva vista kanban (en proceso de testeo aun).
  * **Mejora:** Actualización del framework.

### v72, Abr 5
  * **Nuevo:** nueva barra de gastos para comparar con los ingresos.

### v71, Abr 3
  * **Nuevo:** Ahora las prendas se añaden desde el selector de prendas dentro
    de la vista del pedido.
  * **Mejora:** La barra de objetivo se ha comprimido para alojar toda la
  previsión. Ahora el objetivo queda en el centro (en lugar de a 3/4 como antes).
  * **Mejora:** Ahora el interruptor de pedidos no confirmados se oculta cuando
    todo está confirmado.
  * **Mejora:** los pedidos pendientes de pago ahora se ordenan por fecha de
    entrega (antes era por fecha de entrada).
  * **Mejora:** en la vista de pedidos ahora el titulo de cada pedido es el
    cliente.
  * **Mejora:** los pedidos con el 100% prepagado ya no se muestran en pendientes.
  * **Bug:** Se han eliminado el error que añadía la prenda *Predeterminado*
    y el que daba error al eliminar una prenda.

### v70, Mar 27
  * **Bug:** la barra de progreso en la página de inicio no se correspondía con
    la realidad.
  * **Mejora:** La lista de pedidos ahora muestra el número de pedido.

### v69, Mar 26
  * **Nuevo:** ahora los pedidos pueden estar a la espera de confirmación.
  * **Mejora:** se ha recolocado el botón de volver a lista de pedidos.
  * **Mejora:** ahora se pueden guardar y completar tiempos en un solo *clik*
    en la cola de producción.
  * **Mejora:** la vista principal ahora muestra el progreso del año, es un
    marcador en directo.
  * **Bug:** los pedidos de tz ya no se pueden facturar.
  * **Bug:** las prendas de stock no necesitan tiempos.

### v68, Mar 19
  * **Nuevo:** Ahora las ventas express se pueden convertir en pedidos regulares
  para añadirles arreglos.
  * **Mejora:** ya se puede añadir el CP a la venta express después de crearla.
  * **Mejora:** Ha desaparecido la casilla de arreglo, ya que los arreglos los
  marcamos con la prenda *varios arreglo.*
  * **Bug:** los elementos de stock son solo producción nuestra, por lo que
  ahora las prendas externas ya no podrán ser de stock.
  * **Bug:** ya no aparecen las prendas externas en la cola de producción.
  * **Bug:** las prendas externas ya no muestran los tiempos, entre otras cosas
  porque no tienen.


### v67, Mar 9
  * **Nuevo:** nueva REST API para sacar estadísticas sobre los datos
    almacenados

### v66, Mar 8
  * **Nuevo:** ahora se pueden añadir prendas desde el filtro aplicado.
  * **Nuevo:** ahora hay un botón siempre visible en la vista de pedido para
    volver a la lista de pedidos.
  * **Nuevo:** las ventas express se pueden eliminar desde la vista.
    `[order.delete() for order in Order.obsolete.all()]`
  * **Bug:** al cambiar de status ya no se actualiza la fecha (excepto si es
    para entregar)
  * **Bug:** se ha refinado la efectividad de las prendas duplicadas.
  * **Bug:** se han eliminado los provedores del desplegable de añadir/editar
    pedido

### v65, Feb 21
  * **Nuevo:** ahora los prepagos se añaden de forma independiente y hay opción
    de mandar un email al cliente.
  * **Mejora:** se ha reubicado el botón de editar pedido.
  * **Mejora:** en la cola de producción ahora aparece el nombre del cliente en
    lugar del pedido.
  * **Bug:** la lista de clientes al añadir pedido no muestra el cliente express
    (reservado para ventas anónimas) y está ordenada por nombre ahora.

### v64, Feb 5
  * **Bug:** los ingresos negativos y los gastos en metálico afectan ahora al
    balance con el banco.

### v63, Feb 1
  * **Bug:** han vuelto a casa las cantidades pendientes que habían huido.

### v62, Ene31
  * **Nuevo:** página de inicio renovada con un montón de datos útiles.
  * **Nuevo:** el menu se encuentra ahora en la parte superior.
  * **Nuevo:** muchos iconos añadidos para mejorar la comprensión.
  * **Nuevo:** página de facturación y banco que refleja los movimientos entre
    ambos.

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
