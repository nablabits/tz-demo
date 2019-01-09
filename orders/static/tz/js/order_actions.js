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
    var aditionalPK = false
    if ($(this).attr('data-aditional-pk')) {
      aditionalPK = $(this).attr('data-aditional-pk')
    }
    $.ajax({
      url: '/actions/',
      data: { 'pk': pk, 'action': action, 'aditionalpk': aditionalPK },
      dataType: 'json',
      beforeSend: function () {
        $('#action-modal').modal('show')
      },
      success: function (data) {
        $('#action-modal .modal-content').html(data.html)
        if ($('#action-modal #id_stock').attr('checked')) {
          $('#action-modal .js-set-times').slideUp()
        }
      }
    })
  }

  var saveActionForm = function (e) {
    e.preventDefault()
    var form = $(this)
    $.ajax({
      url: form.attr('action'),
      data: form.serialize(),
      type: form.attr('method'),
      dataType: 'json',
      beforeSend: function () {
        $('#action-modal #submit').addClass('d-none')
        $('#action-modal #bg-working').removeClass('d-none')
      },
      success: function (data) {
        if (data.form_is_valid) {
          $('#action-modal #bg-working').addClass('d-none')
          $('#action-modal #check-success').removeClass('d-none')
          if (data.reload) {
            location.reload()
          } else if (data.redirect) {
            window.location.replace(data.redirect)
          } else {
            $(data.html_id).html(data.html)
          }
          $('#action-modal').modal('hide')
        } else {
          $('#action-modal .modal-content').html(data.html)
        }
      }
    })
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

  var queueAction = function () {
    var pk = $(this).attr('data-pk')
    var action = $(this).attr('data-action')
    $.ajax({
      url: '/queue-actions/',
      data: $.param({
        'pk': pk, 'action': action
      }),
      type: 'post',
      dataType: 'json',
      success: function (data) {
        if (data.is_valid) {
          if (data.reload) {
            location.reload()
          } else {
            $(data.html_id).html(data.html)
          }
        } else {
          $('.js-ajax-error').html(data.error)
          $('#display-errors').removeClass('d-none')
        }
      }
    })
    // return false
  }

  var getItems = function () {
    // Get the items of this type
    var action = $(this).attr('data-action')
    var pk = $(this).attr('data-pk')
    var type = $(this).attr('data-type')
    $.ajax({
      url: '/actions/',
      data: { 'pk': pk, 'action': action, 'item_type': type },
      dataType: 'json',
      success: function (data) {
        $('#items-list').html(data.html)
      }
    })
  }

  // actions (GET)
  $('.js-logout').click(loadActionForm)

  $('#root').on('click', '.js-crud-add', loadActionForm)
  $('#root').on('click', '.js-crud-edit', loadActionForm)
  $('#root').on('click', '.js-crud-delete', loadActionForm)

  // actions (POST)
  $('#action-modal').on('submit', '.js-send-form', saveActionForm)
  $('#order-status').on('click', '.js-order-status', updateStatus)
  $('.js-order-status').click(updateStatus)
  $('#search').on('submit', '.js-search-order', searchAction)
  $('#root').on('click', '.js-get-items', getItems)

  // Pqueue actions
  $('#root').on('click', '.js-queue', queueAction)
})
