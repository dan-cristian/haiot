function today(){
	var dt=now();
	return new Date(dt.getFullYear(), dt.getMonth(), dt.getDate());
}
String.prototype.padL = function(len, pad) {
	if(pad===null) pad=' ';
	if(this.length < len){
		var str=this;
		while (str.length < len) str = pad + str;
	   return str;
	}
	return this;
}

function now(){return new Date();}
if (!(String.prototype.includes)) {
	String.prototype.includes=function(find){
		return this.indexOf(find)!==false;
	}
}

Date.prototype.toText=function(onlyDate){
	return this.getDate()+'.'+(this.getMonth()+1)+'.'+this.getFullYear()+((onlyDate)?'':' '+this.toLocaleTimeString());
}

Date.prototype.shiftDay=function(shift){
	return (new Date(this.getFullYear(), this.getMonth(), this.getDate()+shift));}

Date.prototype.shift=function(shift, type, isDur){
	if((isDur)){
		if(this.getHours()>11){
			if(shift<2) shift=2;
		}else if(shift==0){
			shift=1;	// do pulnoci tehoz dne
		}
	}
	if(shift==0) return this;

	var pStop;
	if(!(shift)) return this;
	switch(type){
		 case 0: // day
			return this.shiftDay(shift);
		 case 1: // work day
				pStop=this;
				if(shift<0){
					while(shift!=0){
						pStop=pStop.shiftDay(-1);
						if(pStop.isWork()) shift++;
					}
				}else{
					while(shift!=0){
						if(pStop.isWork()) shift--;
						pStop=pStop.shiftDay(1);
					}
				}
				return pStop;
		 case 2: // week
				return this.shiftDay(7*shift);
		 case 3: // month
				return this.shiftMonth(shift);
		 case 4: // year
				return new Date(this.getFullYear()+shift, this.getMonth(), this.getDate());
	}
	return null;
}

// LZW-compress a string
function lzw_encode(s, toArr) {
    var dict = {};
    var data = (s + "").split("");
    var out = [];
    var currChar;
    var phrase = data[0];
    var code = 256;
    for (var i=1; i<data.length; i++) {
        currChar=data[i];
        if (dict[phrase + currChar] != null) {
            phrase += currChar;
        }
        else {
            out.push(phrase.length > 1 ? dict[phrase] : phrase.charCodeAt(0));
            dict[phrase + currChar] = code;
            code++;
            phrase=currChar;
        }
    }
    out.push(phrase.length > 1 ? dict[phrase] : phrase.charCodeAt(0));
    for (var i=0; i<out.length; i++) {
        out[i] = String.fromCharCode(out[i]);
    }
	 if ((toArr)) {
		return out;
	 }
    return out.join("");
}
function lzwDecode(data) {
	if(typeof(data)=='object') return lzwDecodeArray(data);
	var dict = {}, data = (data + "").split(""), currChar = data[0], oldPhrase = currChar,
		out = [currChar], code = 256, phrase, currCode;
	for (var i=1; i<data.length; i++) {
		currCode = data[i].charCodeAt(0);
		if (currCode < 256) phrase = data[i];
		else phrase = dict[currCode] ? dict[currCode] : (oldPhrase + currChar);
		out.push(phrase);
		currChar = phrase.charAt(0);
		dict[code] = oldPhrase + currChar;
		code++;
		oldPhrase = phrase;
	}
	return out.join("");
}

function lzw_decode(data) {
	var dict = {}, currChar = String.fromCharCode(data[0]), oldPhrase = currChar,
		out = [currChar], code = 256, phrase, currCode, i;
	for(i=1; i<data.length; i++) {
		currCode = data[i];
		if (currCode < 256) phrase = String.fromCharCode(data[i]);
		else phrase = dict[currCode] ? dict[currCode] : (oldPhrase + currChar);
		out += phrase;
		currChar = phrase[0];
		dict[code] = oldPhrase + currChar;
		code++;
		oldPhrase = phrase;
	}
	return out;
}

function send2client(data, filename, type){
	var file = new Blob([data], {type: type});
	if (window.navigator.msSaveOrOpenBlob) // IE10+
		 window.navigator.msSaveOrOpenBlob(file, filename);
	else { // Others
		var a = document.createElement("a"),
			url = URL.createObjectURL(file);
		a.href = url;
		a.download = filename;
		document.body.appendChild(a);
		a.click();
		setTimeout(function() {
			document.body.removeChild(a);
			window.URL.revokeObjectURL(url);
			}, 0);
	}
}

function sendSync(target,getParms, postParms, debug){
	var myRQ;
	if(!(getParms)) getParms="";
	if((user.auth) && getParms.indexOf('auth')<0) getParms='auth='+user.auth+'&'+getParms;
	if (window.XMLHttpRequest) myRQ=new XMLHttpRequest();
	else myRQ=new ActiveXObject("Microsoft.XMLHTTP");
	myRQ.readystate=0;
	target+=(/\?/.test(target)?'&':'?')+getParms;

	myRQ.open((postParms?"post":"get"), target, false);
	if (postParms) {
		myRQ.setRequestHeader("Content-type", "application/x-www-form-urlencoded; charset=utf-8");
		myRQ.setRequestHeader("Content-length", postParms.length);
		myRQ.setRequestHeader("Connection", "close");
		myRQ.send(postParms);
	} else {
		myRQ.send(null);
	}
	if(debug) alert('Sended: '+target+"\nResponse: "+myRQ.responseText);
	return text2XML(myRQ.responseText);
}


function getFileContent(file, parms, debug){
	var myRQ;
	if((parms)) file+=(/\?/.test(file)?'&':'?')+parms;
	if (window.XMLHttpRequest) myRQ=new XMLHttpRequest();
	else myRQ=new ActiveXObject("Microsoft.XMLHTTP");
	myRQ.readystate=0;
	myRQ.open("get", file, false);
	myRQ.send(null);
	if (debug) {
		document.body.lRQ=myRQ;
	}
	return myRQ.responseText;
}
function text2XML(str){
	if (window.DOMParser){
		var parser=new DOMParser();
		var xmldoc=parser.parseFromString(str,"text/xml");
	}else {
		var xmldoc=new ActiveXObject("Microsoft.XMLDOM");
		xmldoc.async="false";
		xmldoc.loadXML(str);
	}
	if((xmldoc.documentElement) && (xmldoc.documentElement.tagName=='compress')){
		return text2XML('<root>'+decodeURI(lzw_decode(xmldoc.documentElement.childNodes[0].nodeValue))+'</root>');
//		text2XML('<root>'+lzw_decode(xmldoc.documentElement.childNodes[0].nodeValue)+'</root>');

	}
	return xmldoc;
}
function randStr(lLength, chars) {
	if(!(chars))
		chars = "ABCDEFGHIJKLMNOPQRSTUVWXTZabcdefghiklmnopqrstuvwxyz"
	var randStr = '';
	for (var i=0; i<lLength; i++)
		randStr += chars.substr(Math.floor(Math.random() * chars.length),1);
	return randStr;
}

