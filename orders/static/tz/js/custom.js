/* global $ location  */

$(document).ready(function () {
  // Popovers activation
  $(function () {
    $('.js-popover').popover({
      container: 'body',
      trigger: 'focus'
    })
  })

  // opens a list item on orders/customers view
  var openItem = function () {
    var href = $(this).attr('data-href')
    $(location).attr('href', href)
  }

  $('.js-view-list-item').click(openItem)
})
