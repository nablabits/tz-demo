## Edit Order:
  *FrontEnd GET request*
    Trigger: `$('#order-edit').click(loadActionForm)`
    action: order-edit
    data-pk: order.pk

  *BackEnd GET response*
    context: order, form
    template: includes/edit/edit_order.html

  *FrontEnd POST request*
    Trigger: `$('#action-modal').on('submit', '.js-send-form', saveActionForm)`
    [Hidden inputs]
    action: order-edit
    pk: order.pk

  *BackEnd POST response*
    data[html_id]: #order-details
    context: form, order, items
    template: includes/order_details.html

## Add Item:
  *FrontEnd GET request*
    Trigger: `$('#order-details').on('click', '#order-add-item', loadActionForm)`
    action: order-add-item
    data-pk: order.pk

  *BackEnd GET response*
    context: order, form
    template: includes/add/add_item.html

  *FrontEnd POST request*
    Trigger: `$('#action-modal').on('submit', '.js-send-form', saveActionForm)`
    [Hidden inputs]
    action: order-add-item
    pk: order.pk

  *BackEnd POST response*
    data[html_id]: #order-details
    context: form, order, items
    template: includes/order_details.html

## Edit Item:
  *FrontEnd GET request*
    Trigger: `$('#order-details').on('click', '.js-item-edit', loadActionForm)`
    action: order-edit-item
    data-pk: item.pk

  *BackEnd GET response*
    context: item, form
    template: includes/edit/edit_item.html

  *FrontEnd POST request*
    Trigger: `$('#action-modal').on('submit', '.js-send-form', saveActionForm)`
    [Hidden inputs]
    action: order-edit-item
    pk: item.pk

  *BackEnd POST response*
    data[html_id]: #order-details
    context: form, order, items
    template: includes/order_details.html

## Delete item (define)

## Edit Item:
  *FrontEnd GET request*
    Trigger: `$('#order-details').on('click', '.js-item-edit', loadActionForm)`
    action: order-edit-item
    data-pk: item.pk

  *BackEnd GET response*
    context: item, form
    template: includes/edit/edit_item.html

  *FrontEnd POST request*
    Trigger: `$('#action-modal').on('submit', '.js-send-form', saveActionForm)`
    [Hidden inputs]
    action: order-edit-item
    pk: item.pk

  *BackEnd POST response*
    data[html_id]: #order-details
    context: form, order, items
    template: includes/order_details.html