sysCreateElement=function(tag, attrs){
	switch(tag){
		case 'fieldset':
			var o=document.createElement('fieldset');
			o.appendChild(document.createElement('legend'));
			setDesignOptions(o, {
				props:[{key:'legend',title:'Legend',
								get:function(){return this.childNodes[0].innerHTML},
								set:function(val){this.childNodes[0].innerHTML="";this.childNodes[0].appendChild(document.createTextNode(val));}},
						],insert:1});
			break;
		case 'span':
			var o=document.createElement('span');
			o.setAttribute('name','Label');
			o.appendChild(document.createTextNode('Text'));
			setDesignOptions(o, {props:[{key:'text',title:'Text',
						get:function(){return this.innerHTML;},
						set:function(val){this.innerHTML=val;}}]});
			break;
		default:
			o=document.createElement(tag);
			switch(tag){
				case 'div':
					setDesignOptions(o, {insert:1});
					break;
				case 'input':
					setDesignOptions(o, {insert:1,props:[{key:'type',title:'Type', mode:1},
																	 {key:'class',title:'Class', mode:1},
																	 {key:'value',title:'Value',
																		get:function(){var type=this.getAttribute('type').toLowerCase();
																			return (type=='checkbox' || type=='radio'?this.checked:this.value)},
																		set:function(val){var type=this.getAttribute('type').toLowerCase();
																			if(type=='checkbox' || type=='radio')
																				this.checked=val;
																			else this.value=val;}
																	 }]});
					break;
				case 'table':
					o.setAttribute('style','display:block;width:100px;height:100px;background-color:#aaa;');
					o.appendChild(document.createElement('tbody'));
					setDesignOptions(o);
					break;

			}
	}
	if(attrs){
		o.innerHTML='';
		if(attrs.id) o.setAttribute('id', attrs.id);
		if(attrs.Class) o.setAttribute('class', attrs.Class);
		if(attrs.txt) o.appendChild(document.createTextNode(attrs.txt));
		if(attrs.code) o.innerHTML=attrs.code;
		if(attrs.src) o.setAttribute('src',attrs.src);
		if(attrs.name) o.setAttribute('name',attrs.name);
		if(attrs.type) o.setAttribute('type',attrs.type);
		if(attrs.value) o.value=attrs.value;
		if(attrs.style) o.setAttribute('style',attrs.style);
		if(attrs.checked) o.checked=attrs.checked;
		if(attrs.title) o.setAttribute('title',attrs.title)
		if(attrs.content) o.appendChild(attrs.content);

		if(attrs.onmousedown) o.onmousedown=attrs.onmousedown;
		if(attrs.onmouseup) o.onmousedown=attrs.onmouseup;
		if(attrs.onclick) o.onclick=attrs.onclick;
		if(attrs.onchange) o.onchange=attrs.onchange;
	}
	return o;
}
function setDesignOptions(oEl, opts){
	if(!oEl.props) oEl.props={};
	if(!(oEl.dOptions)) oEl.dOptions=new Array();
		for(var i in opts)
			if(i=='props'){
				for(var j=0; j<opts[i].length; j++)
					if((opts[i][j]) && (opts[i][j].key))
						oEl.props[opts[i][j].key]=opts[i][j];
			}else oEl.dOptions[i]=opts[i];

	if(!oEl.props.name) oEl.props.name={key:'name', title:'Name', mode:1};

	if((opts) && opts.move) oEl.style.position="absolute";

	oEl.getProperty=function(key){
		if(this.props[key]){
			if(this.props[key].get){
				this.tmpFcn=this.props[key].get;
				return this.tmpFcn();
			}else if(this.props[key].mode){
				if(this.props[key].mode==1) return this.getAttribute(key);
				else if(this.props[key].mode==2) return this[key];
			}
		}
		return null;
	}
	oEl.setProperty=function(key, val){
		if(this.props[key]){
			if(this.props[key].set){
				this.tmpFcn=this.props[key].set;
				return this.tmpFcn(val);
			}else if(this.props[key].mode){
				if(this.props[key].mode==1) this.setAttribute(key, val);
				else if(this.props[key].mode==2) this[key]=val;
			}
		}
		return true;
	}
}
function nVer(n){return (n/100).toFixed(2).toString().substr(1,3);}
function setVersions(){
//	values['ver_INT']=values['I00000']+nVer(values['I00001'])+(values['I00002']>0?nVer(values['I00002']):''); // RD
	values['ver_INT']=values['I00020']+nVer(values['I00021'])+(values['I00022']>0?nVer(values['I00022']):''); // RD
	values['ver_WEB']=values['I10007']+nVer(values['I10008'])+(values['I10009']>0?nVer(values['I10009']):''); // RD
	jsVer=getFileContent('ver.txt');
	values['ver_JS']='';
	if(isNaN(parseInt(jsVer.substr(0,2), 16))){
		values['ver_JS']+=values['I00017']+nVer(values['I00018'])+(values['I00019']>0?nVer(values['I00019']):'');
	}else{
		for(var i=0;i<3; i++){
			tmp=parseInt(jsVer.substr(2*i,2), 16);
			if(i<2 || tmp>0)
			values['ver_JS']+=(i==0?'':'.')+(tmp<10?'0':'')+tmp;
		}
	}
}

function createElement(tag, cl, co, attrs){
	 var el=document.createElement(tag);
	 if(cl) el.setAttribute('class', cl);
	 if(co) el.appendChild(co);
	 if ((attrs)) {
		for (var i in attrs) el.setAttribute(i, attrs[i]);
	 }
	 return el;
}

function unitInfo(addAlarms){
	var cont=document.createElement('div'),
		row, el, txt, elTable=document.createElement('table'),
		tBody, doc=sendSync(urlCfg,'X'+randStr(2)), xEl;
	cont.appendChild(elTable);
	elTable.appendChild(document.createElement('tbody'));
	elTable.setAttribute('class','infoTable');
	tBody=elTable.tBodies[0];
	tBody.setAttribute('id','infoTBody');

	if(doc && doc.documentElement){
		xEl=doc.documentElement;
	}
	function findXEl(xEl, id){
		var i;
		if(xEl)
			for(i=0;i<xEl.childNodes.length; i++)
				if(xEl.childNodes[i].nodeType==1 && xEl.childNodes[i].tagName=='dir')
					if(Number(xEl.childNodes[i].getAttribute('id'))==id)
						return xEl.childNodes[i];
		return false;
	}
	xEl=findXEl(xEl, values.H10520);
	if(xEl) txt=xEl.getAttribute('name');
	row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('th'); row.appendChild(el);
		el.appendChild(document.createTextNode(words.unitType));
		el=document.createElement('td'); row.appendChild(el);
		txt='';
		xEl=findXEl(xEl, values.H10521);
		if(xEl){
			txt=xEl.getAttribute('name');
			xEl=findXEl(xEl, values.H10522);
			if(xEl) txt+=' '+xEl.getAttribute('name');
		}
		el.appendChild(document.createTextNode(txt));
	row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('th'); row.appendChild(el);
		el.appendChild(document.createTextNode(words.unitDesign));
		el=document.createElement('td'); row.appendChild(el);
		txt='';
		xEl=findXEl(xEl, values.H10523);
		if(xEl) txt=xEl.getAttribute('name');
		el.appendChild(document.createTextNode(txt));
	row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('th'); row.appendChild(el);
		el.appendChild(document.createTextNode(words.unitSpec));
		el=document.createElement('td'); row.appendChild(el);
		txt='';
		xEl=findXEl(xEl, values.H10524);
		if(xEl) txt=xEl.getAttribute('name');
		el.appendChild(document.createTextNode(txt));

	row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('th'); row.appendChild(el);
		el.appendChild(document.createTextNode(words.productNumber));
		el=document.createElement('td'); row.appendChild(el);
		txt='';
		for(i=300; i<310; i++)
			txt+=String.fromCharCode(values['H12'+i]);
		el.appendChild(document.createTextNode(txt));
	if(addAlarms){
		row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('th'); row.appendChild(el);
		el.appendChild(document.createTextNode(words.alarms));
		el=document.createElement('td'); row.appendChild(el);
	}
	row=tBody.insertRow(tBody.rows.length);
		el=document.createElement('td'); row.appendChild(el);
		el.setAttribute('colspan','2');row.style.height="0";el.style.padding=0;el.style.border="outset 1px";

	addVerRows(tBody);
//	if(values.I10006>0){
		row=tBody.insertRow(-1),
			cell=document.createElement('th');
		cell.appendChild(document.createTextNode(words.fwAvail+':')); row.appendChild(cell);
		var cell=row.insertCell(-1); cell.appendChild(document.createTextNode(values['ver_WEB']));

		if(!(addAlarms)){
			var tm=now();
			if(values.I10006>0 && ((values.I10010!=values.I10007 || values.I10011!=values.I10008 || values.I10012!=values.I10009) ||
				tm.getTime()>(values.I10013*65536+(values.I10014<0?values.I10014+65535:values.I10014))*1000)){

				cont.appendChild(document.createElement('div'));
				cont.lastChild.setAttribute('class','buttonLeft');
				cont.lastChild.style.clear="both";
				cont.lastChild.style.marginLeft="95px";
				cont.lastChild.appendChild(document.createTextNode(words.updateIgnore));
				cont.lastChild.onmouseup=function(e){
						send2Unit(getUrlPar('H10006', 2), urlDataSet);
				}
				cont.appendChild(document.createElement('div'));
				cont.lastChild.setAttribute('class','buttonLeft');
				cont.lastChild.appendChild(document.createTextNode(words.updateIt));
				cont.lastChild.onmouseup=function(){
					send2Unit(getUrlPar('H10006', 1), urlDataSet);
				}
			}
		}
/*
	this.object.lastChild.onmouseup=function(){
		var dt=this.parentNode.instance.date, inp=this.parentNode.instance.rBox.getElementsByTagName('input');
		dt.setHours(Number(inp[0].value));
		dt.setMinutes(Number(inp[1].value));
		this.parentNode.instance.target.setDateTime(dt);
		document.getElementById('smog').style.visibility='hidden';
		document.getElementById('pageBlock').removeChild(this.parentNode);
	};
	this.object.appendChild(document.createElement('div'));
	this.object.lastChild.setAttribute('class','buttonLeft');
	this.object.lastChild.appendChild(document.createTextNode(words.cancel));
	this.object.lastChild.onmouseup=function(){
		document.getElementById('smog').style.visibility='hidden';
		document.getElementById('pageBlock').removeChild(this.parentNode);
	};


*/


//	}

	return cont;
}

