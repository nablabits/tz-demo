# Template outline
A brief schema of template hierarchy.

### base.html (root)

  * **block homeview** -> main.html

  * **block orderview** -> order_view.html
    * **include** order_status.html
    * **include** order_details.html
      * **include** action_buttons.html
    * **include** comments_list.html

  * **block orderexpress** -> order_express.html
    * **include** includes/item_string.html
    * **include** includes/ticket.html
      * **include** includes/item_string.html
      * **include** action_buttons.html

  * **block customerview** -> customer_view.html

  * **block pqueueview** -> pqueue_manager.html
    * **include** includes/item_string.html
    * **include** includes/pqueue_list.html
      * **include** includes/item_string.html

  * **block orders** -> orders.html
    * **include** order_entry_element.html
    * **include** order_entry_element_delivered.html

  * **block kanban** -> kanban.html
    * **include** kanban_columns.html
      * **include** kanban_element.html

  * **block listview** -> list_view.html
    * **include** search_box.html
    * **include** include_template
      * items_list.html
        * **include** action_buttons.html
      * customer_list.html

  * **block invoices** -> invoices.html

  * **block pqueuetablet** -> pqueue_tablet.html
    * **include** includes/item_string.html

  * **block timetable_list** -> timetable_list.html
