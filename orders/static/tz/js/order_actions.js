/* global $  alert */
$(function () {
/* Functions */
  var getStatus = function () {
    /* Gets the current order status */
    var pk = $('#order_detail')
    $.ajax({
      url: '/order/get_status',
      data: {'pk': pk.attr('data-pk')},
      dataType: 'json',
      success: function (data) {
        $('#order-status').html(data.html_status)
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
    var pk = $('#order_detail')
    var status = $(this).attr('data-status')
    $.ajax({
      url: '/order/update_status',
      data: {'pk': pk.attr('data-pk'), 'status': status},
      dataType: 'json',
      success: function (data) {
        $('#order-status').html(data.html_status)
        getStatus()
      }
    })
    return false
  }

  var loadActionForm = function () {
    var action = $(this).attr('id')
    var pk = $(this).attr('data-pk')
    $.ajax({
      url: '/order/action/',
      data: {'pk': pk, 'action': action},
      dataType: 'json',
      beforeSend: function () {
        $('#action-modal').modal('show')
      },
      success: function (data) {
        $('#action-modal .modal-content').html(data.html)
      }
    })
  }

  // Get order's status on first load
  if (document.getElementById('order-status')) {
    getStatus()
  }

  // Update Status
  $('#order-status').on('click', '.js-order-inbox', updateStatus)
  $('#order-status').on('click', '.js-order-waiting', updateStatus)
  $('#order-status').on('click', '.js-order-preparing', updateStatus)
  $('#order-status').on('click', '.js-order-performing', updateStatus)
  $('#order-status').on('click', '.js-order-workshop', updateStatus)
  $('#order-status').on('click', '.js-order-outbox', updateStatus)

  // actions
  $('#order-edit').click(loadActionForm)
  $('#order-comment').click(loadActionForm)
  $('#order-file').click(loadActionForm)
  $('#order-file-delete').click(loadActionForm)
  $('#order-status').on('click', '#order-close', loadActionForm)
})