function addVerRows(tB){
	setVersions();
	var row=tB.insertRow(-1),
		cell=document.createElement('th');
	cell.appendChild(document.createTextNode('sw RD5 ver.:')); row.appendChild(cell);
	var cell=row.insertCell(-1); cell.appendChild(document.createTextNode(values['ver_INT']));
/*	row=tB.insertRow(-1),
		cell=document.createElement('th');
	cell.appendChild(document.createTextNode('sw RD5 web ver.:')); row.appendChild(cell);
	cell=row.insertCell(-1); cell.appendChild(document.createTextNode(values['ver_JS']));
*/
}
function createFwStatus(update){
	//if(!(values['ver_ETH']))
	var table=document.createElement('table');
	table.setAttribute('class','infoTable');
/*	var row=table.insertRow(-1);
	row.insertCell(-1);
	var cell=document.createElement('th');
	    cell.appendChild(document.createTextNode(words.fwUnit));
	    row.appendChild(cell);*/
	addVerRows(table);
	if(update){
/*try{
		doc=sendSync("http://rd5update.atrea.cz/software/rd5Packages/packages.php",randStr(2), false, false);
		var packs=doc.getElementsByTagName('package'),
			pack=packs[0];
//			pack=packs[packs.length-1];
		var cell=document.createElement('th');
		    cell.appendChild(document.createTextNode(words.fwAvail));
		    table.rows[0].appendChild(cell);
		var cell=table.rows[1].insertCell(-1);
		cell.appendChild(document.createTextNode(
			pack.getElementsByTagName('cp19')[0].getElementsByTagName('sw_major')[0].childNodes[0].nodeValue+'.'+
			pack.getElementsByTagName('cp19')[0].getElementsByTagName('sw_minor')[0].childNodes[0].nodeValue));

		var cell=table.rows[2].insertCell(-1);
		cell.appendChild(document.createTextNode(
			pack.getElementsByTagName('rd4int')[0].getElementsByTagName('sw_major')[0].childNodes[0].nodeValue+'.'+
			pack.getElementsByTagName('rd4int')[0].getElementsByTagName('sw_minor')[0].childNodes[0].nodeValue));

		var cell=table.rows[3].insertCell(-1);
		cell.appendChild(document.createTextNode(
			pack.getElementsByTagName('digi')[0].getElementsByTagName('sw_major')[0].childNodes[0].nodeValue+'.'+
			pack.getElementsByTagName('digi')[0].getElementsByTagName('sw_minor')[0].childNodes[0].nodeValue));

		var cell=table.rows[4].insertCell(-1);
		cell.appendChild(document.createTextNode(
			pack.getElementsByTagName('rd4web')[0].getElementsByTagName('sw_major')[0].childNodes[0].nodeValue+'.'+
			pack.getElementsByTagName('rd4web')[0].getElementsByTagName('sw_minor')[0].childNodes[0].nodeValue));

}catch(e){;}
*/
	}
	return table;
/*<table style="border:1px outset; width:400px; margin-left:130px;">
*/
}

function getUrlPar(par, val){
	val=parseFloat(val);
	if(params[par]){
		if(params[par].options)
			var opt=options[params[par].options];
		else{
			opt=null;
			if(params[par].optionlist){
				multiOption=params[par].optionlist;
				for(var i in params[par].optionlist){
					if(!(params[par].optionlist[i].when) || testWhen(params[par].optionlist[i].when)){
						opt=options[i];
						break;
					}
				}
			}
		}
		if(opt){
			if(opt.type!="rangeEnum" && ((opt.minVal!=='' && val<opt.minVal) || (opt.maxVal>0 && val>opt.maxVal))){
//			if((opt.minVal!=='' && val<opt.minVal) || (opt.maxVal>0 && val>opt.maxVal)){
				alert(words['badInput']+','+words['allowedRange']+': '+opt.minVal+' .. '+(opt.maxVal>0?opt.maxVal: ''));
				return false;
			}
			if(opt.coef) val=val*opt.coef;
			else if(params[par].coef) val=val*params[par].coef;
			if(opt.offset)	val=val+opt.offset;
			else if(params[par].offset) val=val+params[par].offset;
			val=Math.round(val);
		}
	}
	if(val<0) val=val+65536;
	values[par]=val;
	val=val.toString();
	return par+'0000'.substr(0,5-val.length)+val;
//	return par+val.toString();
}
function getTimezoneOffset(dt){
	var d=new Date(dt.getFullYear(), 0, 1);
	return d.getTimezoneOffset();
}
function nodeContent(n) {
	for(var i=0; i<n.childNodes.length; i++)
		if(n.childNodes[i].nodeType==4) return n.childNodes[i].nodeValue;
	return '';
}

function loadLangs(n, srvc){
	var iLangs=n.getElementsByTagName('i'), txt, id, el;
	langs=[];
	for(var j=0; j<iLangs.length; j++) {
		id=Number(iLangs[j].getAttribute('id'));
		txt=iLangs[j].getAttribute('title');
		txt=(txt.substr(0,1)=='$'?words[txt.substr(1)]:txt);
		langs.push([id, txt]);
		if(values[idLNG]==id){
			el=document.createElement('img');
//			el.setAttribute('src', server+'images/f'+id+'.jpg');
			el.setAttribute('src', 'images/f'+id+'.jpg');
			el.setAttribute('title',txt);
			el.style.boxShadow="1px 1px 3px #666";
			el.onmouseup=function(){showLngs(this.lngId)};
			if((srvc)){
				document.getElementById('langs').appendChild(el);
			}else{
				document.getElementById('topFlags').appendChild(el);
			}
		}
	}
	if(iLangs.length>2){
		// button change language
	}
}
function showLngs(){
	var wnd=createWindow(''), tmp=document.createElement('div'), j, el;
	tmp.setAttribute('style', 'display:block; padding:0px;align-content:center;text-align:center; width:100%; overflow: hidden;height:200px');
	for(j=0; j<langs.length; j++){
		el=document.createElement('img');
		el.setAttribute('src', server+'images/f'+langs[j][0]+'.jpg');
		el.setAttribute('title',langs[j][1]);
		el.lngId=langs[j][0];
		el.onmouseup=function(){changeLng(this.lngId)};

		el.setAttribute('style', 'height:30px; float: left; padding:6px; border: 1px solid #aaa; margin:12px; box-shadow:1px 1px 4px; background-color:#ddd');
		if(langs[j][0]==values[idLNG])
			el.style.boxShadow='inset 2px 2px 4px';
		tmp.appendChild(el);
	}
	wnd.setContent(tmp, true);
	var el=document.createElement('div');
	el.setAttribute('type', 'button');
	el.setAttribute('id', 'cmdCancel');
	el.setAttribute('class', 'buttonSmallR');
	el.appendChild(document.createTextNode(words['cancel']));
	el.onmousedown=function() {this.parentNode.parentNode.close()};
	wnd.setFooter(el, true);
	wnd.show();
}
function changeLng(lngId){
	sendSync(urlDataSet+'','auth='+user.auth+'&'+getUrlPar(idLNG,lngId)+'&X'+randStr(2));
	location.reload(true);
}

