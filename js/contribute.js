function pageTrigger() {
		var contributors = getJSON('https://api.github.com/repos/Khroki/MCEdit-Unified/contributors');
		var totalContributions = 0;
		for (var i = 0; i < contributors.length; i++) {
			totalContributions += contributors[i].contributions;
		}
		var contributorDB = getJSON('contributors.json');
		for (var i = 0; i < contributors.length; i++) {
			var contributor = contributors[i];
			contributorDiv = '<a href="http://github.com/' + contributor.login + '"><i class="fa fa-github"></i></a> ';
			contributorDiv += '<a href="https://github.com/Khroki/MCEdit-Unified/commits?author=' + contributor.login + '"><i class="fa fa-code"></i></a> ';

			var badgeClass = 'contrib-danger';
			var lastDate = new Date();
			var events = [];
			if (contributor && contributor.events_url) {
				var events = getJSON('https://api.github.com/repos/Khroki/MCEdit-Unified/commits?author=' + contributor.login);
				if (events.length > 0) {
					lastDate = new Date(events[0].commit.author.date);
					var timedif = Math.abs((lastDate).getTime() - (new Date()).getTime());
					timedif = timedif / 1000;
					var ACTIVE_COMMITTER_MAX = 432000; //seconds (5 days)
					var RECENT_COMMITTER_MAX = 2678400; //seconds (1 month)
					if (timedif < ACTIVE_COMMITTER_MAX) {
						badgeClass = 'contrib-success';
						console.log(contributor.login + ' - ' + badgeClass);
					} else if (timedif < RECENT_COMMITTER_MAX) {
						badgeClass = 'contrib-old';
						console.log(contributor.login + ' - ' + badgeClass);
					} else {
						console.log(contributor.login + ' - ' + badgeClass);
					}
				}
			}
					
			if (contributorDB[contributor.login]) {
				if (contributorDB[contributor.login].twitter) {
					contributorDiv += '<a href="http://twitter.com/' + contributorDB[contributor.login].twitter + '"><i class="fa fa-twitter"></i></a> ';
				}
				if (contributorDB[contributor.login].youtube) {
					contributorDiv += '<a href="http://youtube.com/' + contributorDB[contributor.login].youtube + '"><i class="fa fa-youtube"></i></a> ';
				}
				if (contributorDB[contributor.login].reddit) {
					contributorDiv += '<a href="http://reddit.com/u/' + contributorDB[contributor.login].reddit + '"><i class="fa fa-reddit"></i></a> ';
				}
				if (contributorDB[contributor.login].facebook) {
					contributorDiv += '<a href="http://facebook.com/' + contributorDB[contributor.login].facebook + '"><i class="fa fa-facebook"></i></a> ';
				}
				if (contributorDB[contributor.login].payment) {
					contributorDiv += '<a href="' + contributorDB[contributor.login].payment + '"><i class="fa fa-usd"></i></a> ';
				}
			}
			console.log(contributor.login + ' - ' + badgeClass);
			$('#contributors').append('<div class="col-xs-6 col-sm-4 col-md-3 col-lg-2 contributor"><div class="circle ' + badgeClass + '" data-toggle="tooltip" data-placement="bottom" title="Last activity on master branch was ' + lastDate.toLocaleDateString() + '"></div><div class="thumbnail"><a href="' + contributor.html_url + '"><img src="' + contributor.avatar_url + '" alt=""></a><div class="caption"><h3>' + contributor.login + '<br><small>' + ((contributorDB[contributor.login] && (contributorDB[contributor.login].role) ? contributorDB[contributor.login].role : 'Contributor') + '<br>' + (Math.round(contributor.contributions / totalContributions * 100) == 0 ? '1' : Math.round(contributor.contributions / totalContributions * 100)) + '%') + '</small></h3><p>' + contributorDiv + '</p></div></div></div>');
		}
		// $('.circle').mouseover(function(){
		// 	$(this).remove();
		// });
		$('[data-toggle="tooltip"]').tooltip()
	}