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

  var saveForm = function (e) {
    // the new method to process AJAX for each model
    e.preventDefault()
    var form = $(this)
    var formData = form.serializeArray()
    var btn = form.find('.js-submit')
    var errorBox = form.find('.js-errors')
    $.ajax({
      url: form.attr('action'),
      data: formData,
      type: form.attr('method'),
      dataType: 'json',
      beforeSend: function () {
        btn.addClass('d-none')
        form.find('.js-bg-working').removeClass('d-none')
      },
      success: function (data) {
        if (data.form_is_valid) {
          if (data.reload) {
            location.reload()
          } else if (data.redirect) {
            window.location.replace(data.redirect)
          } else {
            $(data.html_id).html(data.html)
          }
        } else {
          btn.removeClass('d-none')
          errorBox.html(data.errors)
        }
      }
    })
  }

  var kanbanJump = function () {
    // Move within kanban statuses
    var pk = $(this).attr('data-pk')
    var direction = $(this).attr('data-direction')

    // Show spinner and hide arrows to avoid problems
    var spinner = '#bg-working-' + pk
    $(spinner).removeClass('d-none')
    $('.js-kanban-jump').addClass('d-none')

    $.ajax({
      url: '/orders-CRUD/',
      data: $.param({
        'pk': pk, 'direction': direction, 'action': 'kanban-jump'
      }),
      type: 'post',
      dataType: 'json',
      success: function (data) {
        if (data.form_is_valid) {
          $(data.html_id).html(data.html)
        } else {
          $('#js-errors').html(data.error)
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

  function Hints () {
    // Shows some hints as long as user types in
    var search = $(this).val()
    var url = $(this).attr('id')
    var hiddenInput = '#' + $(this).next().attr('id')
    var outcome = '#' + $(this).next().next().attr('id')
    $.ajax({
      url: '/' + url + '/',
      type: 'get',
      data: $.param({ search: search }),
      dataType: 'json',
      success: function (data) {
        $(outcome).empty().addClass('border')
        var len = Object.keys(data).length
        for (var i = 0; i < len; i++) {
          var id = data[i].id
          var fname = data[i].name
          $(outcome).append(
            "<span class='py-1 js-hint px-2' value='" + id + "'>" + fname + '</span>')
        }
        // binding click event to options shown
        $(outcome + ' span').bind('click', function () {
          console.log('click');
          var name = $(this).text()
          var pk = $(this).attr('value')
          console.log(name, pk);
          if (pk !== 'void') {
            $('#action-modal ' + '#' + url).val(name)
            $('#action-modal ' + hiddenInput).attr('value', pk)
            $(outcome).empty().removeClass('border')
          }
        })
      },
      error: function (data) {
        $(outcome).empty()
      }
    })
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
  $('#root').on('click', '.js-order-status', updateStatus)
  $('.js-order-status').click(updateStatus)
  $('#search').on('submit', '.js-search-order', searchAction)

  // Customer hints for orders
  $('#action-modal').on('keyup', '.js-hints', Hints)

  // actions new CRUD process (POST)
  $('#root').on('submit', '.js-crud-form', saveForm)
  $('#root').on('click', '.js-kanban-jump', kanbanJump)

  // Pqueue actions
  $('#root').on('click', '.js-queue', queueAction)
})
