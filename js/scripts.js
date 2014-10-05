var releaseData = {};
var platforms = ["OSX","Win"];
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
function getLatestRelease() {
	data = releaseData;
	var prereleases = [];
	var releases = [];
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
	$('#navbar').after('<form class="navbar-form navbar-right"></form>');
	latestRelease = releaseData[0];
	for (var i = 0; i < platforms.length; i++) {
		var asset32 = getDownload(platforms[i],latestRelease.tag_name,32);
		var asset64 = getDownload(platforms[i],latestRelease.tag_name,64);
		if (asset32) {
			console.log(asset32);
			$('.navbar-form.navbar-right').append('<a class="btn btn-default" href="' + asset32.browser_download_url + '">Download <i class="fa fa-' + (platforms[i] == 'OSX' ? 'apple' : 'windows') + '"></i> ' + platforms[i] + ' 32bit</a> ');
		}
		if (asset64) {
			$('.navbar-form.navbar-right').append('<a class="btn btn-default" href="' + asset64.browser_download_url + '">Download <i class="fa fa-' + (platforms[i] == 'OSX' ? 'apple' : 'windows') + '"></i> ' + platforms[i] + ' 64bit</a> ');
		}
	}	
	return true;
}
function getDownload(platform,version,bittage) {
	for (var i = 0; i < releaseData.length; i++) {
		var release = releaseData[i];
		for (var x = 0; x < release.assets.length; x++) {
			var asset = release.assets[x];
			if (asset.name == 'MCEdit.v' + version + '.' + platform + '.' + bittage + 'bit.zip') {
				return asset;
			}
		}
	}
	return false;
}
$(document).ready(function(){
	var ratelimits = getJSON('https://api.github.com/rate_limit');
	if (ratelimits.resources.core.remaining > 0) {
		releaseData = getJSON('https://api.github.com/repos/Khroki/MCEdit-Unified/releases');
		releaseData.sort(compareVersionObject);
		if (generatePageStructure()) {
			try {
				pageTrigger();
			} catch(err) {
				console.log(err.message);
			}
		} else {
			alert('An error occured loading the webpage. Please try again later.');
		}
	} else {
		$('body').html('<h1>Rate Limit Exceeded</h1><br>Click <a href="https://github.com/Khroki/MCEdit-Unified">here</a> to go to the repository page instead.');
		$('body').css('background-color','#444444').css('text-align','center').css('color','white');
	}
});