function loadLang(){
	var doc=sendSync('lang/texts_'+values[idLNG]+'.xml',randStr(2), null, false);
	if((doc) && (doc.documentElement)){
		var parTxt;
		eval('words='+nodeContent(doc.documentElement.getElementsByTagName('words')[0]));
		eval('parTxt='+nodeContent(doc.documentElement.getElementsByTagName('params')[0]).replace(/\n/g,"<br/>").replace(/\r/g,""));
		for(var i in params)
		if(parTxt[i]){
			try {
				params[i].title=decodeURIComponent(parTxt[i].t);
			} catch(e) {
				params[i].title=parTxt[i].t;
			}
			if((parTxt[i].d)){
				try {
					params[i].tip=decodeURIComponent(parTxt[i].d);
				} catch(e) {
					params[i].tip=parTxt[i].d;
				}
			}
		}
		document.getElementsByTagName('h1')[0].innerHTML=words['mainTitle'];
		if(document.getElementById('srvcLink'))
			document.getElementById('srvcLink').innerHTML=words['serviceSetup'];
		if(document.getElementById('userLink'))
			document.getElementById('userLink').innerHTML=words['userSetup'];
	}
}

function showOK(){
	document.getElementById('saveBox').style.visibility='visible';
	document.getElementById('smog').style.visibility='visible';
	setTimeout("document.getElementById('saveBox').style.visibility=''; document.getElementById('smog').style.visibility=''",1500);
}
function wait(msg){
	if((msg)){
		document.getElementById('msgBox').innerHTML='';
		document.getElementById('msgBox').appendChild(document.createTextNode(msg));
		document.getElementById('smog').style.visibility='visible';
		document.getElementById('msgBox').style.visibility='visible';
	}else{
		document.getElementById('smog').style.visibility='hidden';
		document.getElementById('msgBox').style.visibility='hidden';
	}
}
function calendar(obj){
	var monthNames=[], tmp, i, selDate=obj.getValue();
	for(i=0; i<12; i++)
		monthNames.push(words['monthName'+(i+1)]);

	if(!(selDate) || !(selDate.getTime))
		selDate=today();
	this.date=new Date(selDate.getFullYear(), selDate.getMonth(), selDate.getDate());
	this.time=[selDate.getHours(), selDate.getMinutes()];

	this.target=obj;

	this.object=document.createElement('div');
	this.object.setAttribute('class', 'calendar');
	this.object.onclick=function(e){
		if(!(e)) e=window.event;
		eventStopBubble(e);
	}
	this.object.instance=this;
	this.object.appendChild(document.createElement('div'));
	this.object.lastChild.setAttribute('class', 'hdr');
//	this.month=document.createElement('InputSelect', {style:'margin-left:20px'});
	this.month=document.createElement('select');
	this.month.setAttribute('style','margin-left:20px');

	for(i=0; i<monthNames.length; i++){
		this.month.appendChild(document.createElement('option'));
	 this.month.lastChild.appendChild(document.createTextNode(monthNames[i]));
	 this.month.lastChild.setAttribute('value',i);
	}
	this.month.value=this.date.getMonth();
	this.month.onchange=function(e){this.parentNode.parentNode.instance.showTable()};
	this.object.lastChild.appendChild(this.month);

	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoRight');
	tmp.onclick=function(e){this.nextSibling.value=Number(this.nextSibling.value)+1;this.nextSibling.onchange()}
	this.object.lastChild.appendChild(tmp);
//	this.year=document.createElement('InputNumber', {style:'width:35px;float:right'});
	this.year=document.createElement('input');
	this.year.setAttribute('type', 'text');
	this.year.value=this.date.getFullYear();
	this.year.onchange=function(e){this.parentNode.parentNode.instance.showTable()};
	this.object.lastChild.appendChild(this.year);
	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoLeft');
	tmp.onclick=function(e){this.previousSibling.value=Number(this.previousSibling.value)-1;this.previousSibling.onchange()};
	this.object.lastChild.appendChild(tmp);

	tmp=document.createElement('div');
	tmp.setAttribute('style','float:left; clear:left;background-color:#fff; padding:8px 6px 8px 6px;');
	tmp.appendChild(document.createElement('div'));
	tmp.lastChild.setAttribute('class','icoLeft');
	tmp.lastChild.setAttribute('style','float:left');
	tmp.lastChild.inst=this;
	tmp.lastChild.onclick=function(){this.inst.goMonth(-1)};

	this.table=document.createElement('div');
	this.table.setAttribute('class', 'table');
	tmp.appendChild(this.table);
	tmp.appendChild(document.createElement('div'));
	tmp.lastChild.setAttribute('class','icoRight');
	tmp.lastChild.setAttribute('style','float:left');
	tmp.lastChild.inst=this;
	tmp.lastChild.onclick=function(){this.inst.goMonth(1)};
	this.object.appendChild(tmp);

	this.table.onmousedown=function(e){
		e=e||window.event;
		var el=e.srcElement || e.target,
			inst=this.parentNode.parentNode.instance;
//			targetEl=this.parentNode.parentNode.instance.target;
		if(el.date){
			inst.date=el.date;
			inst.showTable();

/*			targetEl.setValue(el.date);
			targetEl.onchange();
			if(targetEl.onUserChange) targetEl.onUserChange();
			if(targetEl.onChange) targetEl.onChange();
			this.parentNode.parentNode.instance.close();
*/
		}
	}

	this.rBox=document.createElement('div');
	this.rBox.setAttribute('class','rBox');
	this.object.appendChild(this.rBox);
	this.rBox.appendChild(document.createElement('span'));

	this.rBox.appendChild(document.createElement('div'));
	this.rBox.lastChild.setAttribute('class', 'timeCtrl');

	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoUp');
	tmp.onclick=function(e){this.parentNode.parentNode.oHour.shift(1)};
	this.rBox.lastChild.appendChild(tmp);
	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoUp');
	tmp.onclick=function(e){this.parentNode.parentNode.oMin.shift(1)};
	this.rBox.lastChild.appendChild(tmp);


	this.rBox.appendChild(document.createElement('input'));
	this.rBox.lastChild.value=this.date.getHours().toString().padL(2,'0');
	this.rBox.lastChild.oldVal=this.rBox.lastChild.value;
	this.rBox.oHour=this.rBox.lastChild;
	this.rBox.oHour.shift=function(n){
		var num=Number(this.value)+n;
		if(num<0) num=23;
		else if(num>23) num=0;
		this.value=num.toString().padL(2,'0');
		this.oldVal=this.value;
	}
	this.rBox.lastChild.onchange=function(){
		var num=Number(this.value);
		if (isNaN(num) || num<0 || num>23) {
			alert(words.badInput);
			this.value=this.oldVal;
			return;
		}
		this.value=num.toString().padL(2,'0');
		this.oldVal=this.value;
	}
	this.rBox.lastChild.value=this.time[0];
	this.rBox.lastChild.onchange();

	this.rBox.appendChild(document.createTextNode(':'));
	this.rBox.appendChild(document.createElement('input'));
	this.rBox.lastChild.value=this.date.getMinutes().toString().padL(2,'0');
	this.rBox.lastChild.oldVal=this.rBox.lastChild.value;
	this.rBox.oMin=this.rBox.lastChild;
	this.rBox.oMin.shift=function(n){
		var num=Number(this.value)+n;
		if(num<0) num=59;
		else if(num>59) num=0;
		this.value=num.toString().padL(2,'0');
		this.oldVal=this.value;
	}
	this.rBox.lastChild.onchange=function(){
		var num=Number(this.value);
		if (isNaN(num) || num<0 || num>59) {
			alert(words.badInput);
			this.value=this.oldVal;
			return;
		}
		this.value=num.toString().padL(2,'0');
		this.oldVal=this.value;
	}
	this.rBox.lastChild.value=this.time[1];
	this.rBox.lastChild.onchange();

	this.rBox.appendChild(document.createElement('div'));
	this.rBox.lastChild.setAttribute('class', 'timeCtrl');
	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoDown');
	tmp.onclick=function(e){this.parentNode.parentNode.oHour.shift(-1)};
	this.rBox.lastChild.appendChild(tmp);
	tmp=document.createElement('div');
	tmp.setAttribute('class', 'icoDown');
	tmp.onclick=function(e){this.parentNode.parentNode.oMin.shift(-1)};
	this.rBox.lastChild.appendChild(tmp);

	this.object.appendChild(document.createElement('div'));
	this.object.lastChild.setAttribute('class','buttonLeft');
	this.object.lastChild.style.clear="both";
	this.object.lastChild.style.marginLeft="15px";
	this.object.lastChild.appendChild(document.createTextNode(words.save));

	this.object.lastChild.onmouseup=function(){
		var dt=this.parentNode.instance.date, inp=this.parentNode.instance.rBox.getElementsByTagName('input');
		dt.setHours(Number(inp[0].value));
		dt.setMinutes(Number(inp[1].value));
		this.parentNode.instance.target.setDateTime(dt);
		document.getElementById('smog').style.visibility='hidden';
		document.getElementById('pageBlock').removeChild(this.parentNode);
	};
	this.object.appendChild(document.createElement('div'));
	this.object.lastChild.setAttribute('class','buttonLeft');
	this.object.lastChild.appendChild(document.createTextNode(words.cancel));
	this.object.lastChild.onmouseup=function(){
		document.getElementById('smog').style.visibility='hidden';
		document.getElementById('pageBlock').removeChild(this.parentNode);
	};


	document.getElementById('smog').style.visibility='visible';
	document.getElementById('pageBlock').appendChild(this.object);


	this.goMonth=function(change){
		if(change>0){
			if(this.month.value<11) this.month.value++;
			else{
				this.year.value=Number(this.year.value)+1;
				this.month.value=0;
			}
		}else{
			if(this.month.value>0) this.month.value--;
			else{
				this.year.value=Number(this.year.value)-1;
				this.month.value=11;
			}
		}
		this.showTable();
	}
	this.showTable=function(){
		dt=new Date(Number(this.year.value), Number(this.month.value),1);
		var fromDt=dt.shiftDay(-(dt.getDate()-1)),
			month=dt.getMonth(), dtTime=dt.getTime();
		fromDt=fromDt.shiftDay(-(fromDt.getDay()==0?6:fromDt.getDay()-1))
		this.table.innerHTML='';
		var toDay=today().getTime();
		while(fromDt.getMonth()==month || fromDt.getTime()<dtTime){
			for(i=0; i<7; i++){
				this.table.appendChild(document.createElement('div'));
				this.table.lastChild.appendChild(document.createTextNode(fromDt.getDate().toString()));
				if (i==0)
					this.table.lastChild.style.clear="left";
				if(this.date.getTime()==fromDt.getTime()){
					this.table.lastChild.style.backgroundColor="navy";
					this.table.lastChild.style.color="#fff";
				}else	if(toDay==fromDt.getTime())
						this.table.lastChild.style.backgroundColor="#fda";
				else if(i>4)
					this.table.lastChild.style.backgroundColor='#def';

				this.table.lastChild.date=fromDt;
				if(fromDt.getMonth()!=month){
					this.table.lastChild.style.color='#999';
				}
				fromDt=fromDt.shiftDay(1);
			}
		}
		if(this.object.offsetTop+this.object.offsetHeight>this.object.parentNode.clientHeight)
			this.object.style.top=(this.object.parentNode.clientHeight-this.object.offsetHeight).toString()+'px';
		if(this.object.offsetLeft+this.object.offsetWidth>this.object.parentNode.clientWidth)
			this.object.style.left=(this.object.parentNode.clientWidth-this.object.offsetWidth).toString()+'px';
		this.rBox.childNodes[0].innerHTML=this.date.getDate()+'.'+(this.date.getMonth()+1)+'.'+this.date.getFullYear();
	}



	this.close=function(){
		this.object.parentNode.removeChild(this.object);
		this.target.thisform.onclick=this.oldWsClick;
		this.target.thisform.calObj=null;
		this.target.calendar=null;
	}
	this.showTable();
/*	obj.thisform.calObj=obj;
	obj.thisform.onclick=function(e){
		e=e||window.event;
		var el=e.srcElement || e.target;
		if(el!=this.calObj)
			this.calObj.calendar.close();
	}
*/
}
function md5(str) {
  //  discuss at: http://phpjs.org/functions/md5/
  // original by: Webtoolkit.info (http://www.webtoolkit.info/)
  // improved by: Michael White (http://getsprink.com)
  // improved by: Jack
  // improved by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
  //    input by: Brett Zamir (http://brett-zamir.me)
  // bugfixed by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
  //  depends on: utf8_encode
  //   example 1: md5('Kevin van Zonneveld');
  //   returns 1: '6e658d4bfcb59cc13f96c14450ac40b9'

  var xl;

  var rotateLeft = function(lValue, iShiftBits) {
    return (lValue << iShiftBits) | (lValue >>> (32 - iShiftBits));
  };

  var addUnsigned = function(lX, lY) {
    var lX4, lY4, lX8, lY8, lResult;
    lX8 = (lX & 0x80000000);
    lY8 = (lY & 0x80000000);
    lX4 = (lX & 0x40000000);
    lY4 = (lY & 0x40000000);
    lResult = (lX & 0x3FFFFFFF) + (lY & 0x3FFFFFFF);
    if (lX4 & lY4) {
      return (lResult ^ 0x80000000 ^ lX8 ^ lY8);
    }
    if (lX4 | lY4) {
      if (lResult & 0x40000000) {
        return (lResult ^ 0xC0000000 ^ lX8 ^ lY8);
      } else {
        return (lResult ^ 0x40000000 ^ lX8 ^ lY8);
      }
    } else {
      return (lResult ^ lX8 ^ lY8);
    }
  };

  var _F = function(x, y, z) {
    return (x & y) | ((~x) & z);
  };
  var _G = function(x, y, z) {
    return (x & z) | (y & (~z));
  };
  var _H = function(x, y, z) {
    return (x ^ y ^ z);
  };
  var _I = function(x, y, z) {
    return (y ^ (x | (~z)));
  };

  var _FF = function(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(_F(b, c, d), x), ac));
    return addUnsigned(rotateLeft(a, s), b);
  };

  var _GG = function(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(_G(b, c, d), x), ac));
    return addUnsigned(rotateLeft(a, s), b);
  };

  var _HH = function(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(_H(b, c, d), x), ac));
    return addUnsigned(rotateLeft(a, s), b);
  };

  var _II = function(a, b, c, d, x, s, ac) {
    a = addUnsigned(a, addUnsigned(addUnsigned(_I(b, c, d), x), ac));
    return addUnsigned(rotateLeft(a, s), b);
  };

  var convertToWordArray = function(str) {
    var lWordCount;
    var lMessageLength = str.length;
    var lNumberOfWords_temp1 = lMessageLength + 8;
    var lNumberOfWords_temp2 = (lNumberOfWords_temp1 - (lNumberOfWords_temp1 % 64)) / 64;
    var lNumberOfWords = (lNumberOfWords_temp2 + 1) * 16;
    var lWordArray = new Array(lNumberOfWords - 1);
    var lBytePosition = 0;
    var lByteCount = 0;
    while (lByteCount < lMessageLength) {
      lWordCount = (lByteCount - (lByteCount % 4)) / 4;
      lBytePosition = (lByteCount % 4) * 8;
      lWordArray[lWordCount] = (lWordArray[lWordCount] | (str.charCodeAt(lByteCount) << lBytePosition));
      lByteCount++;
    }
    lWordCount = (lByteCount - (lByteCount % 4)) / 4;
    lBytePosition = (lByteCount % 4) * 8;
    lWordArray[lWordCount] = lWordArray[lWordCount] | (0x80 << lBytePosition);
    lWordArray[lNumberOfWords - 2] = lMessageLength << 3;
    lWordArray[lNumberOfWords - 1] = lMessageLength >>> 29;
    return lWordArray;
  };

  var wordToHex = function(lValue) {
    var wordToHexValue = '',
      wordToHexValue_temp = '',
      lByte, lCount;
    for (lCount = 0; lCount <= 3; lCount++) {
      lByte = (lValue >>> (lCount * 8)) & 255;
      wordToHexValue_temp = '0' + lByte.toString(16);
      wordToHexValue = wordToHexValue + wordToHexValue_temp.substr(wordToHexValue_temp.length - 2, 2);
    }
    return wordToHexValue;
  };

  var x = [],
    k, AA, BB, CC, DD, a, b, c, d, S11 = 7,
    S12 = 12,
    S13 = 17,
    S14 = 22,
    S21 = 5,
    S22 = 9,
    S23 = 14,
    S24 = 20,
    S31 = 4,
    S32 = 11,
    S33 = 16,
    S34 = 23,
    S41 = 6,
    S42 = 10,
    S43 = 15,
    S44 = 21;

  str = utf8_encode(str);
  x = convertToWordArray(str);
  a = 0x67452301;
  b = 0xEFCDAB89;
  c = 0x98BADCFE;
  d = 0x10325476;

  xl = x.length;
  for (k = 0; k < xl; k += 16) {
    AA = a;
    BB = b;
    CC = c;
    DD = d;
    a = _FF(a, b, c, d, x[k + 0], S11, 0xD76AA478);
    d = _FF(d, a, b, c, x[k + 1], S12, 0xE8C7B756);
    c = _FF(c, d, a, b, x[k + 2], S13, 0x242070DB);
    b = _FF(b, c, d, a, x[k + 3], S14, 0xC1BDCEEE);
    a = _FF(a, b, c, d, x[k + 4], S11, 0xF57C0FAF);
    d = _FF(d, a, b, c, x[k + 5], S12, 0x4787C62A);
    c = _FF(c, d, a, b, x[k + 6], S13, 0xA8304613);
    b = _FF(b, c, d, a, x[k + 7], S14, 0xFD469501);
    a = _FF(a, b, c, d, x[k + 8], S11, 0x698098D8);
    d = _FF(d, a, b, c, x[k + 9], S12, 0x8B44F7AF);
    c = _FF(c, d, a, b, x[k + 10], S13, 0xFFFF5BB1);
    b = _FF(b, c, d, a, x[k + 11], S14, 0x895CD7BE);
    a = _FF(a, b, c, d, x[k + 12], S11, 0x6B901122);
    d = _FF(d, a, b, c, x[k + 13], S12, 0xFD987193);
    c = _FF(c, d, a, b, x[k + 14], S13, 0xA679438E);
    b = _FF(b, c, d, a, x[k + 15], S14, 0x49B40821);
    a = _GG(a, b, c, d, x[k + 1], S21, 0xF61E2562);
    d = _GG(d, a, b, c, x[k + 6], S22, 0xC040B340);
    c = _GG(c, d, a, b, x[k + 11], S23, 0x265E5A51);
    b = _GG(b, c, d, a, x[k + 0], S24, 0xE9B6C7AA);
    a = _GG(a, b, c, d, x[k + 5], S21, 0xD62F105D);
    d = _GG(d, a, b, c, x[k + 10], S22, 0x2441453);
    c = _GG(c, d, a, b, x[k + 15], S23, 0xD8A1E681);
    b = _GG(b, c, d, a, x[k + 4], S24, 0xE7D3FBC8);
    a = _GG(a, b, c, d, x[k + 9], S21, 0x21E1CDE6);
    d = _GG(d, a, b, c, x[k + 14], S22, 0xC33707D6);
    c = _GG(c, d, a, b, x[k + 3], S23, 0xF4D50D87);
    b = _GG(b, c, d, a, x[k + 8], S24, 0x455A14ED);
    a = _GG(a, b, c, d, x[k + 13], S21, 0xA9E3E905);
    d = _GG(d, a, b, c, x[k + 2], S22, 0xFCEFA3F8);
    c = _GG(c, d, a, b, x[k + 7], S23, 0x676F02D9);
    b = _GG(b, c, d, a, x[k + 12], S24, 0x8D2A4C8A);
    a = _HH(a, b, c, d, x[k + 5], S31, 0xFFFA3942);
    d = _HH(d, a, b, c, x[k + 8], S32, 0x8771F681);
    c = _HH(c, d, a, b, x[k + 11], S33, 0x6D9D6122);
    b = _HH(b, c, d, a, x[k + 14], S34, 0xFDE5380C);
    a = _HH(a, b, c, d, x[k + 1], S31, 0xA4BEEA44);
    d = _HH(d, a, b, c, x[k + 4], S32, 0x4BDECFA9);
    c = _HH(c, d, a, b, x[k + 7], S33, 0xF6BB4B60);
    b = _HH(b, c, d, a, x[k + 10], S34, 0xBEBFBC70);
    a = _HH(a, b, c, d, x[k + 13], S31, 0x289B7EC6);
    d = _HH(d, a, b, c, x[k + 0], S32, 0xEAA127FA);
    c = _HH(c, d, a, b, x[k + 3], S33, 0xD4EF3085);
    b = _HH(b, c, d, a, x[k + 6], S34, 0x4881D05);
    a = _HH(a, b, c, d, x[k + 9], S31, 0xD9D4D039);
    d = _HH(d, a, b, c, x[k + 12], S32, 0xE6DB99E5);
    c = _HH(c, d, a, b, x[k + 15], S33, 0x1FA27CF8);
    b = _HH(b, c, d, a, x[k + 2], S34, 0xC4AC5665);
    a = _II(a, b, c, d, x[k + 0], S41, 0xF4292244);
    d = _II(d, a, b, c, x[k + 7], S42, 0x432AFF97);
    c = _II(c, d, a, b, x[k + 14], S43, 0xAB9423A7);
    b = _II(b, c, d, a, x[k + 5], S44, 0xFC93A039);
    a = _II(a, b, c, d, x[k + 12], S41, 0x655B59C3);
    d = _II(d, a, b, c, x[k + 3], S42, 0x8F0CCC92);
    c = _II(c, d, a, b, x[k + 10], S43, 0xFFEFF47D);
    b = _II(b, c, d, a, x[k + 1], S44, 0x85845DD1);
    a = _II(a, b, c, d, x[k + 8], S41, 0x6FA87E4F);
    d = _II(d, a, b, c, x[k + 15], S42, 0xFE2CE6E0);
    c = _II(c, d, a, b, x[k + 6], S43, 0xA3014314);
    b = _II(b, c, d, a, x[k + 13], S44, 0x4E0811A1);
    a = _II(a, b, c, d, x[k + 4], S41, 0xF7537E82);
    d = _II(d, a, b, c, x[k + 11], S42, 0xBD3AF235);
    c = _II(c, d, a, b, x[k + 2], S43, 0x2AD7D2BB);
    b = _II(b, c, d, a, x[k + 9], S44, 0xEB86D391);
    a = addUnsigned(a, AA);
    b = addUnsigned(b, BB);
    c = addUnsigned(c, CC);
    d = addUnsigned(d, DD);
  }

  var temp = wordToHex(a) + wordToHex(b) + wordToHex(c) + wordToHex(d);

  return temp.toLowerCase();
}
function utf8_encode(argString) {
  //  discuss at: http://phpjs.org/functions/utf8_encode/
  // original by: Webtoolkit.info (http://www.webtoolkit.info/)
  // improved by: Kevin van Zonneveld (http://kevin.vanzonneveld.net)
  // improved by: sowberry
  // improved by: Jack
  // improved by: Yves Sucaet
  // improved by: kirilloid
  // bugfixed by: Onno Marsman
  // bugfixed by: Onno Marsman
  // bugfixed by: Ulrich
  // bugfixed by: Rafal Kukawski
  // bugfixed by: kirilloid
  //   example 1: utf8_encode('Kevin van Zonneveld');
  //   returns 1: 'Kevin van Zonneveld'

  if (argString === null || typeof argString === 'undefined') {
    return '';
  }

  // .replace(/\r\n/g, "\n").replace(/\r/g, "\n");
  var string = (argString + '');
  var utftext = '',
    start, end, stringl = 0;

  start = end = 0;
  stringl = string.length;
  for (var n = 0; n < stringl; n++) {
    var c1 = string.charCodeAt(n);
    var enc = null;

    if (c1 < 128) {
      end++;
    } else if (c1 > 127 && c1 < 2048) {
      enc = String.fromCharCode(
        (c1 >> 6) | 192, (c1 & 63) | 128
      );
    } else if ((c1 & 0xF800) != 0xD800) {
      enc = String.fromCharCode(
        (c1 >> 12) | 224, ((c1 >> 6) & 63) | 128, (c1 & 63) | 128
      );
    } else {
      // surrogate pairs
      if ((c1 & 0xFC00) != 0xD800) {
        throw new RangeError('Unmatched trail surrogate at ' + n);
      }
      var c2 = string.charCodeAt(++n);
      if ((c2 & 0xFC00) != 0xDC00) {
        throw new RangeError('Unmatched lead surrogate at ' + (n - 1));
      }
      c1 = ((c1 & 0x3FF) << 10) + (c2 & 0x3FF) + 0x10000;
      enc = String.fromCharCode(
        (c1 >> 18) | 240, ((c1 >> 12) & 63) | 128, ((c1 >> 6) & 63) | 128, (c1 & 63) | 128
      );
    }
    if (enc !== null) {
      if (end > start) {
        utftext += string.slice(start, end);
      }
      utftext += enc;
      start = end = n + 1;
    }
  }

  if (end > start) {
    utftext += string.slice(start, stringl);
  }

  return utftext;
}

