function getURL(url){
	var response = $.ajax({
		type: "GET",
		url: url,
		cache: false,
		async: false
	}).responseText;
	try {
		return JSON.parse(response);
	} catch(err) {
		return response;
	}
}
/*versionCompare from http://stackoverflow.com/a/6832721*/
function compareVersionString(v1, v2, options) {
	var lexicographical = options && options.lexicographical,
	zeroExtend = options && options.zeroExtend,
	v1parts = v1.split('.'),
	v2parts = v2.split('.');

	function isValidPart(x) {
		return (lexicographical ? /^\d+[A-Za-z]*$/ : /^\d+$/).test(x);
	}

	if (!v1parts.every(isValidPart) || !v2parts.every(isValidPart)) {
		return NaN;
	}

	if (zeroExtend) {
		while (v1parts.length < v2parts.length) v1parts.push("0");
		while (v2parts.length < v1parts.length) v2parts.push("0");
	}

	if (!lexicographical) {
		v1parts = v1parts.map(Number);
		v2parts = v2parts.map(Number);
	}

	for (var i = 0; i < v1parts.length; ++i) {
		if (v2parts.length == i) {
			return 1;
		}

		if (v1parts[i] == v2parts[i]) {
			continue;
		}
		else if (v1parts[i] > v2parts[i]) {
			return 1;
		}
		else {
			return -1;
		}
	}

	if (v1parts.length != v2parts.length) {
		return -1;
	}

	return 0;
}
function compareVersionObject(a,b) {
	return compareVersionString(a.tag_name, b.tag_name) * -1;
}
function createReleaseInfo(data) {
	if (data.length == 0) {
		releaseBannerFail('Couldn\'t find any releases');
		return false;
	}
	try {
		data.sort(compareVersionObject);
		for (var i = 0; i < data.length; i++) {
			var note = data[i].body;
			note = note.replace(/\n/g,'<br>').replace(/@([a-zA-Z0-9]+)/g,' <a href="http://github.com/$1">@$1</a> ');
			var version = data[i].tag_name;
			var title = data[i].name
			if (data[i].prerelease) {
				var releaselabel = 'Pre-release';
			} else {
				var releaselabel = '';
			}
			var releasetime = new Date(data[i].published_at).toLocaleDateString();
			$('#changelog').append('<div class="row releasenote" version="' + version + '"></div>');
			releasenote = $('.releasenote[version="' + version + '"]');
			releasenote.append('<div class="col c2" style="text-align:right;"><div style="padding-right:10px;"><h2 style="display:inline;"><a href="' + data[i].html_url + '">' + version + '</a></h2><br>' + releaselabel + '<br>' + releasetime + '</div></div>');
			releasenote.append('<div class="col c10"><p>' + note + '</p></div></div>');
		}
		$('#changelog').show();
		prereleases = [];
		releases = [];
		for (var i = 0; i < data.length; i++) {
			if (data[i].prerelease) {
				prereleases.push(data[i]);
			} else {
				releases.push(data[i]);
			}
		}
		releases.sort(compareVersionObject);
		prereleases.sort(compareVersionObject);

		if (releases.length > 0) {
			release = releases[0];
			$('#releaseversion').html(release.tag_name);
			for (var i = 0; i < release.assets.length; i++) {
				$('#release-downloads').append('<a href="' + release.assets[i].browser_download_url + '"><i class="fa fa-cloud-download"></i> ' + release.assets[i].name + '</a><br>');
			}
			$('#release-notes').html('<a href="' + release.html_url + '"><i class="fa fa-book"></i> Release notes</a>');
			$('#release-message').slideDown();
		}
		if (prereleases.length > 0) {
			prerelease = prereleases[0];
			$('#prereleaseversion').html(prerelease.tag_name);
			for (var i = 0; i < prerelease.assets.length; i++) {
				$('#prerelease-downloads').append('<a class="btn btn-sm ' + (prerelease.prerelease == true ? 'btn-c' : 'btn-b') + '" href="' + prerelease.assets[i].browser_download_url + '"><i class="fa fa-cloud-download"></i> ' + prerelease.assets[i].name + '</a> <span style="color:gray">' + prerelease.assets[i].download_count + ' downloads, ' + Math.round(prerelease.assets[i].size/1000000) + ' MB</span><br>');
			}
			$('#prerelease-notes').html('<a href="' + prerelease.html_url + '"><i class="fa fa-book"></i> Release notes</a>');
			$('#prerelease-message').slideDown();
		}
	} catch(err) {
		releaseBannerFail(err.message);
	}
	$('#loading-message').slideUp();
}
function releaseBannerFail(message) {
	if (typeof message == "object") {
		message = 'An error occured loading the release information: ' + message.responseJSON.message;
	}
	if (message == undefined) {
		var message = 'An error occured loading the release information';
	}
	$('#failure-reason').html(message);
	$('#failed-message').slideDown();
	$('#loading-message').slideUp();
}
function populateNavbar() {
	var navjson = getURL('navbar.json');
	var navbar = navjson.navbar;
	for (var i = 0; i < navbar.length; i++) {
		var navitem = navbar[i];
		var active = location.href.replace('#','') == navjson.root + navitem.url;
		$('#navbar').append('<li class="' + (active ? 'active' : '') + '"><a href="' + navjson.root + navitem.url + '">' + navitem.displayname + '</a></li>')
	}
}
function getReleaseInfo() {
	return getURL('https://api.github.com/repos/Khroki/MCEdit-Unified/releases')
}
$(document).ready(function(){
	populateNavbar();
});
