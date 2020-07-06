/* global $  */
$(document).ready(function () {
	function populate () {
		$.ajax({
			url: '/populate',
			beforeSend: function () {
				$('#msgBox').html('<h2><i class="fas fa-circle-notch fa-spin text-info"></i></h2><p class="text-center">Well, you know, it takes me a couple of minutes to generate data for this year. I\'ll let you know if something goes wrong.</p>');
				$('#populate').prop('disabled', true);
			},
			success: function (data) {
				if (data.populated) {
					$('#msgBox').html('<p><i class="fad fa-database fa-3x text-info"></i></p><p>Great!<br>The database has been populated, you can get in with <em>user</em> &amp; <em>pass</em></p>');
					$('#populate').prop('disabled', false);
				} else {
					$('#msgBox').html('<p><i class="fad fa-sad-tear fa-3x text-info"></i></p><p class="text-center">Ooh, something went wrong<br>Try to repopulate the database again and, if the problem persits, please contact me at <a href="mailto:david@nablabits.com">david@nablabits.com</a></p>');
					$('#populate').prop('disabled', false);
				}
			}
		});
	}
	$('#populate').click(populate);
});
