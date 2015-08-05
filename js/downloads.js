function pageTrigger() {
		var is_OSX = navigator.platform.match(/(Mac)/i);
		var is_Win = (navigator.platform.match(/(Win)/i) && !is_OSX);

		if (is_OSX) {
			$('#Win-downloads-toplevel').hide();
			$('#Lin-downloads-toplevel').hide();
			$('#OSX-downloads-toplevel').addClass('col-md-offset-4');
			$('.override-platform-specific-downloads-container').show();
		} else if (is_Win) {
			$('#OSX-downloads-toplevel').hide();
			$('#Lin-downloads-toplevel').hide();
			$('#Win-downloads-toplevel').addClass('col-md-offset-4');
			$('.override-platform-specific-downloads-container').show();
		}
		$('.override-platform-specific-downloads').click(function(){
			$('#Win-downloads-toplevel').show();
			$('#Lin-downloads-toplevel').show();
			$('#OSX-downloads-toplevel').show();
			if (is_OSX) {
				$('#OSX-downloads-toplevel').removeClass('col-md-offset-4');
			} else if (is_Win) {
				$('#Win-downloads-toplevel').removeClass('col-md-offset-4');
			}
			$('.override-platform-specific-downloads-container').hide();
		});

			var releaseData = getReleaseData();
			var commentJSON = getJSON('comments.json');
		for (var i = 0; i < releaseData.length; i++) {
			var note = marked(releaseData[i].body).replace(/@([a-zA-Z0-9]+)/g,' <a href="http://github.com/$1">@$1</a>');
			var version = releaseData[i].tag_name;
			var title = releaseData[i].name
			if (releaseData[i].prerelease) {
				var releaselabel = 'Pre-release';
			} else {
				var releaselabel = '';
			}
			var releasetimesec = (new Date() - new Date(releaseData[i].published_at)) / 1000;
			var releasetime = new Date(releaseData[i].published_at).toLocaleDateString();
			if (releasetimesec < 60) {
				releasetime = Math.round(releasetimesec) + 's ago';
			} else if (releasetimesec < 60 * 60) {
				releasetime = Math.round(releasetimesec / 60) + 'm ago';
			} else if (releasetimesec < 60 * 60 * 24) {
				releasetime = Math.round(releasetimesec / 60 / 60) + ' hours ago';
			} else if (releasetimesec < 60 * 60 * 24 * 30) {
				releasetime = Math.round(releasetimesec / 60 / 60 / 24) + ' days ago';
			}

            var downloadNames = {
                ".Win.64bit.exe" : "Windows 64bit",
                ".Win.64bit.zip" : "Windows 64bit",
                ".Win.32bit.exe" : "Windows 32bit",
                ".Win.32bit.zip" : "Windows 32bit",
                ".OSX.64bit.zip" : "OS X",
                ".Lin.Universal.run" : "Linux",
                ".Universal.run" : "Linux",
                ".Source.zip" : "Source Code"
            }

            var getDownloadName = function(key)
            {
                if(key == "translations.zip")
                    return "Translations";
                key = key.split(version)[1];
                var res = downloadNames[key];
                if(typeof(res) == "undefined")
                res = key
                return res;
            }

            var versionDownloads = '';

			var totalDownloads = 0

            releaseData[i].assets.sort(function(a, b) {
                return a.download_count - b.download_count;
            });

			for (var x = releaseData[i].assets.length - 1; x >= 0; x--) {
                versionDownloads += getDownloadName(releaseData[i].assets[x].name) + ' - ' + releaseData[i].assets[x].download_count;
				if(x > 0)
                versionDownloads += '<br/>';
				totalDownloads += releaseData[i].assets[x].download_count;
			}

			var commentlink = '';
			if (commentJSON.hasOwnProperty(version)) {
				commentlink = 'Comment <a href="' + commentJSON[version] + '">Here</a>';
			} else {
				commentlink = 'Comments unavailable';
			}

			var downloadLinks = '<div class="row" style="padding-right:15px;">';
			downloadLinks += '<div class="btn-group"><button type="button" class="btn btn-primary btn-xs dropdown-toggle" data-toggle="dropdown" aria-expanded="false"><i class="fa fa-windows"></i> <span class="caret"></span></button><ul class="dropdown-menu" role="menu"><li><a href="' + getDownload('Win',version,64).browser_download_url + '">64 bit</a></li><li><a href="' + getDownload('Win',version,32).browser_download_url + '">32 bit</a></li></ul></div>';
			downloadLinks += ' <a href="' + getDownload('OSX',version,64).browser_download_url + '" class="btn btn-xs btn-primary"><i class="fa fa-apple"></i></a>';
			downloadLinks += ' <a href="' + getDownload('Lin',version,'Universal').browser_download_url + '" class="btn btn-xs btn-primary"><i class="fa fa-linux"></i></a>';
			downloadLinks += '</div>';

			$('#changelog').append('<div class="row releasenote" version="' + version + '"></div>' + (i < releaseData.length - 1 ? '<hr>' : ''));
			releasenote = $('.releasenote[version="' + version + '"]');
			releasenote.append('<div class="col-md-2 releasenote-title"><div style="padding-right:10px;"><h2 style="display:inline;"><a href="' + releaseData[i].html_url + '">' + version + '</a></h2><br><div class="hide" id="popover-' + version.replace(/\./g, '-') + '">' + versionDownloads + '</div><a class="badge" rel="popover" data-popover-content="#popover-' + version.replace(/\./g, '-') + '">' + totalDownloads + ' downloads</a><br>' + downloadLinks + commentlink + '<br>' + (releaseData[i].prerelease ? 'Pre-release<br>' : '') + releasetime + '</div></div>');
			releasenote.append('<div class="col-md-10"><p>' + note + '</p></div></div>');
            $('[rel="popover"]').popover({
                container: 'body',
                html: true,
                trigger: 'hover',
                content: function () {
                    var clone = $($(this).data('popover-content')).clone(true).removeClass('hide');
                    return clone;
                }
            }).click(function(e) {
                e.preventDefault();
            });
		}
		$('#changelog').show();
		
		var latestRelease = getReleaseData()[0];
		for (var i = 0; i < platforms.length; i++) {
			var assetUniversal = getDownload(platforms[i], latestRelease.tag_name, 'Universal');
			var asset32 = getDownload(platforms[i],latestRelease.tag_name, 32);
			var asset64 = getDownload(platforms[i],latestRelease.tag_name, 64);
			if(assetUniversal) {
				$('#' + platforms[i] + '-downloads').append('<a class="dl btn btn-default" href="' + assetUniversal.browser_download_url + '"><i class="fa fa-cloud-download" ></i> Version ' + latestRelease.tag_name + ' 32/64bit</a><br><br>');
			} else {
				if (asset32) {
					$('#' + platforms[i] + '-downloads').append('<a class="dl btn btn-default" href="' + asset32.browser_download_url + '"><i class="fa fa-cloud-download" ></i> Version ' + latestRelease.tag_name + ' 32bit</a><br><br>');
				}
				if (asset64) {
					$('#' + platforms[i] + '-downloads').append('<a class="dl btn btn-default" href="' + asset64.browser_download_url + '"><i class="fa fa-cloud-download"></i> Version ' + latestRelease.tag_name + ' 64bit</a>');
				}
			}
		}
		for (var i = 0; i < platforms.length; i++) {
			if ($('#' + platforms[i] + '-downloads').children().length == 0) {
				$('#' + platforms[i] + '-downloads').append('<button class="dl btn btn-danger" disabled>No Download Found</button><br><br>');
			}
		}
	}