function createNetSetup() {
	var el=createElement('div', 'netSetup');
	function setValue(arr) {
		this.value=arr[0]+'.'+arr[1]+'.'+arr[2]+'.'+arr[3];
/*		this.value=(val >>> 24).toString()+'.'+
			((val >>> 16)&0xff).toString()+'.'+
			((val >>> 8)&0xff).toString()+'.'+
			(val&0xff).toString();
*/
	}

	el.innerHTML='<h3>'+words['netSetup']+'</h3>'+
		'<div class="frame"><div id="ip4type1" name="ip4type1" idVal="dhcp" class="radioOn">'+words['getFromDHCP']+'</div>'+
		'<div id="ip4type2" name="ip4type2" class="radioOff">'+words['useNextValues']+'</div>'+
		'<span>'+words['addressIP']+'</span><input type="text" idVal="ip" disabled/>'+
		'<span>'+words['subnetMask']+'</span><input type="text" idVal="ip4mask" disabled/>'+
		'<span>'+words['serverDNS']+'</span><input type="text" idVal="ip4dns1" disabled/>'+
		'<span>'+words['defaultGW']+'</span><input type="text" idVal="ip4gw" disabled/>'+
		'<div class="button" style="margin-top:20px">'+words['save']+'</div>'+
		'<div class="button" style="margin-top:5px">'+words['refresh']+'</div>'+
		'</div>';
	//code

	for(var i=0; i<el.childNodes[1].childNodes.length; i++)
		if(el.childNodes[1].childNodes[i].hasAttribute('idVal'))
			el.childNodes[1].childNodes[i].setValue=setValue;
	el.childNodes[1].childNodes[0].setValue=function(val){
		this.setAttribute('class',val?'radioOn':'radioOff');
		this.nextSibling.setAttribute('class',val?'radioOff':'radioOn');
		var els=this.parentNode.getElementsByTagName('input'), i;
		for(i=0; i<els.length; i++)
			if(val){
				els[i].setAttribute('disabled','1');
			}else{
				els[i].removeAttribute('disabled');
			}
	}
	el.childNodes[1].childNodes[0].onclick=function(){
		this.setValue(1);
	}
	el.childNodes[1].childNodes[1].onclick=function(){
		this.previousSibling.setValue(0);
	}
	el.childNodes[1].lastChild.previousSibling.onclick=function(){
		var isDHCP=this.parentNode.firstChild.getAttribute('class')=='radioOn',
			pars='dhcp='+(isDHCP?'1':'0'), vals=[],
			els=this.parentNode.getElementsByTagName('input'),
			err=false, i, j, key, txt, val, arr,
			errMsg={ip:words['addressIP'], ip4mask:words['subnetMask'],ip4dns1:words['serverDNS'],ip4gw:words['defaultGW']};
		for(i=0; i<els.length;i++){
			key=els[i].getAttribute('idVal');
			if(errMsg[key]){
				txt=els[i].value;
				val==false;
				if(txt.replace(/[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}/,'').length==0){
					arr=txt.split('.');
					if (arr.length==4) {
						val=0;
						for(j=0;j<4;j++){
							arr[j]=Number(arr[j]);
							val+=(arr[j]*Math.pow(256,3-j));
						}
						vals[key]=[arr[0]+(arr[1]<<8), arr[2]+(arr[3]<<8)];
					}
				}
				if((val)) {
					val=val.toString();
					pars+='&'+key+'='+'000000000'.substring(0,10-val.length)+val;
				}else{
					pars='';
					break;
				}
			}
		}
		if(pars==''){
			alert(words['badInput']+' - '+errMsg[key])
		}else{
			send2Unit(pars);
			console.log(pars)
			pars=getUrlPar('H12200', isDHCP?1:0)+	// dhcp
				getUrlPar('H12202', vals.ip[0])+getUrlPar('H12203', vals.ip[1])+
				getUrlPar('H12204', vals.ip4mask[0])+getUrlPar('H12205', vals.ip4mask[1])+
				getUrlPar('H12206', vals.ip4gw[0])+getUrlPar('H12207', vals.ip4gw[1])+
				getUrlPar('H12208', vals.ip4dns1[0])+getUrlPar('H12209', vals.ip4dns1[1]);
			setTimeout(function() {send2Unit(pars, urlDataSet);},500);
			showOK();
		}
	}
	el.childNodes[1].lastChild.onclick=function(){
		this.parentNode.parentNode.dataLoaded=false;
		rq('getSetting');
	}
	el.showValues=function(){
		if (!(this.dataLoaded)) {
			var childs=this.childNodes[1].childNodes, i,
				vals={dhcp:values.H12200,
					ip:val2Arr(values.H12202, values.H12203),
					ip4mask:val2Arr(values.H12204, values.H12205),
					ip4gw:val2Arr(values.H12206, values.H12207),
					ip4dns1:val2Arr(values.H12208, values.H12209)};
			for(i=0; i<childs.length;i++){
				if (childs[i].hasAttribute('idVal')) {
					childs[i].setValue(vals[childs[i].getAttribute('idVal')]);
				}
			}
			this.dataLoaded=true;
		}
	}
	return el;
}

