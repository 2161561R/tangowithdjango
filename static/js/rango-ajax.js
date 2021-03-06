$(document).ready(function() {
//	Category likes
	$('#likes').click(function(){
		var catid;
		catid = $(this).attr("data-catid");
		$.get('/rango/like_category/', {category_id: catid}, function(data){
			$('#like_count').html(data);
			$('#likes').hide();
		});
	});

//	Category filter
	$('#suggestion').keyup(function(){
		var query;
		var dict;
		query = $(this).val();
		catid = $(this).attr("data-catid");
		if(catid.length != 0){
			$.get('/rango/suggest_category/', {suggestion: query, catid: catid}, function(data){
				$('#nav-sidebar').hide();
				$('#cats').html(data);
			});
		} else {
			$.get('/rango/suggest_category/', {suggestion: query, catid: ''}, function(data){
				$('#nav-sidebar').hide();
				$('#cats').html(data);
			});
		}
	});

//	Refresh results but not the whole page
	$('#search').click(function(){
		var query;
		query = $('#query').val();
		$.get('/rango/category_search/', {query: query}, function(data){
			$('#category_search').html(data);
		});

	});

//	Edit profile
	$('#edit').click(function(){
		$.get('/rango/edit_profile/', {}, function(data){
			$('#edit_profile').html(data).ready(function(){
				$('#cancel').click(function(){
					location.reload()
				});
			});
		$('#profile_data').hide();
		});
	});

//	Change Password
	$('#change_password').click(function(){
		$.get('/rango/change_password/', {}, function(data){
			$('#change_password_div').html(data).ready(function(){
				$('#cancel_password').click(function(){
					location.reload()
				});
			});
		$('#profile_data').hide();
		});
	});

	$('#cancel_password').click(function() {
		window.location.replace(window.location.href);
	});
});