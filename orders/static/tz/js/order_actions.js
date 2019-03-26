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
    var form = $('#send-form')
    var formData = form.serializeArray()
    formData.push({ name: $(this).attr('name'), value: $(this).attr('value') })
    $.ajax({
      url: form.attr('action'),
      data: formData,
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

  var itemSelector = function () {
    // Deal with item_selector view
    var itemType = $(this).attr('data-type')
    var itemName = $(this).attr('data-name')
    var itemSize = $(this).attr('data-size')
    var aditionalpk = $('#order_view').attr('data-pk')

    $.ajax({
      url: '/item-selector/',
      data: $.param({
        'item-type': itemType,
        'item-name': itemName,
        'item-size': itemSize,
        'aditionalpk': aditionalpk
      }),
      type: 'get',
      dataType: 'json',
      success: function (data) {
        $('#item-selector').html(data.html)
      }
    })
    return false
  }

  var itemSelectorAdd = function (e) {
    // add items from selector
    e.preventDefault()
    var form = $(this)
    $.ajax({
      url: '/item-selector/',
      type: 'post',
      data: form.serialize(),
      dataType: 'json',
      success: function (data) {
        $('#item-selector').html(data.html)
      }
    })
    // return false
  }

  // actions (GET)
  $('.js-logout').click(loadActionForm)

  $('#root').on('click', '.js-crud-add', loadActionForm)
  $('#root').on('click', '.js-crud-edit', loadActionForm)
  $('#root').on('click', '.js-crud-delete', loadActionForm)

  // item selector trigger
  $('#root').on('click', '.js-item-selector', itemSelector)
  if ($('#item-selector').length) {
    itemSelector()
  }

  // item selector add
  $('#root').on('submit', '.js-item-selector-add', itemSelectorAdd)

  // actions (POST)
  $('#action-modal').on('click', '#send-form button', saveActionForm)
  $('#order-status').on('click', '.js-order-status', updateStatus)
  $('.js-order-status').click(updateStatus)
  $('#search').on('submit', '.js-search-order', searchAction)

  // Pqueue actions
  $('#root').on('click', '.js-queue', queueAction)
})
