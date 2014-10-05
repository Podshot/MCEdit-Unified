function getJSON(url){
	try {
		var response = $.ajax({
			type: "GET",
			url: url,
			cache: false,
			async: false
		}).responseText;
		return JSON.parse(response);
	} catch(err) {
		alert(err.message);
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
function getLatestReleases(data) {
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

	var ret_val = {};

	if (releases.length > 0) {
		ret_val.release = releases[0];
	}

	if (prereleases.length > 0) {
		ret_val.prerelease = prereleases[0];
	}

	return ret_val;
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
function generatePageStructure() {
	$('body').prepend('<nav class="navbar navbar-default navbar-fixed-top" role="navigation"><div class="container"><div class="navbar-header"><button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1"><span class="sr-only">Toggle navigation</span><span class="icon-bar"></span><span class="icon-bar"></span><span class="icon-bar"></span></button><a class="navbar-brand" href="#">MCEdit</a></div><div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1"><ul class="nav navbar-nav" id="navbar"></ul></div></div></nav>')
	var navjson = getJSON('navbar.json');
	var navbar = navjson.navbar;
	for (var i = 0; i < navbar.length; i++) {
		var navitem = navbar[i];
		var active = location.href.replace('#','') == navjson.root + navitem.url;
		if (active) {
			$('title').html('MCEdit Fork - ' + navitem.displayname);
		}
		$('#navbar').append('<li class="' + (active ? 'active' : '') + '"><a href="' + navjson.root + navitem.url + '">' + navitem.displayname + '</a></li>')
	}
	return true;
}
function getReleaseInfo() {
	return getJSON('https://api.github.com/repos/Khroki/MCEdit-Unified/releases')
}
function buildReleaseNotes(releasesJSON,element) {
	releasesJSON.sort(compareVersionObject);
	for (var i = 0; i < releasesJSON.length; i++) {
		var note = releasesJSON[i].body;
		note = note.replace(/\n/g,'<br>').replace(/@([a-zA-Z0-9]+)/g,' <a href="http://github.com/$1">@$1</a> ');
		var version = releasesJSON[i].tag_name;
		var title = releasesJSON[i].name
		if (releasesJSON[i].prerelease) {
			var releaselabel = 'Pre-release';
		} else {
			var releaselabel = '';
		}
		var releasetime = new Date(releasesJSON[i].published_at).toLocaleDateString();
		element.append('<div class="row releasenote" version="' + version + '"></div>' + (i < releasesJSON.length - 1 ? '<hr>' : ''));
		releasenote = $('.releasenote[version="' + version + '"]');
		releasenote.append('<div class="col-md-2" style="text-align:right;"><div style="padding-right:10px;"><h2 style="display:inline;"><a href="' + releasesJSON[i].html_url + '">' + version + '</a></h2><br>' + releaselabel + '<br>' + releasetime + '</div></div>');
		releasenote.append('<div class="col-md-10"><p>' + note + '</p></div></div>');
	}
	element.show();
}
$(document).ready(function(){
	if (generatePageStructure()) {
		var releases = getJSON('https://api.github.com/repos/Khroki/MCEdit-Unified/releases');
		buildReleaseNotes(releases,$('#changelog'));
	} else {
		alert('An error occured loading the webpage. Please try again later.');
	}
});
