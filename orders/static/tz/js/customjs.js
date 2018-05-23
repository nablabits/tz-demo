$(function () {

/* Functions */
  var getStatus = function () {
    /* Gets the current order status */
    var pk = $('#order_detail');
    $.ajax({
      url: '/order/status',
      data: {'pk': pk.attr('data-pk')},
      dataType: 'json',
      success: function (data) {
        switch (data.status) {
          case '1':
            $('.js-order-inbox').addClass('active')
            break
          case '2':
            $('.js-order-waiting').addClass('active')
            break
          case '3':
            $('.js-order-preparing').addClass('active')
            break
          case '4':
            $('.js-order-performing').addClass('active')
            break
          case '5':
            $('.js-order-workshop').addClass('active')
            break
          case '6':
            $('.js-order-outbox').addClass('active')
            break
          case '7':
            $('.js-order-delivered').addClass('active')
            break
        }
      }
    })
  }

  var updateStatus = function () {
    /* Updates current order status */

  }
  getStatus()
})