function val2Arr(low, high){
	if(high<0) high+=65536;
	if(low<0) low+=65536;
	low=(low.toString(16).padL(4,'0'));
	high=(high.toString(16).padL(4,'0'));
	return [parseInt(low.substr(2,2),16),parseInt(low.substr(0,2),16),parseInt(high.substr(2,2),16),parseInt(high.substr(0,2),16)];
}

function showValues() {
	var oContent=document.getElementById('content'), oBoxs, isSet=false;
	if (oContent.childNodes.length==1 && oContent.childNodes[0].showValues) {
		oContent.childNodes[0].showValues();
		return;
	}
	if(oContent.getAttribute('autoRefresh')=='1' || oContent.getAttribute('dataLoaded')=='0'){
		oBoxs=oContent.getElementsByTagName('*');
		for(var j=0; j<oBoxs.length; j++) {
			if(oBoxs[j].getAttribute('idVal') && typeof(values[oBoxs[j].getAttribute('idVal')])!=='undefined') {
				if(oBoxs[j].setValue){
					oBoxs[j].setValue(values[oBoxs[j].getAttribute('idVal')], true);
					isSet=true;
				}
				if(oBoxs[j].setEnabled){
					oBoxs[j].setEnabled(checkRule(oBoxs[j].getAttribute('idVal'), true))
					isSet=true;
				}
			}else if(oBoxs[j].getAttribute('idVal') && oBoxs[j].getAttribute('idVal').match(',')){
				keys=oBoxs[j].getAttribute('idVal').split(',');
				isSet=true;
				for(var k=0;k<keys.length;k++){
					if(typeof(values[keys[k]])!=='undefined')
						oBoxs[j].setValue(keys[k], values[keys[k]], true);
				}

			}
			if(oBoxs[j].getAttribute('idValW') && typeof(values[oBoxs[j].getAttribute('idValW')])!=='undefined') {
				oBoxs[j].setValueW(values[oBoxs[j].getAttribute('idValW')], true);
			}
		}
		if (isSet) {
			oContent.setAttribute('dataLoaded', '1');
		}
	}
}
function createWindow(caption, id, parent) {
	if(!(id)) id=randStr(5);
	if(!(parent)) parent=document.body;
	oWnd=createElement('div', 'window', null, {id:id, caption:caption, modal:''});
	parent.appendChild(oWnd);
	oWnd.modal=true;
	var htm='<div class="header">'+caption+'</div><div id="'+oWnd.id+'_content"></div><div class="footer" id="'+oWnd.id+'_footer"></div>';
	oWnd.innerHTML=htm;
	oWnd.setAttribute('close','');
	oWnd.close=function() {
		document.getElementById('smog').style.visibility='hidden';
	   this.parentNode.removeChild(this)
	};
	oWnd.setAttribute('workSpace','');
	oWnd.workSpace=oWnd.getElementsByTagName('div')[1];
	oWnd.setAttribute('footer','');
   oWnd.footer=oWnd.getElementsByTagName('div')[2];
	oWnd.workSpace.setAttribute('style', 'position: absolute; left:8px; right:12px; top:40px; bottom:0px; overflow:auto;');
	oWnd.footer.setAttribute('style', 'position: absolute; height:33px; left:0px; right:20px; bottom:0px; overflow:hidden');

	oWnd.onmousedown=function(e){
		e=window.event || e;
		if (e.clientY-this.offsetTop>30) return;

		this.style.opacity = 0.75;
		this.style.filter = 'alpha(opacity=75)';

		this.smog=document.getElementById('smog');
		this.smog.dialogWnd={o:this, x:e.screenX-this.offsetLeft, y:e.screenY-this.offsetTop};
		this.smog.onmousemove=function(e){
			if(this.dialogWnd) {
				this.dialogWnd.o.style.left=e.screenX-this.dialogWnd.x+'px';
				this.dialogWnd.o.style.top=e.screenY-this.dialogWnd.y+'px';
			}else{
				this.onmouseup();
			}
		}
		this.smog.onmouseup=function(e){

			this.dialogWnd.o.style.opacity = 1;
			this.dialogWnd.o.style.filter = '';
			this.dialogWnd.o.onmousemove=null;
			this.dialogWnd.o.onmouseup=null;
			this.onmousemove=null;
			this.onmouseup=null;
			delete this.dialogWnd;
		}
		this.onmousemove=function(e){
			this.smog.onmousemove(e);
		}
		this.onmouseup=function(e){
			this.smog.onmouseup(e);
		}
	}

	oWnd.setAttribute('setContent','');
	oWnd.setContent=function(content, autoCenter, add) {
      this.workSpace.style.position="relative";
      if(typeof(content)=='string') {
	      this.workSpace.innerHTML=content;
		} else {
			if(content!==null) {
				if(add===null || !add) this.workSpace.innerHTML='';
			   this.workSpace.appendChild(content);
			}
		}
		this.setContentSize(this.workSpace.scrollWidth, this.workSpace.scrollHeight, autoCenter);
      this.workSpace.style.position="absolute";
	}
	oWnd.setAttribute('setContentSize','');
	oWnd.setContentSize=function(width, height, autoCenter) {
		width=Math.max(width, 480);
		footHeight=(this.modal?Number(this.footer.style.height):0)
		if(height>0) {
			this.style.height=Math.min(height+65, document.getElementById('smog').clientHeight-10).toString()+'px';
		}
		if(width>0){
			this.style.width=Math.min(20+width, this.parentNode.clientWidth).toString()+'px';
		}
		if(autoCenter) {
			this.center();
		}
	}
	oWnd.setAttribute('setFooter','');
	oWnd.setFooter=function(content, add) {
      if(typeof(content)=='string') {
	      this.footer.innerHTML=content;
		} else {
			if(!(add)) this.footer.innerHTML='';
		   this.footer.appendChild(content);
		}
	}

	oWnd.setAttribute('setStyle','');
	oWnd.setStyle=function(style) {
      this.style=style;
	}

	oWnd.setAttribute('center','');
	oWnd.center=function() {
		this.style.left=((parseInt(this.parentNode.offsetWidth)-parseInt(this.offsetWidth))/2).toString()+'px';
		this.style.top=((parseInt(document.getElementById('smog').offsetHeight)-parseInt(this.offsetHeight))/2).toString()+'px';
	}
	oWnd.setAttribute('show','');
	oWnd.show=function() {
		document.getElementById('smog').style.visibility='visible';
		this.style.visibility="visible";
		var c=this.getAttribute('class');
		this.setAttribute('class','');
		this.setAttribute('class',c);
	}
	return oWnd;
}
// * Added
function isset(v) {
	switch (typeof(v)) {
		case 'undefined':
			return false;
		case 'object':
			return(v===null?false:true);
	}
	return true;
}

