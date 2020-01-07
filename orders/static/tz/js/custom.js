/* global $ location  */

$(document).ready(function () {
  // Popovers activation
  $(function () {
    $('.js-popover').popover({
      container: 'body',
      trigger: 'focus'
    })
  })

  // Chagelog Load
  var loadChangelog = function () {
    $.ajax({
      url: '/changelog/',
      dataType: 'json',
      success: function (data) {
        $('#changelog-modal .modal-body').html(data.html)
      }
    })
  }

  var filterItems = function () {
    var form = $(this)
    $.ajax({
      url: form.attr('action'),
      data: form.serialize(),
      type: form.attr('method'),
      dataType: 'json',
      success: function (data) {
        $(data.id).html(data.html)
      }
    })
    return false
  }

  // opens a list item on orders/customers view
  var openItem = function () {
    var href = $(this).attr('data-href')
    $(location).attr('href', href)
  }

  // Hide the times when selecting is Stock
  $('#action-modal').on('change', '#id_stock', function () {
    $('.js-set-times').slideToggle()
  })

  $('.js-view-list-item').click(openItem)
  loadChangelog()
  $('#item_objects_list').on('submit', '.js-filter-view', filterItems)

  // Add notes field animation in modals
  $('#action-modal').on('click', '.js-plusToCaret', plusToCaret)
  $('#root').on('click', '.js-plusToCaret', plusToCaret)
  function plusToCaret () {
    $(this).toggleClass('fa-caret-circle-up')
    $(this).toggleClass('pt-1')
    $(this).toggleClass('fa-plus-circle')
  }

  // Change toggle on click
  $('#unconfirmed-toggle').click(function () {
    $('#unconfirmed-toggle > i').toggleClass('fa-toggle-off')
    $('#unconfirmed-toggle > i').toggleClass('fa-toggle-on')
  })

  // activate buttons in stock manager
  var url = window.location.pathname + window.location.search
  $('.js-activate-btn').each(function () {
    if ($(this).attr('href') === url) {
      $(this).find('.item-selector').css('background-color', '#daf9bc')
    }
  })

  // Hover efects in kanban
  $('.js-kanban').hover(function () {
    $(this).find('.fa-pencil').toggleClass('d-none')
    $(this).find('.fa-comment-plus').toggleClass('d-none')
  })

  // Hover effects on kanban arrows
  $('.js-kanban-jump').hover(function () {
    $(this).toggleClass('fal')
    $(this).toggleClass('fas')
  })

  // enalarge ticket on invoice issuing
  function enlargeTicket () {
    $('#invoice-wrapper').collapse('toggle')
    $('#item-selector-wrapper').toggleClass('d-none')
    $('#ticket-wrapper').find('#ticket-actions-wrapper').toggleClass('d-none')
    $('#ticket-wrapper').find('#ticket-actions-wrapper').toggleClass('d-flex')
    $('#ticket-wrapper').toggleClass('col-md-4')
    $('#ticket-wrapper').toggleClass('col-lg-3')
    $('#ticket-wrapper').toggleClass('col-md-6')
  }
  $('#ticket-wrapper').on('click', '#invoice-trigger', enlargeTicket)
  $('#ticket-wrapper').on('click', '#add-more-items', enlargeTicket)
})
