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

  // opens a list item on orders/customers view
  var openItem = function () {
    var href = $(this).attr('data-href')
    $(location).attr('href', href)
  }

  $('.js-view-list-item').click(openItem)
  loadChangelog()
})