function newMonCal(nM, nY, days, add6Row){
	var el=document.createElement('div'), nD=1, nWd=1, obj, rows=0,
		boxSt='border:1px solid black; height:16px; width:19px; margin:0 -1px -1px 0;';
	el.setAttribute('class', 'calMonth');

	el.oDays=[];
	el.appendChild(document.createElement('div'));
	el.lastChild.setAttribute('class','calMonthHdr');
	if((days)) el.lastChild.appendChild(document.createTextNode(words['monthName'+(nM+1)]+' '+nY));
	else el.lastChild.appendChild(document.createTextNode(words['monthName'+(nM+1)]));
	d=new Date(nY, nM, nD,0,0,0,0);
	if(d.getDay()!==(nWd<7?nWd:0)){
		while(d.getDay()!==(nWd<7?nWd:0)){
			el.appendChild(document.createElement('div'));
			el.lastChild.setAttribute('class', 'calMonthBox');
			nWd++;
		}
		rows=1;
	}
	while(d.getMonth()==nM){
		if (d.getDay()==1) rows++;
		obj=document.createElement('div');
		el.appendChild(obj);
		el.lastChild.setAttribute('class', 'calMonthDay');
		obj.appendChild(document.createTextNode(nD));
		el.oDays.push(obj);
		if ((days)){
			if (days.map(Number).indexOf(+d)>=0) {
				obj.date=new Date(d.getTime());
				obj.setAttribute('active','1');
				obj.onclick=function(){this.parentNode.parentNode.parentNode.onDayClick(this)};
				obj.onmousemove=function(){
					if(this.parentNode.parentNode.parentNode.onDayOver)
						this.parentNode.parentNode.parentNode.onDayOver(this);
				};

			}
		}else{
			obj.month=nM;
			obj.date=nD;
			obj.onclick=function(){this.parentNode.parentNode.onDayClick(this.month, this.date)};
			obj.onmousemove=function(){this.parentNode.parentNode.onDayMove(this.month, this.date)};
		}
		nD++;
		d.setDate(nD);
	}
	nWd=d.shiftDay(-1).getDay();
	if (nWd==0) nWd=7;
	while(nWd<7){
		el.appendChild(document.createElement('div'));
		el.lastChild.setAttribute('class', 'calMonthBox');
		nWd++;
	}
	if((add6Row))
		while(rows<6){
			el.appendChild(document.createElement('div'));
			el.lastChild.setAttribute('class', 'calEmptyWeek');
			rows++;
		}
	return el;
}

