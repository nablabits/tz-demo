/* global $ alert */
$(function () {
/* Functions */
  var getStatus = function () {
    /* Gets the current order status */
    var pk = $('#order_detail')
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

  var loadForm = function () {
    $.ajax({
      url: '/comment/add',
      type: 'get',
      dataType: 'json',
      beforeSend: function () {
        $('#modal-comment').modal('show')
      },
      success: function (data) {
        $('#modal-comment .modal-content').html(data.html_form)
      }
    })
  }

  var saveForm = function () {
    console.log('clicked modal')
    var form = $(this)
    $.ajax({
      url: form.attr('action'),
      data: form.serialize(),
      type: form.attr('method'),
      dataType: 'json',
      success: function (data) {
        console.log(data.form_is_valid)
        if (data.form_is_valid) {
          alert('Comentario enviado')
          $('#comment_list').html(data.html_comment_list)
          $('#modal-comment').modal('hide')
        } else {
          $('#modal-comment .modal-content').html(data.html_form)
        }
      }
    })
    return false
  }

  getStatus()

  // Add comment
  $('#add-comment').click(loadForm)
  $('#modal-comment').on('submit', '.js-add-comment-form', saveForm)
})
