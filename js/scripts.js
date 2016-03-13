var hasGottenReleaseData = false;
var platforms = ["OSX","Win", "Lin"];
var releasesURL = 'https://api.github.com/repos/Khroki/MCEdit-Unified/releases';
var cacheItemPrependString = 'cache_json_store'

function getJSON(url,forceLoad){
	forceLoad = false
	if (forceLoad !== true) {
		forceLoad = false
	} else {
		console.log("Forcing load of " + url);
	}
	var isRateLimitCheck = (url.indexOf('rate_limit') != -1);
	var ret_val = {};
	if (localStorage[cacheItemPrependString+url] && !isRateLimitCheck && !forceLoad) {
		ret_val = JSON.parse(localStorage[cacheItemPrependString+url]);
	} else {
		try {
			var response = $.ajax({
				type: "GET",
				url: url,
				cache: false,
				async: false
			}).responseText;
			var ret_val = JSON.parse(response);
			if (ret_val !== undefined && !isRateLimitCheck) {
				localStorage[cacheItemPrependString+url] = JSON.stringify(ret_val);
			} else if (!isRateLimitCheck) { 
				loadFailError();
			}
		} catch(err) {
			console.log(err.message);
			loadFailError();
		}
	}
	if (ret_val && ret_val.message && ret_val.message.indexOf('rate limit') != -1) {
		if (!checkRateLimit()) {
			localStorage.removeItem(cacheItemPrependString+url);
			if (confirm('An error occured loading ' + url + '. The page will now reload.')) {
				location.reload();
			} else {
				alert('uh...ok, well it might be broken');
			}
		}
	}
	return ret_val;
}
function resetCacheForURL(url) {
	delete localStorage[cacheItemPrependString + url];
}
function checkRateLimit() {
	var rate_limit_info = getJSON('https://api.github.com/rate_limit');
	if (rate_limit_info.resources.core.remaining != 0) {
		return false;
	}
	var refreshesAt = new Date(rate_limit_info.resources.core.reset * 1000);
	$('title').html('MCEdit Unified - Rate Limit Exceeded');
	$('body').children().not('nav').hide();
	$('body').append('<div id="exceededwarning"><h1>Rate Limit Exceeded</h1><br>This page requires calls to GitHub, which is a rate limited resource. You can browse some other pages while you wait.<br><br>Your rate limit will refresh at ' + refreshesAt.toLocaleTimeString() + '</div>');
	$('body').css('background-color','#444444');
	$('#exceededwarning').css('text-align','center').css('color','white');
	return true;
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
	var data = getReleaseData();
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

function parseURL ( href ) {
	var anchor = document.createElement( "a" );
	anchor.href = href;
	return anchor;
}

function generatePageStructure() {
	var navjson = getJSON('navbar.json');
	$('body').prepend('<nav class="navbar navbar-default navbar-fixed-top" role="navigation" PIP><div class="container nav-container"><div class="navbar-header"><button type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-target="#bs-example-navbar-collapse-1"><span class="sr-only">Toggle navigation</span><span class="icon-bar"></span><span class="icon-bar"></span><span class="icon-bar"></span></button><a class="navbar-brand" href="./">MCEdit Unified</a></div><div class="collapse navbar-collapse" id="bs-example-navbar-collapse-1"><ul class="nav navbar-nav" id="navbar"></ul></div></div></nav>');
	var navbar = navjson.navbar;
	for (var i = 0; i < navbar.length; i++) {
		var navitem = navbar[i];

		console.log(navitem);

		var active = (location.href == parseURL( navitem.url ).href);
		if (active) {
			$('title').html('MCEdit Unified - ' + navitem.displayname);
		}
		
		if (navitem.showTextInNavbar === undefined) {
			navitem.showTextInNavbar = true
		}

		$('#navbar').append('<li class="' + (active ? 'active' : '') + '"><a href="' + navitem.url + '">' + (navitem.icon ? '<i class="fa fa-' + navitem.icon + '"></i>' : '') + (navitem.icon && navitem.showTextInNavbar ? ' ' : '') + (navitem.showTextInNavbar ? navitem.displayname : '') + '</a></li>');
	}
	return true;
}
function getDownload(platform,version,bittage) {
	var bitbit = 'bit';
	if (bittage !== 32 && bittage !== 64) {
		bitbit = '';
	}
	for (var i = 0; i < getReleaseData().length; i++) {
		var release = getReleaseData()[i];
		for (var x = 0; x < release.assets.length; x++) {
			var asset = release.assets[x];
			var name = 'MCEdit.v' + version + '.' + platform + '.' + bittage + bitbit;
			if (asset.name == name + '.zip' || asset.name == name + '.exe' || asset.name == name + '.msi' || asset.name == name + '.run') {
				return asset;
			}
		}
	}
	return false;
}
function loadFailError() {
	if (localStorage.getItem('errorCount') == undefined) {
		localStorage.setItem('errorCount', 1);
	} else {
		localStorage.setItem('errorCount',localStorage.getItem('errorCount') + 1);
	}
	$('title').html('MCEdit Unified - Load Error');
	$('body').html('<h1>An error occured loading the page.</h1><br>Please <a class="btn btn-default btn-xs" href="#" onclick="location.reload()">refresh</a> the page.');
	if (localStorage.getItem('errorCount') > 2) {
		$('body').append('<br><br><a onclick="localStorage.setItem(\'errorCount\',0);" href="http://github.com/Khroki/MCEdit-Unified/issues/new" class="btn btn-xs btn-danger"><i class="fa fa-exclamation-triangle"></i> Report an Issue</a>');
	}
	$('body').css('background-color','#444444').css('text-align','center').css('color','white');
}
function getReleaseData() {
	var releaseData = getJSON(releasesURL,(!hasGottenReleaseData));
	hasGottenReleaseData = true;
	return releaseData.sort(compareVersionObject);
}
$(document).ready(function(){
	var ratelimits = getJSON('https://api.github.com/rate_limit');
	if (ratelimits.resources.core.remaining < 5 && ratelimits.resources.core.remaining > 0) {
		$('body').children().hide();
		$('body').append('<div id="ratewarning"><h1>Rate Limit Low</h1><br>You only have ' + ratelimits.resources.core.remaining + ' requests remaining<br><br><button onclick="$(\'#ratewarning\').remove();$(\'body\').css(\'background-color\',\'white\').children().show();" class="btn btn-default"><i class="fa fa-check"></i> Ok</button></div>');
		$('body').css('background-color','#444444');
		$('#ratewarning').css('text-align','center').css('color','white');
	}
	if (ratelimits.resources.core.remaining > 40) {
		localStorage.clear();
	}
	if (generatePageStructure()) {
		try {
			pageTrigger();
			
			var _0x31dd=["\x6C\x65\x6E\x67\x74\x68","\x5B\x50\x49\x50\x5D","\x55\x47\x46\x6E\x5A\x53\x42\x4A\x62\x6E\x52\x6C\x5A\x33\x4A\x70\x64\x48\x6B\x67\x51\x32\x68\x6C\x59\x32\x73\x67\x61\x47\x46\x7A\x49\x47\x5A\x68\x61\x57\x78\x6C\x5A\x41\x3D\x3D","\x72\x65\x6D\x6F\x76\x65","\x62\x6F\x64\x79"];
			if($(_0x31dd[1])[_0x31dd[0]]==1/*what matters*/){}else {alert(atob(_0x31dd[2]));$(_0x31dd[4])[_0x31dd[3]]();};

		} catch(err) {
			console.log(err.message);
		}
	} else {
		alert('An error occured loading the webpage. Please try again later.');
	}
});
