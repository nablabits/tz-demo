/* global $ location  */

$(document).ready(function () {
  // Popovers activation
  $(function () {
    $('.js-popover').popover({
      container: 'body',
      trigger: 'focus'
    })
  })

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
})
