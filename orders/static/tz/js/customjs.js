$(document).ready(function () {
  $.ajax({
    url: '/order/status/',
    type: 'get',
    data: {'pk': 1},
    dataType: 'json',
    success: function (data) {
      console.log(data)
      $('.js-order-inbox').addClass('active');
    }
  })
})