function getCookie(cname) {
	var name = cname + "=", ca;
	if ((document.cookie)) {
		ca = decodeURIComponent(document.cookie).split(';');
		for(var i=0; i<ca.length; i++) {
			var c = ca[i];
			while(c.charAt(0)==' ') c = c.substring(1);
			if (c.indexOf(name) == 0) return c.substring(name.length,c.length);
		}
	}
	return "";
}
function setCookie(name,value,days) {
    var expires = "";
    if (days) {
        var date = new Date();
        date.setTime(date.getTime() + (days*24*60*60*1000));
        expires = "; expires=" + date.toUTCString();
    }
    document.cookie = name + "=" + (value || "")  + expires + "; path=RD5/";
}

function delCookie(cname) {
//    document.cookie = cname+'=;';
    document.cookie = cname+'=;path=RD5/';
}
function loginSave(form){
	var inputs=form.getElementsByTagName('input');
	if(inputs[2].checked){
		var exp=new Date();
		exp.setFullYear(exp.getFullYear()+1);
		document.cookie="autoLogin="+encodeURIComponent(inputs[0].value+"\b"+inputs[1].value)+";expires="+exp.toUTCString()+";path=/";
	}else{
		document.cookie="autoLogin=;expires=Thu, 01 Jan 1970 00:00:00 UTC;";
	}
}
function getBinData(url) {
	var req = new XMLHttpRequest();
	req.open('GET', url, false);
	req.overrideMimeType('application/octet-stream; charset=x-user-defined');
	req.send(null);
	if (req.status != 200) return '';
	return req.response;
}
