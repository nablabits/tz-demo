/* global $ jQuery */
$(function () {
/* Functions */
  $.ajaxSetup({
    beforeSend: function (xhr, settings) {
      function getCookie (name) {
        var cookieValue = null
        if (document.cookie && document.cookie !== '') {
          var cookies = document.cookie.split(';')
          for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i])
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
              cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
              break
            }
          }
        }
        return cookieValue
      }
      if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
        // Only send the token to relative URLs i.e. locally.
        xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'))
      }
    }
  })

  var updateStatus = function () {
    /* Updates current order status */
    var pk = $(this).attr('data-pk')
    var status = $(this).attr('data-status')
    var action = 'update-status'
    $.ajax({
      url: '/order/action/',
      data: $.param({
        'pk': pk, 'status': status, 'action': action
      }),
      type: 'post',
      dataType: 'json',
      success: function (data) {
        // $('#order-status').html(data.html)
        $(data.html_id).html(data.html)
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

  var saveActionForm = function () {
    var action = $(this).attr('data-action')
    var form = $(this)
    $.ajax({
      url: form.attr('action'),
      data: form.serialize(),
      type: form.attr('method'),
      dataType: 'json',
      success: function (data) {
        if (data.form_is_valid) {
          $(data.html_id).html(data.html)
          $('#action-modal').modal('hide')
        }
      }
    })
    if (action !== 'order-file') {
      return false
    }
  }

  // actions
  $('#order-edit').click(loadActionForm)
  $('#order-comment').click(loadActionForm)
  $('#order-file').click(loadActionForm)
  $('#order-details').on('click', '#order-add-item', loadActionForm)
  $('#order-details').on('click', '#order-edit-item', loadActionForm)
  $('.js-file-delete').on('click', loadActionForm)
  $('#order-status').on('click', '#order-close', loadActionForm)

  $('#action-modal').on('submit', '.js-send-form', saveActionForm)
  $('#order-status').on('click', '.js-order-status', updateStatus)
})
