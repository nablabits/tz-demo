# base.html (root)

  * **block homeview** -> main.html

  * **block orderview** -> order_view.html
    * **include** order_status.html
    * **include** order_details.html
      * **include** action_buttons.html
    * **include** comments_list.html

  * **block customerview** -> customer_view.html

  * **block orders** -> orders.html
    * **include** search_box.html
    * **include** order_entry_element.html
    * **include** order_entry_element_delivered.html

  * **block listview** -> list_view.html
    * **include** search_box.html
    * **include** include_template
      * items_list.html
        * **include** action_buttons.html
      * customer_list.html
