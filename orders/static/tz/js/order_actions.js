/* global $ jQuery location */
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
      url: '/actions/',
      data: $.param({
        'pk': pk, 'status': status, 'action': action
      }),
      type: 'post',
      dataType: 'json',
      success: function (data) {
        if (data.reload) {
          location.reload()
        } else {
          $(data.html_id).html(data.html)
        }
      }
    })
    return false
  }

  var loadActionForm = function () {
    var action = $(this).attr('data-action')
    var pk = $(this).attr('data-pk')
    $.ajax({
      url: '/actions/',
      data: { 'pk': pk, 'action': action },
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
          if (data.reload) {
            $('#action-modal').modal('hide')
            location.reload()
          } else {
            $(data.html_id).html(data.html)
            $('#action-modal').modal('hide')
          }
        }
      }
    })
    if (action !== 'order-add-file') {
      return false
    }
  }

  var searchAction = function () {
    var form = $(this)
    $.ajax({
      url: form.attr('action'),
      data: form.serialize(),
      type: 'post',
      dataType: 'json',
      success: function (data) {
        $('#search-results').html(data.html)
        $('#search-results').collapse('show')
      }
    })
    return false
  }

  // actions (GET)
  $('.js-order-add').click(loadActionForm)
  $('.js-order-edit').click(loadActionForm)
  $('.js-order-edit-date').click(loadActionForm)
  $('#order-status').on('click', '.js-pay-now', loadActionForm)
  $('#order-status').on('click', '.js-close-order', loadActionForm)
  $('.js-order-add-comment').click(loadActionForm)
  $('#order-details').on('click', '.js-add-item', loadActionForm)
  $('#order-details').on('click', '.js-edit-item', loadActionForm)
  $('#order-details').on('click', '.js-delete-item', loadActionForm)
  $('.js-customer-add').click(loadActionForm)
  $('.js-customer-edit').click(loadActionForm)
  $('.js-customer-delete').click(loadActionForm)
  $('#timing-list').on('click', '.js-time-add', loadActionForm)
  $('#timing-list').on('click', '.js-time-delete', loadActionForm)
  $('.js-logout').click(loadActionForm)

  // actions (POST)
  $('#action-modal').on('submit', '.js-send-form', saveActionForm)
  $('#order-status').on('click', '.js-order-status', updateStatus)
  $('.js-order-status').click(updateStatus)
  $('#search').on('submit', '.js-search-order', searchAction)
})
