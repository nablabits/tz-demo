// Flips between the orderlist and the week views
/* global $  */

$(document).ready(function () {
  // config
  $('#view-mode').flip({
    'trigger': 'manual',
    'front': '#week-view',
    'back': '#list-view'
  })

  // Action
  $('.js-flip').click(function () {
    $('#view-mode').flip('toggle')
    $(this).find('i').toggleClass('fa-toggle-off fa-toggle-on')
  })
})
