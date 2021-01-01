//<!-- RpDZT -->
/* status :
	0 - start
	1 - values loaded
	2 - based content loaded
	3 - translation loaded
	4 - user setting loaded
*/
//	idLNG='H11200',

var webMode=false,
	demoMode=false,
	idLNG='H10900',
	idLINE='H10513',
	paramKeys={
		power:"H11001",
		mode:"H11000",
		zone:"H11011",
		temp:"I10202",
		isTemp:"C11200"
	},
	testLng=false,
	pwrType, tempType='Temp100', tempIZT='TempIZT',
	server='',lastPrg='vzt';

if(webMode){
var server='',
	urlLogin='config/login.php',
	urlPasswd='config/passwd.php',
	urlDataRead='config/get.php?file=xml.xml',
	urlDataSet='config/xml.cgi',
	urlIpSet='config/ip.cgi',
	urlAlarms='config/get.php?file=alarms.xml',
	urlCfg='cfgdir.php',
	urlWeekPrg={RTS:{vzt:['config/get.php?file=rtssetup.xml', 'config/set.php?file=rtssetup.cgi'],
						izt:['config/get.php?file=rgtssetup.xml', 'config/set.php?file=rgtssetup.cgi']}
					,RNS:{vzt:['config/get.php?file=rnssetup.xml', 'config/set.php?file=rnssetup.cgi'],
						izt:['config/get.php?file=rgnssetup.xml', 'config/set.php?file=rgnssetup.cgi']}};
}else{
	var server='',
	urlLogin='config/login.cgi',
	urlPasswd='config/passwd.cgi',
	urlDataRead='config/xml.xml',
	urlDataSet='config/xml.cgi',
	urlIpSet='config/ip.cgi',
	urlAlarms='config/alarms.xml',
	urlCfg='cfgdir.xml',
	urlWeekPrg={RTS:{vzt:['config/rtssetup.xml', 'config/rtssetup.cgi'],
						izt:['config/rgtssetup.xml', 'config/rgtssetup.cgi']}
					,RNS:{vzt:['config/rnssetup.xml', 'config/rnssetup.cgi'],
						izt:['config/rgnssetup.xml', 'config/rgnssetup.cgi']}};
	;

}
function rq(lAction, par) {
	oRequest='';
	if (window.XMLHttpRequest) oRequest=new XMLHttpRequest();
	else oRequest=new ActiveXObject("Microsoft.XMLHTTP");
	oRequest.readystate=0;
	oRequest.onreadystatechange=rqAccept;
	var lParms=false, dataFile=false;
	switch(lAction) {
		case 'setSetting':
			lParms=par;
			if(body.menus[activePage] && body.menus[activePage].menus[activeContent].content.target){
				dataFile=body.menus[activePage].menus[activeContent].content.target;
				send2Unit(par, dataFile);
				dataFile=false;
			}
			else send2Unit(par);
			break;
		case 'getSetting':
			if(body.menus[activePage] && body.menus[activePage].menus[activeContent].content.source)
				dataFile=body.menus[activePage].menus[activeContent].content.source;
			else dataFile=urlDataRead;
			dataFile+='?auth='+user.auth+'&'+randStr(2);
			break;
		default:
			alert('Unknown action: '+lAction);
			break;
	}
	if(dataFile) {
		oRequest.target=dataFile;
		if(lParms && comm.demo) alert(words['notInDemo']);
		else {
			oRequest.open((lParms?'post':'get'), dataFile, true);
			if (lParms) {
				if(comm.debug) alert("Target: "+dataFile+"\nParametry: "+lParms);
				oRequest.setRequestHeader("Content-type", "application/x-www-form-urlencoded; charset=utf-8");
				oRequest.setRequestHeader("Content-length", lParms.length);
				oRequest.setRequestHeader("Connection", "close");

				oRequest.send(lParms);
//				rq('getSetting');
				setTimeout("rq('getSetting')",500);
			} else {
				oRequest.send(null);
			}
		}
	}
}

function rqAccept() {
	if(this.readyState == 4){
		if(this.status == 200){
			if(this.responseXML && this.responseXML.getElementsByTagName('root').item(0)) {
				xmldoc = this.responseXML;
			} else {
				if (window.DOMParser){
					parser=new DOMParser();
					var xmldoc=parser.parseFromString(this.responseText,"text/xml");
				}else {
					var xmldoc=new ActiveXObject("Microsoft.XMLDOM");
					xmldoc.async="false";
					xmldoc.loadXML(this.responseText);
				}
			}
			root=xmldoc.documentElement;
			if(root){
//			alert(this.responseText);
				for (var iNode = 0; iNode < root.childNodes.length; iNode++) {
					var node = root.childNodes.item(iNode);
					if(node.nodeType==1){
						switch (node.nodeName) {
							case '#text':
								break;
							case 'RD5WEB':
							case 'RD5':
								loadRD5Values(node);
								showValues();
								break;
							case 'texts':
								loadTexts(node);
								showValues();
								break;
							case 'rnsset':
							case 'rtsset':
								values[node.nodeName]=loadRSVals(node);
								showRSVals(values[node.nodeName]);
								break;
							case 'rgrtsset':
							case 'rgrnsset':
								values[node.nodeName]=loadRGSVals(node);
								showRGSVals(values[node.nodeName]);
								break;
							case 'comm':
								comm.demo=node.getAttribute('demo')=='1';
								comm.debug=node.getAttribute('debug')=='1';
								break;
							case 'sourcetext':
								break;
							case 'errors':
								break;
							case 'head':
							case 'body':
								console.log('Request error',this.target,this.responseText);
								break;
							default:
								if(webMode){
									alert('XML processing for '+node.nodeName+" is not defined! \n"+this.target+' '+ this.responseText);
								}
								break;
						}
					}
				}
			}else{
				alert("Faulty XML \n"+this.responseText);
			}
		}else{
			alert("The HTTP request is not proceeded. ("+this.status+")\n"+this.responseText);
}	}	}


function loadRSVals(node) {
	var days=new Array();
	for(var i=0; i<node.childNodes.length; i++) {
		if(node.childNodes[i].nodeName=='day') {
			var day=parseInt(node.childNodes[i].getAttribute('id'));
			days[day]=new Array();
			eval("var arrRec="+ node.childNodes[i].getElementsByTagName('aircond')[0].childNodes[0].nodeValue+';');
			days[day]['VZT']=new Array();
			// 0		1		 2					3		4
			// mode, power, temperature, zone, 'hh:mm'
			for(var n=0; n<arrRec.length; n++) {
				days[day]['VZT'][n]=new Array();
				days[day]['VZT'][n][0]=formatTime(arrRec[n][4]);
				days[day]['VZT'][n][1]=arrRec[n][1];	// pwr
				days[day]['VZT'][n][2]=arrRec[n][0];	// mode
				days[day]['VZT'][n][3]=arrRec[n][3];	// zone
				days[day]['VZT'][n][4]=arrRec[n][2];	// temp
			}
		}
	}
	return days;
}
function loadRGSVals(node) {
	var days=new Array();
	for(var i=0; i<node.childNodes.length; i++) {
		if(node.childNodes[i].nodeName=='day') {
			var day=parseInt(node.childNodes[i].getAttribute('id'));
			days[day]=new Array();
			eval("var arrRec="+ node.childNodes[i].getElementsByTagName('aircond')[0].childNodes[0].nodeValue+';');
			days[day]['IZT']=new Array();
			// 0		1		 2					3		4
			// mode, power, temperature, zone, 'hh:mm'
			for(var n=0; n<arrRec.length; n++) {
				days[day]['IZT'][n]=new Array();
				days[day]['IZT'][n][0]=formatTime(arrRec[n][2]);
				days[day]['IZT'][n][1]=arrRec[n][0];	// 1.temp
				days[day]['IZT'][n][2]=arrRec[n][1];	// 2.temp
			}
		}
	}
	return days;
}

function showRSVals(vals) {
	showGraphs(vals);
	var arrName='VZT';

	var i=0;
	if(vals[activeDay] && vals[activeDay][arrName]){
		for(i=0; i<vals[activeDay][arrName].length; i++) {
			var el=document.getElementById('recVZT'+i.toString());
			var divs=el.getElementsByTagName('div');
			el.setAttribute('class', 'rec');
			divs[0].innerHTML=words['record']+' '+(i+1).toString();

			el.setAttribute('recType',arrName);
			divs[2].innerHTML=options[pwrType].display(vals[activeDay][arrName][i][1]);
			divs[3].innerHTML=options[modeType].display(vals[activeDay][arrName][i][2]);
			divs[4].innerHTML=options[params[paramKeys['zone']].options].display(vals[activeDay][arrName][i][3]);
			divs[5].innerHTML=options[tempType].display(vals[activeDay][arrName][i][4]);

			divs[divs.length-1].innerHTML=vals[activeDay][arrName][i][0];
			el.setAttribute('values','');
			el.values=vals[activeDay][arrName][i];
		}
	}

	for(i; i<8; i++) {
		var el=document.getElementById('recVZT'+i.toString());
		var divs=el.getElementsByTagName('div');
		el.setAttribute('recType',arrName);
		el.setAttribute('values','');
		el.values=new Array();
		el.values[0]='0:00';
//		if(arrName=='airCond') {
			el.values[1]=options[pwrType].initial;
			el.values[2]=options[modeType].initial;
			el.values[3]=options[params[paramKeys['zone']].options].initial;
			divs[2].innerHTML='';
			divs[3].innerHTML='';
			divs[4].innerHTML='';
			divs[5].innerHTML='';
/*		} else {
			el.values[1]=options[tempOpt].initial;
			divs[2].innerHTML='';
			divs[3].innerHTML='';
		}
*/
		el.setAttribute('class', 'recD');
	}
}

function showRGSVals(vals) {
	showGraphs(vals, true);
	var arrName='IZT';

	var i=0;
	if(vals[activeDay] && vals[activeDay][arrName]){
		for(i=0; i<vals[activeDay][arrName].length; i++) {
			var el=document.getElementById('recIZT'+i.toString());
			var divs=el.getElementsByTagName('div');
			el.setAttribute('class', 'rec');
			divs[0].innerHTML=words['record']+' '+(i+1).toString();
			el.setAttribute('recType',arrName);
			divs[2].innerHTML=options[tempIZT].display(vals[activeDay][arrName][i][1]);
			divs[3].innerHTML=options[tempIZT].display(vals[activeDay][arrName][i][2]);
			divs[divs.length-1].innerHTML=vals[activeDay][arrName][i][0];
			el.setAttribute('values','');
			el.values=vals[activeDay][arrName][i];
		}
	}

	for(i; i<4; i++) {
		var el=document.getElementById('recIZT'+i.toString());
		var divs=el.getElementsByTagName('div');
		el.setAttribute('recType',arrName);
		el.setAttribute('values','');
		el.values=new Array();
		el.values[0]='0:00';
		el.values[1]=options[tempIZT].initial;
		el.values[2]=options[tempIZT].initial;
		divs[2].innerHTML='';
		divs[3].innerHTML='';
		divs[4].innerHTML='';
		el.setAttribute('class', 'recD');
	}
}

function clearGraphs(prg) {
	var els=document.querySelectorAll('.graphLine, .graphBlock');
	for(var i=0; i<els.length; i++)
		els[i].parentNode.removeChild(els[i]);
}

function showGraphs(vals, forIZT) {
	if (forIZT) {
		var tops=showGraph(vals, 'IZT', 1,0, document.getElementById('graphIZT0'));
		showGraph(vals, 'IZT', 2,0, document.getElementById('graphIZT0'), tops);
	}else{
		showGraph(vals, 'VZT', 1,0, document.getElementById('graphVZT0'));
		showGraph(vals, 'VZT', 2,0, document.getElementById('graphVZT1'));
		showGraph(vals, 'VZT', 3,0, document.getElementById('graphVZT2'));
		if(document.getElementById('graphVZT3'))
			showGraph(vals, 'VZT', 4,0, document.getElementById('graphVZT3'));
	}
}
function showGraph(vals, arrName, arrPos, tmPos, elGr, tops) {
	if(!(tops)) tops=prepareTops(elGr);


	var points=new Array();
	points[0]=[0,0];
	var prevVal=getLastACTVal(vals, arrName, arrPos, tmPos, activeDay);
	if(elGr.opY.type=='range' || elGr.opY.type=='rangeEnum') { // XY graph
		for(var j=1; j<tops.length && tops[j].value<prevVal; j++){};
		points[0][1]=tops[j-1].top+(tops[j-1].value-prevVal)*((tops[j-1].top-tops[j].top)/(tops[j].value-tops[j-1].value));
		if(vals[activeDay] && vals[activeDay][arrName])
			for(var i=0; i<vals[activeDay][arrName].length; i++) {
				points[i+1]=new Array();
				points[i+1][0]=cTime2Hours(vals[activeDay][arrName][i][tmPos]);
				for(var j=1; j<tops.length-1 && tops[j].value<vals[activeDay][arrName][i][arrPos]; j++){};
				points[i+1][1]=tops[j-1].top+(tops[j-1].value-vals[activeDay][arrName][i][arrPos])*((tops[j-1].top-tops[j].top)/(tops[j].value-tops[j-1].value));
			}
		drawGraph(elGr, points);
	} else { // color graph
		points[0][1]=prevVal;
		if(vals[activeDay] && vals[activeDay][arrName])
			for(var i=0; i<vals[activeDay][arrName].length; i++) {
				points[i+1]=new Array();
				points[i+1][0]=cTime2Hours(vals[activeDay][arrName][i][tmPos]);
				points[i+1][1]=vals[activeDay][arrName][i][arrPos];
			}
		fillGraph(elGr, points);
	}
	return tops;
}

function getLastACTVal(vals, arrName, arrPos, tmPos, nDay) {
	var find=false;
	while(true) {
		nDay=(nDay==0?6:nDay-1);
		if(vals[nDay]){
			return vals[nDay][arrName][vals[nDay][arrName].length-1][arrPos];
		}
	}
}
function prepareTops(elGr) {
	var tops=new Array(), divs=elGr.getElementsByTagName('div'), i;
	for(i=divs.length-1; i>=0; i--) {
		if(divs[i].getAttribute('class')=='graphRow') {
			tops.push({value:Number(divs[i].getAttribute('value')),top:divs[i].offsetTop});
		} else if(divs[i].getAttribute('class')=='graphBlock' || divs[i].getAttribute('class')=='graphLine')
			divs[i].parentNode.removeChild(divs[i]);
	}
	return tops;
}
function fillGraph(elGr, points) {

	var pattern=document.createElement('div'),
		lStart=elGr.firstChild.offsetLeft-1, tmp, lft;

	pattern.setAttribute('class','graphBlock');
	pattern.style.top=elGr.childNodes[0].style.top;
	pattern.style.height=elGr.childNodes[0].style.height;
	for(var i=0; i<points.length;i++) {
		tmp=pattern.cloneNode(false);
		tmp.style.backgroundColor=elGr.opY.values[points[i][1]].color;
		tmp.title=elGr.opY.values[points[i][1]].title;
		lft=(25.58*points[i][0]+lStart)
		tmp.style.left=lft.toString()+'px';
		tmp.style.width=(25.58*(i==points.length-1?24:points[i+1][0])+lStart+1-lft).toString()+'px';
		elGr.appendChild(tmp);
		if(i==0) pattern.style.backgroundImage="none";
	}
}


function drawGraph(elGr, points) {
	var lStart=elGr.firstChild.offsetLeft-1, tmp, lft;
	for(var i=0; i<points.length;i++) {
		tmp=document.createElement('div');
		tmp.setAttribute('class', 'graphLine');
		tmp.style.borderLeftStyle='solid';
		if(i==0) {
			tmp.style.top=(points[i][1]).toString()+'px';
			tmp.style.borderTopStyle='dotted';
		} else {
			tmp.style.top=Math.min(points[i-1][1],points[i][1]).toString()+'px';
			tmp.style.height=Math.abs(points[i-1][1]-points[i][1]).toString()+'px';
			if(points[i-1][1]<points[i][1]) {tmp.style.borderBottomStyle='solid';}
			else {tmp.style.borderTopStyle='solid';}
		}
		lft=(25.58*points[i][0]+lStart)
		tmp.style.left=lft.toString()+'px';
		tmp.style.width=(25.58*(i==points.length-1?24:points[i+1][0])+lStart-lft).toString()+'px';
		elGr.appendChild(tmp);
	}
}

function cTime2Hours(str) {
	var delim=str.indexOf(':')
 return parseFloat(str.substr(0,delim))+parseFloat(str.substr(delim+1,2))/60;
}


function loadTexts(node) {
	if(node){
		var childNodes=node.getElementsByTagName('i'), key, value;
		for(var i=0; i<childNodes.length; i++) {
			key=childNodes[i].getAttribute('id');
			value=unescape(childNodes[i].getAttribute('value'));
			values[key]=value;
		}
		document.getElementById('pageTitle').getElementsByTagName('h2')[0].innerHTML='';
		if ((values.UnitName))
			document.getElementById('pageTitle').getElementsByTagName('h2')[0].appendChild(document.createTextNode(values.UnitName));
}}

function loadRD5Values(node, init) {
var key, value;
	if(node){
		var childNodes=node.getElementsByTagName('O');
		for(var i=0; i<childNodes.length; i++) {
			key=childNodes[i].getAttribute('I');
			value=childNodes[i].getAttribute('V');
			values[key]=parseInt(value);
			if(values[key]>32767) values[key]-=65536;
			if(params[key] && params[key].offset)
				values[key]=values[key]-params[key].offset;
			if(params[key] && params[key].coef)
				values[key]=values[key]/params[key].coef;
		}
		if(testLng) values[idLNG]=testLng;
		if(init) return;
		activeAlarm=false;
		activeWarning=false;
		for(var i=0; i<alarmKeys.length; i++){
			if(values[alarmKeys[i]]==1){
				activeAlarm=true;
				break;
			}
		}
		if(!activeAlarm)
			for(var i=0; i<warnKeys.length; i++){
				if(values[warnKeys[i]]==1){
					activeWarning=true;
					break;
				}
			}
//		if(!activeAlarm && !activeWarning){
		if(!activeAlarm){
			var d=new Date(), utc=-(getTimezoneOffset(d)/60);
			if(values.H11400==0 || !(timeZones[values.H11400]) || timeZones[values.H11400].utc!==utc){
				activeAlarm=true;
			}else{
				var dUnit=new Date(values.I00004, values.I00005-1, values.I00006, values.I00007, values.I00008, values.I00009);
				if(Math.abs(dUnit.getTime()-d.getTime())>900000) activeAlarm=true;
			}
		}
		if(activeAlarm || activeWarning){
			var aEl=document.getElementById('alarmIco');
			if(activeAlarm) aEl.removeAttribute('warning');
			else aEl.setAttribute('warning', '1');
			document.getElementById('alarmIco').style.visibility="visible";
		}else{
			document.getElementById('alarmIco').style.visibility="hidden";
		}
		if(document.getElementById('leftMenuAL'))
			if(activeAlarm){
				document.getElementById('leftMenuAL').style.visibility="visible";
			}else{
				document.getElementById('leftMenuAL').style.visibility="hidden";
			}
		document.getElementsByTagName('h1')[0].style.backgroundImage="url('"+server+"images/logo_"+values['H10520']+".png')";

		if(!(pwrType)){
			if(typeof(paramKeys['power'])=='object'){
				for(var j=0; j<paramKeys['power'].length && !(pwrType); j++)
					if(typeof(values[paramKeys['power'][j]])!=='undefined') {
						paramKeys['power']=paramKeys['power'][j];
						pwrType=params[paramKeys['power']].options;
					}
			}else pwrType=params[paramKeys['power']].options;
		}
		setModeType();
		setVersions();
		setPowerType();
		setPowerRange();
		showStatus();
/*		if(values.C11100==0){

			var now=new Date();
			now=new Date(now.getFullYear(), now.getMonth(), now.getDate(), now.getHours()+1, now.getMinutes(),0);
			values.H11104=now.getFullYear();
			values.H11105=now.getMonth()+1;
			values.H11106=now.getDate();
			values.H11107=now.getHours();
			values.H11108=now.getMinutes();
		}
*/
		if(activePage=='AL'){
			showPage();
		}
//		if(activeMenu!=='' && menus[activeMenu].refresh) menus[activeMenu].refresh();
	}
}

function showStatus(){
	var vis=false, cnt=0;
	document.getElementById('heatIco').style.visibility=
		((values.C10202 ||
		  (values.C10215 && values.H10519==0) ||
      values.H10203>0 ||
		  (values.C10217 && values.H11801==0)) ?'visible':'hidden');
	document.getElementById('coolIco').style.visibility=
		(values.C10216?'visible':'hidden');
	document.getElementById('partyIco').style.visibility=
		(values.C10800>0?'visible':'hidden');
	if(values.I10005>3){
		activeUpdate=getFileContent('verpckg.txt');;
		wait(words.updateInProcess);
	}else{
		if(activeUpdate){
			location.reload(true);
//				wait();
		}
	}
	var vis=false;
	if((values.H10700+values.H10701+values.H10702+values.H10703>0)){
		var dt, getDM=function(val){
			var hex=val.toString(16);
			if (hex.length==3) hex='0'+hex;
			return {month:Number('0x'+hex.substr(0,2)), day:Number('0x'+hex.substr(2,2))};
		}
		for(i=18000; i<18016; i++){
			cnt+=values['C'+i];
			if ((values['H'+i]) && (values['H'+i])) {
				dt=getDM(values['H'+i]);
				if (values.I00005==dt.month && values.I00006==dt.day) {
					vis=true;
					break;
				}
			}
		}
		if (!vis) {
			var from, to;
			for(i=18100; i<18107; i=i+2){
				if((values['C'+i]) && (values['H'+i])){
					from=getDM(values['H'+i]);
					to=getDM(values['H'+(i+1)]);
					if (from.month<to.month || (from.month==to.month && from.day<=to.day)) {
						if (values.I00005>=from.month && values.I00005<=to.month && values.I00006>=from.day && values.I00006<=to.day) {
							vis=true;
							break;
						}
					}else{
						if ((values.I00005<to.month || (values.I00005==to.month && values.I00006<=to.day)) ||
							 (values.I00005>from.month || (values.I00005==from.month && values.I00006>=from.day))){
							vis=true;
							break;
						}
					}
				}
			}
		}
	}
	document.getElementById('holidayIco').style.visibility=
		(vis?'visible':'hidden');

	document.getElementById('heatIco').setAttribute('title',words.heatIconTip);
	document.getElementById('coolIco').setAttribute('title',words.coolIconTip);
	document.getElementById('partyIco').setAttribute('title',words.partyIconTip);
	document.getElementById('alarmIco').setAttribute('title',words.alarmIconTip);


	document.getElementById('holidayIco').setAttribute('title',words.holidayTip);
}

function setModeType(){
	var mask=values.I12004.toString(2);
	mask='00000000'.substr(0,8-mask.length)+mask;
	for(var i=0; i<8;i++){
		if((i==3 || i==4) && values.H11700==0)
			options['Mode'].values[i].rw="0";
		else
			options['Mode'].values[i].rw=mask[7-i];
	}
	modeType='Mode';
}
function setPowerType(){
	if(options['Power']){
		var realPwrKey=(values.C10509==1?'2Z':values.H10510);
		var oProps=['caption','type','minVal','maxVal','step','count','dec','unit','initial','graph'];
		for(var i=0; i<oProps.length; i++)
			options['Power'][oProps[i]]=options['Power_'+realPwrKey][oProps[i]];
		if(values.C10509==1){ // 2Zone
			options.Power.values=options['Power_'+realPwrKey].values.slice();
			options.Power.onshow=options['Power_'+realPwrKey].onshow;
			options.Power.onshow();
			return;
		}else{
			options.Power.onshow=null;
		}
		if(values.H10510==1){
			if(values.I12003>0)
				options.Power.minVal=values.I12003;
			if(values.I12002>0)
				options.Power.maxVal=values.I12002;
			options.Power.from=1;
			options.Power.to=100;
			options.Power.recalc(true);
			options.Power.values[0]=options['Power_'+realPwrKey].values[0];
		}else if(values.H10510==0){
			options.Power.values=options['Power_'+realPwrKey].values.slice();
		}
		if(values.H10510<2){
			if(values.H11616>0){
				for(i=1; i<values.H11616; i++){
					if(options.Power.values[i]){
						options.Power.values[i].rw=0;
					}
				}
			}

			if(values.H11617>0){
				for(i in options.Power.values)
					if(i>values.H11617){
						options.Power.values[i].rw=0;
					}
			}
		}else{
			/* options.Power.values=options['Power_'+realPwrKey].values.slice();			 tento Ã¸Ã¡dek je originÃ¡lnÃ­ , pÃ¸ed Ãºpravou 26.11.2015*/

      if(values.H10510==4){
        if((values.H10705==1)||(values.H10705==1)){
          options.Power.values=options['Power_4'].values.slice();
          }else{
          options.Power.values=options['Power_5'].values.slice();
          }
        }else{
          options.Power.values=options['Power_'+realPwrKey].values.slice();
          }
		}
	}
}

function setPowerRange(){
/*	if(typeof(values['H10516'])=='number' && (values[idLINE]==1)){
		for(var i in options.Power.values){
			if(i>1)
				options['Power'].values[i].rw=(i<=values['H10516']?1:0);
		}
	}
*/
}
function setTempOption(){
	options[tempType].to=values.H11316;
	options[tempType].recalc();
}

function loadLayout(node) {
	for(var i=0; i<node.childNodes.length; i++) {
		if(node.childNodes[i].nodeType==1) {
			var n=node.childNodes[i];
			switch(n.nodeName){
				case 'body':
					body=loadPage(body, n);
					break;
				case 'options':
					loadOptions(n);
					break;
				case 'messages':
					messages=nodes2Array(messages, n.getElementsByTagName('i'), new Object());
					break;
				case 'rules':
					rules=nodes2Array(rules, n.getElementsByTagName('i'), new Object());
					break;
				case 'languages':
					loadLangs(n);
					break;
				default:
					alert('Unknown section '+n.nodeName+' in the content.xml !');
					break;
			}
		}
	}
}

function loadPage(page, node) {
	var attrName
	for(var i=0; i<node.attributes.length; i++){
		attrName=node.attributes[i].name;
		page[attrName]=node.attributes[i].value;
		if((page[attrName].substr) && page[attrName].substr(0,1)=='$'){
			page[attrName]=words[page[attrName].substr(1)];
		}
	}
	for(var i=0; i<node.childNodes.length; i++) {
		var n=node.childNodes[i];
		if(n.nodeType==1) {
			switch(n.nodeName) {
				case 'menu':
					var key=n.getAttribute('id');
					if(!(page.menus[key])) {
						page.menus[key]={content:'',initial:false,source:''};
						if(n.getElementsByTagName('menu').length>0) page.menus[key].menus=new Array();
					}
					page.menus[key]=loadPage(page.menus[key], n)
					break;
				case 'content':
					if(!(page.content.items)) page.content={type:'', items:new Array()};
					page.content=loadContent(page.content, n);
					break;
			}
		}
	}
	return page;
}

function loadContent(content, node) {
	var attrName, i;
	for(i=0; i<node.attributes.length; i++){
		attrName=node.attributes[i].name;
		content[attrName]=node.attributes[i].value;
		if(attrName=='source')
			content.source+=(webMode?'.php':'.xml');
		else{
			if((content[attrName].substr) && content[attrName].substr(0,1)=='$'){
				content[attrName]=words[content[attrName].substr(1)];
			}
		}
	}
	if(!(content.type)) content.type='';
	if(content.type=='html'){
		content.code=node.childNodes[0].nodeValue
	}else{
		var pgId='', pages=node.getElementsByTagName('page');
		if (pages.length>0) {
			content.pages=[];
			var pgId;
			for(i=0; i<pages.length; i++){
				pgId=pages[i].getAttribute('id');
				content.pages[pgId]={id:pages[i].getAttribute('id'), title:pages[i].getAttribute('title'), items:[]};
				if((content.pages[pgId].title.substr) && content.pages[pgId].title.substr(0,1)=='$')
					content.pages[pgId].title=words[content.pages[pgId].title.substr(1)];
				if (pages[i].hasAttribute('when')) content.pages[pgId].when=pages[i].getAttribute('when');
				loadContentItems(content.pages[pgId].items, pages[i].getElementsByTagName('i'));
			}
		}else{
			loadContentItems(content.items, node.getElementsByTagName('i'));
		}
	}
	return content;
}
function loadContentItems(items, nodes) {
	var key='', keyVal, value, attrName, i;
	for(var i=0; i<nodes.length; i++) {
		key=nodes[i].getAttribute('id');
		keyVal=(nodes[i].getAttribute('key') || key)
		keyW=nodes[i].getAttribute('idw');
		if(typeof(values[keyVal])!=='undefined' || nodes[i].getAttribute('always')=='1') {
			if(!(items[key])) items[key]=new Object();
//				for(var j=1; j<nodes[i].attributes.length; j++){
			for(var j=0; j<nodes[i].attributes.length; j++){
				attrName=nodes[i].attributes[j].name;
				items[key][attrName]=nodes[i].attributes[j].value;
				if((items[key][attrName].substr) && items[key][attrName].substr(0,1)=='$')
					items[key][attrName]=words[items[key][attrName].substr(1)];
			}
			items[key].id=keyVal;
			var tmp=nodes[i].getElementsByTagName('onchange');
			if(tmp && tmp.length==1){
				eval("items['"+key+"'].onChange="+tmp[0].childNodes[0].nodeValue);
			}
			var tmp=nodes[i].getElementsByTagName('displayval');
			if(tmp && tmp.length==1){
				eval("items['"+key+"'].displayVal="+tmp[0].childNodes[0].nodeValue);
			}
			var tmp=nodes[i].getElementsByTagName('setupval');
			if(tmp && tmp.length==1)
				eval("items['"+key+"'].setupVal="+tmp[0].childNodes[0].nodeValue);
			var tmp=nodes[i].getElementsByTagName('saveval');
			if(tmp && tmp.length==1)
				eval("items['"+key+"'].saveVal="+tmp[0].childNodes[0].nodeValue);
		}else if(keyVal.substring(0,1)=='['){
			// more keys
			eval('keys='+keyVal+';');
			whenOK=keys.length>0;
			for(var iKey=0; iKey<keys.length;iKey++)
				if(typeof(values[keys[iKey]])=='undefined'){
					whenOK=false;
					break;
				}
			if(whenOK){
				keyVal=keyVal.replace(/[\[\]\']/g,"");
				if(!(items[keyVal])) items[keyVal]=new Object();
				for(var j=0; j<nodes[i].attributes.length; j++){
					attrName=nodes[i].attributes[j].name;
					items[keyVal][attrName]=nodes[i].attributes[j].value;
					if((items[keyVal][attrName].substr) && items[keyVal][attrName].substr(0,1)=='$')
						items[keyVal][attrName]=words[items[keyVal][attrName].substr(1)];
				}
				items[keyVal].id=keyVal;
				items[keyVal].ids=keys;
			}
		}
	}
}

function node2Object(n){
	var o=new Object(), attrName;
	for(var i=0; i<n.attributes.length; i++){
		attrName=n.attributes[i].name;
		o[attrName]=n.attributes[i].value;
		if((o[attrName].substr) && o[attrName].substr(0,1)=='$'){
			o[attrName]=words[o[attrName].substr(1)];
		}
	}
	for(var i=0; i<n.childNodes.length; i++){
		if(n.childNodes[i].nodeType==1){
			aN=n.childNodes[i];
			if(aN.getAttribute('id') && aN.getAttribute('id')!=='') {   // array
				eval("if(!(o."+aN.nodeName+")) o."+aN.nodeName+"=new Array();");
				eval("o."+aN.nodeName+"s['"+aN.getAttribute('id')+"']=node2Object(aN);");
			} else {
				eval("o."+aN.nodeName+"=node2Object(aN);");
			}
		}
	}
	return o;
}

function nodes2Array(arr, nodes, newObject) {
	var key='', attrName;
	for(var i=0; i<nodes.length; i++) {
		key=nodes[i].getAttribute('id');
		if(!(arr[key])) arr[key]=newObject.constructor();
//		for(var j=1; j<nodes[i].attributes.length; j++){
		for(var j=0; j<nodes[i].attributes.length; j++){
			attrName=nodes[i].attributes[j].name;
			arr[key][attrName]=nodes[i].attributes[j].value;
			if((arr[key][attrName].substr) && arr[key][attrName].substr(0,1)=='$')
				arr[key][attrName]=words[arr[key][attrName].substr(1)];

		}
	}
	return arr;
}

function getUrlPar(par, val){
	val=parseFloat(val);
	if(params[par]){
		var opt=options[params[par].options];
		if(opt.type=="rangeEnum"){
//			if(opt.values[val])
		}else{
			if((opt.minVal!=='' && val<opt.minVal) || (opt.maxVal>0 && val>opt.maxVal)){
				alert(words['badInput']+','+words['allowedRange']+': '+opt.minVal+' .. '+(opt.maxVal>0?opt.maxVal: ''));
				return false;
			}
		}
		if(params[par].coef)	val=val*params[par].coef;
		if(params[par].offset)	val=val+params[par].offset;
	}
	if(val<0) val=val+65536;
	val=val.toString();
//	alert(par+'0000'.substr(0,5-val.length)+val)
	return par+'0000'.substr(0,5-val.length)+val;
//	return par+val.toString();
}

function loadTZ(node){
	options['TimeZone'].values=[];
	var childs=node.getElementsByTagName('i'), i, id, hours, minutes, cTime;
	for(i=0; i<childs.length; i++){
		id=Number(childs[i].getAttribute('id'));
		timeZones[id]={utc:Number(childs[i].getAttribute('utc')),
			dst:Number(childs[i].getAttribute('dst')),
			title:childs[i].getAttribute('tz')};
		hours=parseInt(Math.abs(timeZones[id].utc));
		minutes=(Math.abs(timeZones[id].utc)-hours)*60;
		cTime=(timeZones[id].utc>0?'+':(timeZones[id].utc<0?'-':' '))+(hours<10?'0':'')+hours+':'+(minutes<10?'0':'')+minutes;
		options['TimeZone'].values[id]={value:id, title:cTime+' '+timeZones[id].title};
	}
}
function loadOptions(node) {
	var childs=node.getElementsByTagName('op');
	for(var i=0; i<childs.length; i++) {
		key=childs[i].getAttribute('id');
		if(!(options[key])) options[key]=new option();
		options[key].load(childs[i]);
	}
	setPowerType();
	setPowerRange();
	setTempOption();
}
function loadParams(node) {
	var childs=node.getElementsByTagName('i');
	alarmKeys=new Array();
	warnKeys=new Array();
	for(var i=0; i<childs.length; i++) {
		key=childs[i].getAttribute('id');
		params[key]=node2Object(childs[i]);
		if(params[key].flag=='A') alarmKeys.push(key);
		else if(params[key].flag=='W') warnKeys.push(key);
		params[key].type=parseInt(params[key].type);
		if(params[key].coef){
			params[key].coef=eval(params[key].coef);
		}else params[key].coef=1;
		if(params[key].offset)
			params[key].offset=parseFloat(params[key].offset);
	}
}
function option() {
	this.caption='';
	this.type='enum';
	this.minVal=0;
	this.maxVal=0;
	this.step=0;
	this.count=0;
	this.dec=0;
	this.unit='';
	this.initial=0;
	this.values=new Array();
	this.graph='';
	this.display=function(value, index) {
		if(this.type=='range') {
			if(isNaN(Number(value))) return value;
			if(this.dec)
				value=Number(value);
			for(var i=0; i<this.values.length; i++)
				if(this.values[i].value==value)
					return this.values[i].title;
			if(this.dec)
				value=value.toFixed(this.dec);
			return value+this.unit;
		} else {
			try{
				this.values[value].ondisplay();
			}catch(e){};
			try{
				return this.values[value].title+((/\D/.test(this.values[value].title))?'':this.unit);
			} catch(e) {
				if(typeof(value)=='object'){
					if(!(index)) index=0;
					return this.values[value[index]].title+this.unit;
				} else if(this.type=='input') {
					return value;
				} else if(webMode)
					console.warn('Error in '+this.caption+' value='+value+' type='+this.type+' index='+index);
			}

		}
	}

	this.recalc=function(debug){
		var val, i, d;
		if(this._values && this._values.length>0){
			this.values=this._values.slice(0);
		}else{
			this.values=[];
		}

		if(this.step){
			this.values[this.from]={value:this.minVal, title:this.minVal.toFixed(this.dec)+this.unit};
			for(i=this.from+1; i<=this.to; i++){
				val=this.values[i-1].value+this.step;
				this.values[i]={value:val, title:val.toFixed(this.dec)+this.unit};
				if(this.stepset){
					d=(i-this.from)/this.stepset;
					if(d!==parseInt(d))
						this.values[i].rw=0;
				}
			}
		}else{
			for(i=this.from; i<=this.to; i++){
				val=Math.round((this.maxVal-this.minVal)*((i-this.from)/(this.to-this.from))+this.minVal);
				if(val>999) val=Math.round(val/10)*10;
				this.values[i]={value:val,
						title:val.toFixed(this.dec)+this.unit};
			this.type='rangeEnum';
			}}
	}

	this.load=function(node) {
		var valI, attrName, title, val;
		this.caption=node.getAttribute('title');
		if((this.caption) && this.caption.substr(0,1)=='$') this.caption=words[this.caption.substr(1)];
		if(node.getAttribute('unit')) this.unit=node.getAttribute('unit');
		if(node.getAttribute('graph')) this.graph=node.getAttribute('graph');
		if(node.getElementsByTagName('unit').length==1)
			this.unit=nodeContent(node.getElementsByTagName('unit')[0]);
		if(node.getAttribute('type')) this.type=node.getAttribute('type');
		else if(this.type=='') this.type='enum';
		if(node.getAttribute('initial')) this.initial=node.getAttribute('initial');
		if(node.getElementsByTagName('onshow').length==1){
//			this.onshow=nodeContent(node.getElementsByTagName('unit')[0]);
			eval("this.onshow="+ nodeContent(node.getElementsByTagName('onshow')[0]));
		}

		if(this.type=='range' && node.getAttribute('minval') && node.getAttribute('maxval') && node.getAttribute('step')){
			this.minVal=parseFloat(node.getAttribute('minval'));
			this.maxVal=Number(node.getAttribute('maxval'));
			this.step=parseFloat(node.getAttribute('step'));
			if((this.step-parseInt(this.step))){
				this.dec=(this.step-parseInt(this.step)).toString().length-2;
			}
			if(node.getAttribute('stepset'))
				this.stepset=parseInt(node.getAttribute('stepset'));
			if(this.initial=='') this.initial=this.minVal;
			else this.initial=parseFloat(this.initial);

			var valNodes=node.getElementsByTagName('i');
			this.values=[];
			this._values=[];
			for(var i=0; i<valNodes.length; i++) {
				title=valNodes[i].getAttribute('title');
				if((title.substr) && title.substr(0,1)=='$') title=words[title.substr(1)];
				this._values.push({value:Number(valNodes[i].getAttribute('val')), title:title});
				this.values.push({value:Number(valNodes[i].getAttribute('val')), title:title});
			}
			if(node.getAttribute('from') && node.getAttribute('to')){
				this.from=parseInt(node.getAttribute('from'));
				this.to=parseInt(node.getAttribute('to'));
				this.recalc();
//				this.minVal=null;
//				this.maxVal=null;
				this.type='rangeEnum';
			}
		} else {
			var cnt=0;
			if(node.getElementsByTagName('i').length>0) {
				var valNodes=node.getElementsByTagName('i');
				for(var i=0; i<valNodes.length; i++) {
					valI=valNodes[i].getAttribute('id');
					if(this.initial=='') this.initial=valI;
					this.values[valI]=new Object();
//					this._values[valI]=new Object();
					for(var j=0; j<valNodes[i].attributes.length; j++){
						attrName=valNodes[i].attributes[j].name;
						if(attrName=='val')
							this.values[valI].val=Number(valNodes[i].attributes[j].value);
						else
							this.values[valI][attrName]=valNodes[i].attributes[j].value;
						if((this.values[valI][attrName].substr) && this.values[valI][attrName].substr(0,1)=='$')
							this.values[valI][attrName]=words[this.values[valI][attrName].substr(1)];
					}
					for(var j=0; j<valNodes[i].childNodes.length; j++){
						if(valNodes[i].childNodes[j].nodeType==1){
							var attrName=valNodes[i].childNodes[j].nodeName;
							eval("this.values[valI]."+attrName+"="+ nodeContent(valNodes[i].childNodes[j]));
							for(var k in this.values[valI][attrName])
								if(typeof(this.values[valI][attrName][k])=='string' && this.values[valI][attrName][k].substr(0,1)=='$')
									this.values[valI][attrName][k]=words[this.values[valI][attrName].substr(1)];
//							if((this.values[key].substr) && this.values[key].substr(0,1)=='$')
						}
					}
					cnt++;
//					if(this.values[valI].rw!=='0') this.lastKey=valI;
				}
				this.firstKey=valNodes[0].getAttribute('id');
				this.lastKey=valNodes[valNodes.length-1].getAttribute('id');
			} else if(node.getElementsByTagName('values').length==1) {
				eval('var vals='+nodeContent(node.getElementsByTagName('values')[0]));
				this.firstKey=false;
				for(var key in vals) {
					this.values[key]=new Object();
					if((vals[key].substr) && vals[key].substr(0,1)=='$')
						this.values[key].title=words[vals[key].substr(1)];
					else
						this.values[key].title=vals[key];
					cnt++;
					if(!this.firstKey) {this.firstKey=key};
					this.lastKey=key;
				}
				if(this.initial=='') this.initial=this.firstKey;
			}
			this.count=cnt;
			if(this.type=='range') {
				this.type='rangeEnum';
			}
		}
	}

	this.getValueIndex=function(value, index) {
		if(typeof(value)=='object'){
			if(!(index)) index=0;
			value=value[index];
		}
		var result=0;
		if(this.type=='enum' || this.type=='boxes' || this.type=='rangeEnum') {
			this.testRW();
			for(var i=0; i<this.values.length; i++)
				if(this.values[i]==value) return i;
		}else if(this.type=='range') {
			result=(value-this.minVal)/(this.maxVal-this.minVal);
		}
		return result;
	}
	this.testRW=function(){
		if(!(this.valuesRW)){
			this.valuesRW=[];
			for(var key in this.values)
				if(typeof(this.values[key].rw)=='undefined' ||
						(this.values[key].rw==1) ||
						this.values[key].rw=='1'){
					this.valuesRW.push(key);
				}
		}
	}
	this.getValueRatio=function(value, index) {
		if(typeof(value)=='object'){
			if(!(index)) index=0;
			value=value[index];
		}
		var result=0;
		if(this.type=='enum' || this.type=='boxes' || this.type=='rangeEnum') {
			this.testRW();
			for(var i=0; i<this.valuesRW.length; i++) {
				if(this.valuesRW[i]==value){
					return i/(this.valuesRW.length-1);
				}
			}
		}else if(this.type=='range') {
			result=(value-this.minVal)/(this.maxVal-this.minVal);
		}
		return result;
	}

	this.getPrevNextVal=function(value, direction, index) {
		if(typeof(value)=='object'){
			if(!(index)) index=0;
			value=value[index];
		}
		var result='';
		if(this.type=='enum' || this.type=='boxes' || this.type=='rangeEnum') {
			this.testRW();
			if(direction==-1){
				var prevKey=this.valuesRW[this.valuesRW.length-1];
				for(var i=0; i<this.valuesRW.length; i++){
					if(this.valuesRW[i]==value){
						return prevKey;
					}
					prevKey=this.valuesRW[i];
				}
			}else if(direction==1) {
				for(var i=0; i<(this.valuesRW.length-1); i++){
					if(this.valuesRW[i]==value)
						return this.valuesRW[i+1];
				}
				return this.valuesRW[0];
			} else result=value;

		}else	if(this.type=='range') {
			result=Math.round((value+direction*this.step)*100)/100;
			if(result<this.minVal) result=this.maxVal;
			if(result>this.maxVal) result=this.minVal;
		}
		return result;
	}
	this.getValueFromRatio=function(ratio) {
		if(this.type=='range') {
			return Math.round((Math.round((Math.round((this.maxVal-this.minVal)/this.step))*ratio)*this.step+this.minVal)*100)/100;
		} else if(this.type=='rangeEnum') {
			this.testRW();
			pos=Math.round((this.valuesRW.length-1)*Math.min(ratio,1));
			return(this.valuesRW[pos]);
		}
	}
}
// x************ VISUALISATION ********
function showPage() {

	document.getElementById('mainBlock').innerHTML='';
	if(activePage=='') {
		document.getElementById('content').style.backgroundImage="url('"+server+"style/images/backBlueMain.png')";
		showMenu(body.menus);
		showContent(body.content);
		document.getElementById('pageTitle').getElementsByTagName('h2')[1].innerHTML='';
		document.getElementById('pageTitle').getElementsByTagName('h2')[1].appendChild(document.createTextNode(words['mainPage']));
	} else {
		document.getElementById('content').style.backgroundImage="url('"+server+"style/images/backBlue.png')";
		showMenu(body.menus[activePage].menus);
		showContent(body.menus[activePage].menus[activeContent].content);
		document.getElementById('pageTitle').getElementsByTagName('a')[0].innerHTML=words['backToHome'];
		document.getElementById('pageTitle').getElementsByTagName('h2')[1].innerHTML='';
		document.getElementById('pageTitle').getElementsByTagName('h2')[1].appendChild(document.createTextNode(body.menus[activePage].title));
	}
//	document.getElementById('pageTitle').setAttribute('class',(activePage==''?'hidden':''));
	document.getElementById('pageTitle').childNodes[0].setAttribute('class',(activePage==''?'hidden':'back'));
	showValues();
//	fill Values;
}
function showMenu(menus) {
	var showIt, aEls=[];
	for(var key in menus) {

		showIt=menus[key].hidden!=="1";
		if(key=='passwd' || (showIt && (menus[key].when))){
			showIt=testWhen(menus[key].when);
		}
		if(showIt) {
			var id='leftMenu'+key;
			if(document.getElementById(id)) {
				o=document.getElementById(id);
			} else {
				var o=document.createElement('div');
				o.setAttribute('id',id);
				o.setAttribute('menuId',key);
				if(activePage=='') {
					if(menus[key].type=="warning"){
						o.setAttribute('class','menuItemWarn');
						if(key=="AL"){
							if(!activeAlarm) o.style.visibility="hidden";
						}
					}
					else o.setAttribute('class','menuItem');
					o.onmousedown=function() {
						activeContent='';
						activePage=this.getAttribute('menuId');
						showPage();
					};
				}else{
					o.setAttribute('class','subMenuItem');
					o.setAttribute('active', '');
					o.active=false;
					if(menus[key].initial=='1'){
						activeContent=key;
						o.active=true;
					}
					o.onmousedown=function() {
						if(activeContent!=='') document.getElementById('leftMenu'+activeContent).setAttribute('class','subMenuItem');
						document.getElementById('leftMenu'+activeContent).setAttribute('class', '');
						document.getElementById('leftMenu'+activeContent).setAttribute('class', 'subMenuItem');
						activeContent=this.getAttribute('menuId')
						this.active=true;
						document.getElementById('content').innerHTML='';
						showContent(body.menus[activePage].menus[activeContent].content);
						showValues();
					};
				}
				var a=document.createElement('a');

				if(menus[key].image) {
					var el=document.createElement('img');
					el.src=server+'images/'+menus[key].image;
					a.appendChild(el);
				}
				a.appendChild(document.createElement('span'));
				o.appendChild(a);
				document.getElementById('mainBlock').appendChild(o);
			}
			o.getElementsByTagName('span')[0].innerHTML=menus[key].title;
			aEls.push(o);
		}
	}
	if(aEls.length>6){
		var height=((665/(3*aEls.length-1))), MBott=Math.round((height-5)/2),
				MTop=height-MBott;
		height=height*2;
		var mTop=Math.floor(height/6-4.8);

		height=Math.floor(height.toString())+'px';
		mTop=mTop.toString()+'px';
		MTop=MTop.toString()+'px';
		MBott=MBott.toString()+'px';
		for(var i=0; i<aEls.length; i++){
			aEls[i].childNodes[0].childNodes[0].style.marginTop=mTop;
			if(i>0){
				aEls[i].style.marginTop=MTop;
			}
			aEls[i].style.marginBottom=MBott;
			aEls[i].style.height=height;
		}
	}
}
function showLogin(){
	document.getElementById('smog').style.bottom="25px";
	document.getElementById('smog').style.visibility='visible';
	var wnd=document.createElement('div');
	wnd.setAttribute('class', 'boxBigBig');
	wnd.style.zIndex="5000";
	wnd.appendChild(document.createElement('h3'));
	wnd.lastChild.appendChild(document.createTextNode(words.userLogin));
	wnd.appendChild(document.createElement('div'));
	wnd.lastChild.setAttribute('class', 'fullArea');
	wnd.lastChild.appendChild(document.createTextNode(words.passwordInput));
	wnd.lastChild.appendChild(document.createElement('input'));
	wnd.lastChild.lastChild.setAttribute('type', 'password');
	wnd.lastChild.lastChild.onchange=function(){this.parentNode.parentNode.login();}
	wnd.oPwd=wnd.lastChild.lastChild;
	wnd.login=function(){
		if(!(this.oPwd.value)) return;
		if(demoMode){
			window.location='index.htm?sid=12345';
			this.oPwd.value='';
		}else{
			var doc=sendSync(urlLogin,'magic='+md5("\r\n"+this.oPwd.value)+'&'+randStr(2), null);
			this.oPwd.value='';
			if(doc && doc.documentElement){
				var nPass=Number(doc.documentElement.textContent);
				if(nPass>0){
					window.location='index.htm?sid='+doc.documentElement.textContent;
				}else{
					alert(words.accessDenied);
				}
			}
		}
	};


	wnd.appendChild(document.createElement('div'));
	wnd.lastChild.setAttribute('class','button');
	wnd.lastChild.style.marginBottom='-20px';
	wnd.lastChild.appendChild(document.createTextNode(words.loginCmd));
	wnd.lastChild.onmouseup=function(){};
	document.getElementById('mainBlock').appendChild(wnd);
	wnd.oPwd.focus();
	return;
}

function showContent(content) {
	var key,o ;
	if(location.hash!=='#'+activePage+'.'+activeContent)
		location.hash = '#'+activePage+'.'+activeContent;

	document.getElementById('content').innerHTML='';
	document.getElementById('content').setAttribute('autoRefresh', '1');
	document.getElementById('content').setAttribute('dataLoaded', '0');
	document.getElementById('content').dateChanged=false;
	if(activeContent!=='') {
//		document.getElementById('leftMenu'+activeContent).class= 'subMenuItemA';
		document.getElementById('leftMenu'+activeContent).setAttribute('class', '');
		document.getElementById('leftMenu'+activeContent).setAttribute('class', 'subMenuItemA');
	}
	var nCnt=0, multiPage=0, cntPages=1, onPage;
	if(content.type=='') {
		var keys=[], isInput=false;
		if (content.pages) {
			multiPage=2;
		}else{
			for(key in content.items){
				if(!(testWhen(content.items[key].when))) continue;
				if(content.items[key].type=='endPage'){
					multiPage=1;
					cntPages++;
					continue;
				}
				if(content.items[key].options=='DateTime'){
					isInput=true;
				}
				keys[content.items[key].id]=true;
			}
			for(key in keys){
				if(typeof(keys[key])=='boolean' && content.items[key].type!='spacer' && content.items[key].type!='endPage');
				nCnt++;
			}
		}
		var boxClass='boxItem'+(nCnt>8?'Min':''), contentBox=document.getElementById('content');

		if(multiPage==1){
			o=document.createElement('div');
			o.setAttribute('style','position:absolute;top:0; right:0; height:630px; left:0; overflow:hidden');
			contentBox.appendChild(o);
			o=document.createElement('div');
			o.setAttribute('style','position:absolute;  top:0; left:0; right:0; overflow:visible');

			contentBox.childNodes[0].appendChild(o);
			contentBox.childNodes[0].moveContTo=function(step){
				if (!step) {
					step=(this.toTop>this.childNodes[0].offsetTop?2:-2);
				}else{
					if(Math.abs(this.toTop-this.childNodes[0].offsetTop)>=400) {
						step=step*1.5;
					}else if(Math.abs(this.toTop-this.childNodes[0].offsetTop)<=168) {
						if (step>0) {
							step=Math.max(step/1.5,1);
						}else{
							step=Math.min(step/1.5,-1);
						}
					}
				}
				var nPos=this.childNodes[0].offsetTop+step;
				if(step<0){
					if(nPos<this.toTop) nPos=this.toTop;
				}else{
					if(nPos>this.toTop) nPos=this.toTop;
				}
				this.childNodes[0].style.top=nPos.toString()+'px';
				if (nPos!=this.toTop) {
					setTimeout("document.getElementById('content').childNodes[0].moveContTo("+step+")",30);
				}
			}

			o=createElement('div', false, false,
					{style:'position:absolute;  right:5px; bottom:0;left:0px; height:48px;\
						background-color:rgba(255,255,255,.5); padding-top:7px'});
			o.page=1;
			o.appendChild(createElement('img',false,false,{style:'position:absolute; left:30px; cursor:pointer',
												 src:server+'style/images/downBig.png'}));
			o.appendChild(createElement('span'),false, false,
					{style:'display:block;position:absolute; left:100px; right:100px; text-align:center; font-size:32px'});
			o.lastChild.innerHTML="1/"+cntPages;
			o.appendChild(createElement('img',false,false,{style:'position:absolute; right:30px; cursor:pointer',
												 src:server+'style/images/upBig.png'}));
			o.cntPages=cntPages;
			o.goPage=function(direction){
				this.page=Math.max(this.page+direction,1);
				if (this.page>this.cntPages) {this.page=this.cntPages;return;				}
				this.childNodes[1].innerHTML=this.page+'/'+this.cntPages;
				document.getElementById('content').childNodes[0].toTop=-620*(this.page-1);
				document.getElementById('content').childNodes[0].moveContTo(0);
			}
			o.childNodes[0].onmouseup=function(e){this.parentNode.goPage(1);}
			o.childNodes[2].onmouseup=function(e){this.parentNode.goPage(-1);}
			contentBox.appendChild(o);
			contentBox=contentBox.childNodes[0].childNodes[0];
		}

		if (multiPage==2) {
			var bmWidth=30, boxWidth=754, boxes, pgKey, rMargin;
/*			contentBox.appendChild(createElement('div', false, false, {style:'height:100%;width:300%'}));
			contentBox=contentBox.lastChild;*/
			for(pgKey in content.pages)
				if((testWhen(content.pages[pgKey].when))) boxWidth-=bmWidth;
			rMargin=(boxWidth-652)/3;
			cntPages=0;
			for(var pgKey in content.pages){
				if(!(testWhen(content.pages[pgKey].when))) continue;
				cntPages++;
				contentBox.appendChild(createElement('div', 'multiPage'));
/*				contentBox.lastChild.key=pgKey;
				contentBox.lastChild.style.width=(boxWidth+bmWidth)+'px';
				contentBox.lastChild.style.marginLeft=pgKey=='vzt'?'-9px':'-2px';
*/
				contentBox.lastChild.style.width=(boxWidth+bmWidth)+'px';
				contentBox.lastChild.style.marginLeft=pgKey=='vzt'?'-7px':'0px';
				contentBox.lastChild.setAttribute('active',(cntPages==1?'1':'0'))
				contentBox.lastChild.appendChild(createElement('div', false,
												document.createTextNode(content.pages[pgKey].title)));
				contentBox.lastChild.lastChild.onclick=function(){
					var pages=this.parentNode.parentNode.childNodes;
					for(var i=0; i<pages.length; i++) pages[i].setAttribute('active','0');
					this.parentNode.setAttribute('active', '1');
				}
				contentBox.lastChild.appendChild(createElement('div', false, false,
						{style:"float:left; display: grid; grid-template-columns: auto auto; max-width:"+boxWidth+'px'}));
				addBoxes(contentBox.lastChild.lastChild, true, content.pages[pgKey].items, 8, 'boxItem', false);
				boxes=contentBox.lastChild.lastChild.childNodes;

				for(i=0; i<boxes.length; i++){
					boxes[i].style.margin="18px 0 0 "+rMargin+"px";
					boxes[i].style.width="320px";
				}
			}

		}else{
			addBoxes(contentBox, multiPage==1, content.items, nCnt, boxClass, isInput);
		}

		if(nCnt>0 && (nCnt<5 || (nCnt==5 && isInput)) && !(document.getElementById('cmdSave'))) {
			var o=document.createElement('div');
			o.setAttribute('type', 'button');
			o.setAttribute('id', 'cmdSave');
			o.setAttribute('class', 'button');
			if(content.confirm){
//				o.confirmid=content.confirm;
				document.getElementById('content').confirmId=content.confirm;
			}

			if(content.idactive){
				o.setAttribute("sendid",content.idactive);
				o.onmouseup=function() {
					saveValues(this.getAttribute('sendid'),1,true);
					document.getElementById('content').setAttribute('dataLoaded', '0');
				};
				o.appendChild(document.createTextNode(words['activate']));
				document.getElementById('content').appendChild(o);
				document.getElementById('content').setAttribute('autoRefresh', '0');
				var o=document.createElement('div');
				o.setAttribute("sendid",content.idactive);
				o.setAttribute('type', 'button');
				o.setAttribute('id', 'cmdDeact');
				o.setAttribute('class', 'button');
				o.style.marginRight="20px";
				o.style.marginTop="-100px";
				o.style.float="right";
				o.appendChild(document.createTextNode(words['deactivate']));
				o.onmousedown=function() {
					saveValues();
					saveValues(this.getAttribute('sendid'),0);document.getElementById('content').setAttribute('dataLoaded', '0');
				};
				document.getElementById('content').appendChild(o);
				document.getElementById('content').setAttribute('autoRefresh', '0');
				o.setAttribute('idVal', content.idactive);
				o.setAttribute('setValue','');
				o.setValue=function(value, refresh){
					if(value) this.style.visibility='visible';
					else  this.style.visibility='hidden';
				};
			}else{
				o.onmousedown=function() {saveValues();document.getElementById('content').setAttribute('dataLoaded', '0')};
				o.appendChild(document.createTextNode(words['save']));
				o.onmouseup=function() {saveValues();document.getElementById('content').setAttribute('dataLoaded', '0')};
				document.getElementById('content').appendChild(o);
				document.getElementById('content').setAttribute('autoRefresh', '0');
			}
		}else{
			if(content.idactive){
				var o=document.createElement('div');
				o.setAttribute('type', 'button');
				o.setAttribute('id', 'cmdSave');
				o.setAttribute('class', 'button');
				o.setAttribute("sendid",content.idactive);
				o.onmouseup=function() {
					var parms=getUrlPar(this.getAttribute('sendid'),(this.value==1?0:1)),
						el=(this.previousSibling.previousSibling);
					if(this.value==0){
						for(var i=0; i<el.ids.length; i++)
							parms+='&'+getUrlPar(el.ids[i], el.values[el.ids[i]]);
						el=(this.previousSibling);
						for(var i=0; i<el.ids.length; i++)
							parms+='&'+getUrlPar(el.ids[i], el.values[el.ids[i]]);
					}
					send2Unit(parms);
//					saveValues(this.getAttribute('sendid'),);
//					document.getElementById('content').setAttribute('autoRefresh', '0');
					document.getElementById('content').setAttribute('dataLoaded', '0');
				};
				document.getElementById('content').appendChild(o);
//
				o.setAttribute('idVal', content.idactive);
				o.setAttribute('setValue','');
				o.setValue=function(value, refresh){
					this.value=value;
					this.innerHTML='';
					if(value) this.appendChild(document.createTextNode(words.deactivate));
					else this.appendChild(document.createTextNode(words.saveActive));
//					document.getElementById('content').setAttribute('autoRefresh', '0');
				};
				document.getElementById('content').setAttribute('autoRefresh', '0');		}
				document.getElementById('content').setAttribute('dataLoaded', '0');
		}
	} else { // other content type
		var oContent=createContent(content);
		if ((oContent)) document.getElementById('content').appendChild(oContent);
		if(content.source) rq('getSetting');
	}
}
function addBoxes(contentBox, multiPage, items, nCnt, boxClass, isInput) {
	var onPage=0, xKey, key, id, o;
	for(var xKey in items){
		onPage++
		key=items[xKey].id;
		if(!(testWhen(items[xKey].when))) continue;
		var id='contentBox'+key;
		if(document.getElementById(id)) o=document.getElementById(id);
		else {
			if((nCnt>4 && !isInput) || nCnt>5) {
				if(items[xKey].type=='spacer'){
					if (Math.floor(onPage/2)*2==onPage) {
						o=document.createElement('div');
						o.setAttribute('class',boxClass+'Spacer');
						o.style.marginBottom='-9px';
						contentBox.appendChild(o);
					}else continue;
				}else if(items[xKey].type=='endPage'){
					while (onPage<12) {
						o=document.createElement('div');
						o.setAttribute('class',boxClass+'Spacer');
						o.style.marginBottom='-9px';
						contentBox.appendChild(o);
						onPage++;
					}
					onPage=0;
					continue;
				}else{
					o=createItemBox(items[xKey], id, boxClass, key);
				}
				if((multiPage)){
					if(items[xKey].type=='spacer'){
						o.style.margin='6px auto -8px 0';
					}else o.style.marginBottom='-9px';
				}
				contentBox.appendChild(o);
			} else {
				if(!(key)) key=xKey;
				var o=createSetupEl(key, '', items[xKey].options,
										  (items[xKey].setupVal?items[xKey].setupVal():values[key]),true);
				if(items[xKey].idw){
					o.setAttribute('idValW', items[xKey].idw);
				}
				if(items[xKey].setupVal){
					o.setValueX=o.setValue;
					o.getMyVal=items[xKey].setupVal;
					o.setValue=function(value, refresh){
						if(refresh)
							this.setValueX(this.getMyVal(), true);
						else
							this.setValueX(value);
					}
				}
				if(items[xKey].saveVal)
					o.saveVal=items[xKey].saveVal;

				o.setAttribute('id', id);

				if(items[xKey].type=='info'){
					o.setAttribute('class','boxItemLongInfo');
					contentBox.appendChild(o);
					switch(o.childNodes[1].tagName){
						case 'INPUT':
							o.childNodes[1].readOnly=true;
							break;
						case 'SPAN': // datetime
							o.onmousedown=null;
							o.onmouseup=null;
							o.onclick=null;
					}
					if(nCnt==5){
						if(o.type=='input'){
							o.setAttribute('class','boxItemLongInfoLow');
							o.style.height='80px';
							o.style.marginTop='2px';
							o.style.marginBottom='-5px';
						}else{
							o.style.marginTop='0px';
							o.style.marginBottom='-5px';
						}
					}
				}else{
					o.setAttribute('class','boxItemLong');
					contentBox.appendChild(o);
					if(nCnt==5){
						if(o.type=='input'){
							o.setAttribute('class','boxItemLongInput');
							o.style.height='80px';
							o.style.marginTop='2px';
							o.style.marginBottom='-5px';
						}else{
							o.style.marginTop='0px';
							o.style.marginBottom='-5px';
						}
					}

				}
				var idOpt=items[xKey].options;
				if(options[idOpt].type=='range' || options[idOpt].type=='rangeEnum')	o.changeValue(0);
			}
		}
		if(o.getElementsByTagName('h3').length>0)
			o.getElementsByTagName('h3')[0].innerHTML=items[xKey].title;
	}
}
function createItemBox(item, id, boxClass, key) {
	var o=document.createElement('div'), tmp;
	o.setAttribute('id', id);
	o.setAttribute('class',boxClass+(item.type && item.type=='info'?'Info':''));
	o.setAttribute('idVal',key);
	o.setAttribute('value','');
	o.value='';
	o.setAttribute('options',item.options);
	o.appendChild(document.createElement('h3'));
	o.setEnabled=function(enabled) {
		this.enabled=enabled;
		if(enabled) this.childNodes[1].style.color='';
		else this.childNodes[1].style.color='#ccc';
	}
	var tmp=document.createElement('div');
	o.appendChild(tmp);
	o.setAttribute('enabled','');
	o.enabled=true;
	if(item.idw){
		o.title=item.title;
		o.titleW=item.titlew;
		o.v1=document.createElement('div'); o.v2=document.createElement('div');
		o.v1.setAttribute('style','margin-top:0px;float:left;width:100%; height:60px; padding-top:20px; color:#888;')
		o.v2.setAttribute('style','display:block;float:left;clear:left;width:100%; height:60px; padding-top:20px;')
		o.childNodes[1].appendChild(o.v1); o.childNodes[1].appendChild(o.v2);
		o.childNodes[1].setAttribute('style','overflow:hidden;height:80px;padding:0;margin-top:10px;')

		o.setAttribute('idValW', item.idw);
		o.setAttribute('valueW','');
		o.valueW='';
		o.dTimer=false;
		o.rVal=false;
		if(item.type!=='info') {
			o.onmousedown=function(e) {
				if(checkRule(this.getAttribute('idValW'))){
					setupOption(this.getAttribute('idValW'), this.titleW, this.getAttribute('options'), this.getAttribute('valueW'), this);
				}
			};
		}
		o.display=function(start){
			var mTop=Number(this.v1.style.marginTop.replace('px',''));
			if(start)
				this.direction=(mTop<0?5:-5);
			mTop+=this.direction;
			this.v1.style.marginTop=mTop.toString()+'px';
			var id=this.getAttribute('id');
			if(mTop===0 || mTop==-80){
				setTimeout('if(document.getElementById("'+id+'")) document.getElementById("'+id+'").display(true);',3000);
			}else{
				if(mTop==-40) this.getElementsByTagName('h3')[0].innerHTML=(this.direction<0?this.titleW:this.title);
				setTimeout('if(document.getElementById("'+id+'")) document.getElementById("'+id+'").display();',50);
			}

		}

		o.setValue=function(value, refresh) {
			if(typeof(value)=='object'){
				this.v1.innerHTML=options[this.getAttribute('options')].display(value[0]);
				this.setAttribute('value', value[1]);
			}else{
				try{
					if(this.displayVal){
						value=this.displayVal();
						if(typeof(value)=='string')
							this.v1.innerHTML=value;
						else
							this.v1.innerHTML=options[this.getAttribute('options')].display(value);
					}else{
						this.v1.innerHTML=options[this.getAttribute('options')].display(value);
					}
				}catch(e){
					alert('Bad option '+this.getAttribute('options'));
				}
				this.setAttribute('value', value);
			}
		}
		o.setValueW=function(value, refresh) {
			if(typeof(value)=='object'){
				this.childNodes[1].childNodes[1].innerHTML=options[this.getAttribute('options')].display(value[0]);
				this.setAttribute('valueW', value[1]);
			}else{
				this.childNodes[1].childNodes[1].innerHTML=options[this.getAttribute('options')].display(value);
				this.setAttribute('valueW', value);
			}
		}
		setTimeout('if(document.getElementById("'+id+'")) document.getElementById("'+id+'").display(true);',2000);
	}else{
		tmp.appendChild(document.createTextNode('--'));
		if(item.options=='FilterChange'){
			o.childNodes[1].style.paddingTop='10px';
			o.ids=item.ids;
			o.setAttribute('idVal',o.ids[0]);
			o.values=new Array();
			o.display=function(dt){
				var keys=this.ids;
				if(keys.length==2 && !isNaN(this.values[keys[1]])){
					if(!dt){
						dt=new Date();
						var now=new Date();
						dt.setTime((this.values[keys[0]]*65536+(this.values[keys[1]]<0?this.values[keys[1]]+65535:this.values[keys[1]]))*1000);
						dt.setHours(0);
						dt.setMinutes(0);
						dt.setSeconds(0);
					}
	//				this.childNodes[1].childNodes[1].innerHTML=dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear();
					this.childNodes[1].innerHTML='<span style="font-size:22px" class="descript">'+words.dtFilterChange+':</span><span style="font-size:22px">'+dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear()+'</span>';
					if(dt.getTime()<now.getTime()){
						var btn=createElement('span', 'button', document.createTextNode(words.confirmFilter));
						btn.setAttribute('style', 'display:block;float:none; margin:10px auto 0 auto');
						btn.onmouseup=function(e){
							if(confirm(words.confFilterQuest+'?')){
								var dt=new Date();
								dt=new Date(dt.getFullYear(), dt.getMonth()+(values['C10513']==1?6:3), dt.getDate());
								var utc=Math.floor(dt.getTime()/1000),
										h=Math.floor(utc/65536), l=utc-(h*65536);
								var keys=this.parentNode.parentNode.getAttribute('idVal').split(',');
								values[keys[0]]=h; values[keys[1]]=l;
								send2Unit(getUrlPar(keys[0], h)+'&'+getUrlPar(keys[1], l));
								this.parentNode.parentNode.display(dt);
							}
						}
						this.childNodes[1].appendChild(btn);
					}
				}
			}
			o.setValue=function(value, refresh) {
				this.values[this.ids[0]]=value;
				this.values[this.ids[1]]=values[this.ids[1]];
				this.display();
			}
		}else if(item.options=='DateTime'){
			o.ids=item.ids;
			o.setAttribute('idVal',o.ids[0]);
			o.values=new Array();

			if(item.type!=='info') {
				o.getValue=function(){
					var keys=this.ids;
					return new Date(this.values[keys[0]], this.values[keys[1]], this.values[keys[2]], this.values[keys[3]], this.values[keys[4]]);
				}
				o.setDateTime=function(dt){
					var keys=this.ids;
					this.values[keys[0]]=dt.getFullYear();
					this.values[keys[1]]=dt.getMonth();
					this.values[keys[2]]=dt.getDate();
					this.values[keys[3]]=dt.getHours();
					this.values[keys[4]]=dt.getMinutes();
					document.getElementById('content').dateChanged=true;
					this.display(dt);
				}

				o.onmousedown=function(e) {
					this.calendar=new calendar(this);
/*										if(checkRule(this.getAttribute('idVal'))){
						setupOption(this.ids,
											this.getElementsByTagName('h3')[0].innerHTML,
											this.getAttribute('options'),
											this.values, this);
					}
*/
				};
			}

			o.display=function(dt){
				var keys=this.ids, parms='';
				if(keys.length==5 && !isNaN(this.values[keys[1]])){
					if(values.C10800==0 && !(document.getElementById('content').dateChanged)){
						dt=new Date();
						if(this.ids[0]=='H10809'){
							dt.setHours(dt.getHours()+1);
						}
						this.values[this.ids[0]]=dt.getFullYear();
						this.values[this.ids[1]]=dt.getMonth();
						this.values[this.ids[2]]=dt.getDate();
						this.values[this.ids[3]]=dt.getHours();
						this.values[this.ids[4]]=dt.getMinutes();

						for(var i=0; i<5; i++){
							values[this.ids[i]]=this.values[this.ids[i]];
							parms+=(parms==''?'':'&')+getUrlPar(this.ids[i], this.values[this.ids[i]]);
						}
						send2Unit(parms);

					}else{
//												alert(this.ids[0])
						if(!dt){
							dt=new Date(this.values[keys[0]],
											this.values[keys[1]],
											this.values[keys[2]],
											this.values[keys[3]],
											this.values[keys[4]],0,0);
						}
					}
					this.childNodes[1].innerHTML='<span style="font-size:22px">'+dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear()+
					(dt.getHours()<10?' 0':' ')+dt.getHours()+
					(dt.getMinutes()<10?':0':':')+dt.getMinutes()+'</span>';
				}
			}

			o.setValue=function(value, refresh) {
				this.values[this.ids[0]]=value;
				this.values[this.ids[1]]=values[this.ids[1]];
				this.values[this.ids[2]]=values[this.ids[2]];
				this.values[this.ids[3]]=values[this.ids[3]];
				this.values[this.ids[4]]=values[this.ids[4]];
				this.display();
			}
//									o.type='input';

		}else{
			if(item.type!=='info') {
				o.onmousedown=function(e) {
					if(checkRule(this.getAttribute('idVal'))){
//											alert(this.displayVal)
						setupOption(this.getAttribute('idVal'),
											this.getElementsByTagName('h3')[0].innerHTML,
											this.getAttribute('options'),
											(this.setupVal?this.setupVal():(this.displayVal?this.displayVal():this.getAttribute('value'))),
											this);
					}
				};
			}
			o.setValue=function(value, refresh) {
				if(typeof(value)=='object'){
					this.childNodes[1].innerHTML=options[this.getAttribute('options')].display(value[0]);
					this.setAttribute('value', value[1]);
				}else{
					this.childNodes[1].innerHTML=options[this.getAttribute('options')].display((this.displayVal?this.displayVal():value));
					this.setAttribute('value', value);
				}
			}
		}
	}
	if(item.onChange) o.onChange=item.onChange;
	if(item.displayVal) o.displayVal=item.displayVal;
	if(item.setupVal) o.setupVal=item.setupVal;
	return o;
}

function createContent(content) {
	switch(content.type) {
		case 'holiday':
			el=createHoliday();
			break;
		case 'netSetup':
			el=createNetSetup();
			break;
		case 'actSetup':
			activeDay=parseInt(activeContent.substr(4));

//			if (values.H10533==1) {
			var contentBox=document.getElementById('content'),
				bmWidth=30, boxWidth=700, boxes, pages={vzt:{title:words.vztTitle}}, cntPages=0;
			if (values.H10533==1) pages.izt={title:words.iztTitle};

			for(var pgKey in pages){
				contentBox.appendChild(createElement('div', 'multiPage'));
				contentBox.lastChild.key=pgKey;
				contentBox.lastChild.style.width=(boxWidth+bmWidth)+'px';
				contentBox.lastChild.style.marginLeft=pgKey=='vzt'?'-9px':'-2px';
				contentBox.lastChild.setAttribute('active',(pgKey==lastPrg?'1':'0'))
				contentBox.lastChild.appendChild(createElement('div', false, document.createTextNode(pages[pgKey].title)));
				contentBox.lastChild.lastChild.onclick=function(){
					clearGraphs(lastPrg);
					var pages=this.parentNode.parentNode.childNodes;
					for(var i=0; i<pages.length; i++) pages[i].setAttribute('active','0');
					this.parentNode.setAttribute('active', '1');
					lastPrg=this.parentNode.key;
					body.menus[activePage].menus[activeContent].content.source=urlWeekPrg[activePage][lastPrg][0];
					body.menus[activePage].menus[activeContent].content.target=urlWeekPrg[activePage][lastPrg][1];
					setTimeout("rq('getSetting')",800);
				}
				contentBox.lastChild.appendChild(createElement('div', false, false,
						{style:"float:left; display: grid; grid-template-columns: auto auto; max-width:"+boxWidth+'px'}));
				var el=createElement('div', 'actSetup', createRestButton(), {style:'margin-left:-13px;'});
				el.appendChild(createCopyButton());
				el.appendChild(createACTemp(pgKey=='izt'));
				contentBox.lastChild.lastChild.appendChild(el);
			}
			body.menus[activePage].menus[activeContent].content.source=urlWeekPrg[activePage][lastPrg][0];
			body.menus[activePage].menus[activeContent].content.target=urlWeekPrg[activePage][lastPrg][1];
			rq('getSetting');
			el=false;

				//code
/*			}else{
				var el=createElement('div','actSetup',createRestButton());
				el.appendChild(createCopyButton());
				el.appendChild(createACTemp());
			}
*/
			break;
		case 'swInfo':
			var el=document.createElement('div'), o, key='UnitName';
			el.setAttribute('class', 'netSetup');

			o=document.createElement('div');
			el.appendChild(o);
			o.setAttribute('id', key);
			o.setAttribute('class','boxItem');
			o.setAttribute('style', 'margin-left:135px')
			o.setAttribute('idVal',key);
			o.value=values[key];
			o.setAttribute('options','String');
			o.appendChild(document.createElement('h3'));
			o.lastChild.appendChild(document.createTextNode(words.unitName))
			o.lastChild.setAttribute('style','color:#fff;margin:0;text-align:center');

			var tmp=document.createElement('div');
			o.appendChild(tmp);
			tmp.appendChild(document.createTextNode(o.value));
			o.onmousedown=function(e) {
					setupOption(this.getAttribute('idVal'),
										this.getElementsByTagName('h3')[0].innerHTML,
										this.getAttribute('options'),
										this.value,
										this);
			};
			o.onChange=function(value) {
				this.value=value;
				this.childNodes[1].innerHTML=''
				this.childNodes[1].appendChild(document.createTextNode(value));
				values[this.getAttribute('idVal')]=value;
				document.getElementById('pageTitle').getElementsByTagName('h2')[0].innerHTML='';
				document.getElementById('pageTitle').getElementsByTagName('h2')[0].appendChild(document.createTextNode(values.UnitName));
			}

			el.appendChild(unitInfo());

			break;
		case 'html':
			var from, to, key,
				el=document.createElement('div');
			el.setAttribute('class', 'netSetup');
			while(content.code.indexOf('<%')>=0){
				from=content.code.indexOf('<%');
				to=content.code.indexOf('%>');
				key=content.code.substr(from+2,to-from-2);
				content.code=content.code.substr(0,from)+values[key]+content.code.substr(to+2);
			}

			el.innerHTML=content.code;
			break;
		case 'alarms':
			var el=document.createElement('div');
			el.setAttribute('class', 'netSetup');
			el.appendChild(document.createElement('h3'));
			el.childNodes[0].appendChild(document.createTextNode(words['activeAlarms']));

			var tmp= document.createElement('div');
			tmp.setAttribute('class', 'button');
			tmp.setAttribute("style","position:absolute; bottom:50px; right:260px")
			tmp.innerHTML=words['reset'];
			tmp.onmousedown=function() {
				send2Unit(getUrlPar('C10005',1));
				showOK();
			}
			el.appendChild(tmp);

			var cont=document.createElement('div');
			cont.setAttribute('class','frame');
			//el.appendChild(frame);

//			var cont=document.createElement('ul');
//			cont.setAttribute('class','list');

			if(activeAlarm || activeWarning){
				var d=new Date(), utc=-(getTimezoneOffset(d)/60), tmp, butt;
				if(values.H11400==0 || !(timeZones[values.H11400]) || timeZones[values.H11400].utc!==utc){
					var i, opt;
					tmp=document.createElement('div');
					tmp.setAttribute('class', 'item');
					tmp.appendChild(document.createTextNode(words.badTimeZone));
					tmp.style.paddingTop="11px";
					butt=document.createElement('div');
					butt.appendChild(document.createTextNode(words.set));
					butt.setAttribute('class', 'button');
					butt.setAttribute('style','float:right; clear:none; margin:-13px 30px -8px auto; font-size:18px;padding-top:13px;')
					tmp.appendChild(butt);
					butt.onmouseup=function() {
						activePage='TZ';
/*						var d=new Date();
						values.H11400=-getTimezoneOffset(d)/60;
						send2Unit(getUrlPar('H11400', values.H11400));
*/
						document.getElementById('smog').style.bottom="25px";
						document.getElementById('smog').style.visibility='visible';
						var wnd=document.createElement('div');
						wnd.setAttribute('class', 'boxBigBig');
						wnd.style.zIndex="5000";
						wnd.appendChild(document.createElement('h3'));
						wnd.lastChild.appendChild(document.createTextNode(words.settingTZ));
						wnd.appendChild(document.createElement('div'));
						wnd.lastChild.setAttribute('class', 'fullArea');
						wnd.lastChild.appendChild(document.createTextNode(words.timeZone));
						wnd.lastChild.appendChild(document.createElement('select'));
						for(var i=1; i<timeZones.length; i++){
							opt=document.createElement('option');
							opt.setAttribute('value', i);

							var hours=parseInt(Math.abs(timeZones[i].utc)),
								minutes=(Math.abs(timeZones[i].utc)-hours)*60,
								cTime=(timeZones[i].utc>0?'+':(timeZones[i].utc<0?'-':' '))+(hours<10?'0':'')+hours+':'+
										(minutes<10?'0':'')+minutes;

							opt.appendChild(document.createTextNode(cTime+' '+timeZones[i].title));
							wnd.lastChild.lastChild.appendChild(opt);
						}

						wnd.lastChild.lastChild.onchange=function(){
							values.H11400=Number(this.value);
//							this.parentNode.parentNode.login();
						}


						wnd.appendChild(document.createElement('div'));
						wnd.lastChild.setAttribute('class','button');
						wnd.lastChild.style.marginBottom='-20px';
						wnd.lastChild.appendChild(document.createTextNode(words.save));
						wnd.lastChild.onmouseup=function(){
							document.getElementById('smog').style.visibility='hidden';
							activePage='AL';
							send2Unit(getUrlPar('H11400', values.H11400));
							showOK();
							showPage();
						};
						document.getElementById('mainBlock').appendChild(wnd);
						return;

					}
					cont.appendChild(tmp);
				}
				var dUnit=new Date(values.I00004, values.I00005-1, values.I00006, values.I00007, values.I00008, values.I00009);
				if(Math.abs(dUnit.getTime()-d.getTime())>900000){
					tmp=document.createElement('div'); tmp.setAttribute('class', 'item');
					tmp.appendChild(document.createTextNode(words.badTime));
					tmp.style.paddingTop="11px";
					butt=document.createElement('div');
					butt.appendChild(document.createTextNode(words.setByPC));
					butt.setAttribute('class', 'button');
					butt.setAttribute('style','float:right; clear:none; margin:-13px 30px -8px auto; font-size:18px;padding-top:13px;')
//					butt.setAttribute('style','float:right; clear:none; margin:0; margin-top:-13px; font-size:18px;padding-top:13px;')
					tmp.appendChild(butt);
					butt.onmouseup=function() {
						var d=new Date();
						send2Unit(getUrlPar('H10905', d.getFullYear())+'&'+
									 getUrlPar('H10906', d.getMonth()+1)+'&'+
									 getUrlPar('H10907', d.getDate())+'&'+
									 getUrlPar('H10908', d.getHours())+'&'+
									 getUrlPar('H10909', d.getMinutes())+'&'+
									 getUrlPar('C00003',1));
						showOK();
						showPage();
					}
					cont.appendChild(tmp);
				}
				for(var i=0; i<alarmKeys.length;i++)
					if(values[alarmKeys[i]]==1){
						tmp=document.createElement('div');
						tmp.setAttribute('class', 'item');
						tmp.appendChild(document.createTextNode(params[alarmKeys[i]].title));
						cont.appendChild(tmp);
					}
				for(var i=0; i<warnKeys.length;i++)
					if(values[warnKeys[i]]==1){
						tmp=document.createElement('div');
						tmp.setAttribute('class', 'item');
						tmp.setAttribute('warning', '1');
						tmp.appendChild(document.createTextNode(params[warnKeys[i]].title));
						cont.appendChild(tmp);
						if(warnKeys[i]=='D11183' && (values.H10512==1||values.H10512==3)){
//						if(warnKeys[i]=='D11122' && values.H10512==1){
							tmp.style.paddingTop="11px";
							butt=document.createElement('div');
							butt.appendChild(document.createTextNode(words.confirmFilter));
							butt.setAttribute('class', 'button');
							butt.setAttribute('style','float:right; clear:none; margin:-13px 30px -8px auto; font-size:18px;padding-top:13px;')
							tmp.appendChild(butt);
							butt.onmouseup=function() {
								var d=new Date();
								send2Unit(getUrlPar('C10007',1));
								showOK();
								showPage();
							}

						}
					}
			}else{
				cont.style.borderColor='green';
				var tmp=document.createElement('li'); tmp.setAttribute('class', 'item')
				tmp.appendChild(document.createTextNode(words['noAlarmDetected']));
				cont.appendChild(tmp);
			}
			el.appendChild(cont);
			break;
		case 'passwd':
			el=document.createElement('div');
			el.setAttribute('class', 'netSetup');
			el.innerHTML='<form style="padding-bottom:20px"><table style="border:1px outset; box-shadow:2px 2px 5px #666; width:400px; margin-left:100px; padding:5px;">'+
'<tr><th colspan="2" style="font-size:18px; text-align:center;border-bottom:solid 2px navy">'+words.passwordMenu+'</th></tr>'+
'<tr><th>'+words.passwordOld+':</th><td><input type="password" name="old"></td></tr>'+
'<tr><th>'+words.passwordNew+':</th><td><input type="password" name="new"></td></tr>'+
'<tr><th>'+words.passwordConfirm+':</th><td><input type="password" name="check"></td></tr>'+
'<tr><td></td><td></td></tr>'+
'</table><input type="submit" class="button" value="'+words.save+'" style="margin-top:10px;padding-top:10px"></form>'+

'<form style="padding-bottom:20px"><table style="border:1px outset; box-shadow:2px 2px 5px #666; width:400px; margin-left:100px; padding:5px;">'+
'<tr><th colspan="2" style="font-size:18px; text-align:center;border-bottom:solid 2px navy">'+words.resetUserPass+':</th></tr>'+
'<tr><th>'+words.servicePass+':</th><td><input type="password" name="old"></td></tr>'+
'<tr><td></td><td></td></tr>'+
'</table><input type="submit" class="button" value="'+words.reset+'" style="margin-top:10px;padding-top:10px"></form>';
/*
+


'<form style="padding-bottom:20px"><table style="border:1px outset; box-shadow:2px 2px 5px #666; width:400px; margin-left:100px; padding:5px;">'+
'<tr><th colspan="2" style="font-size:18px; text-align:center;border-bottom:solid 2px navy">'+words.resetSrvcPass+':</th></tr>'+
'<tr><th>'+words.passwordOld+':</th><td><input type="password" name="old"></td></tr>'+
'<tr><td></td><td></td></tr>'+
'</table><input type="submit" class="button" value="'+words.reset+'" style="margin-top:10px;padding-top:10px"></form>';
 */


			el.firstChild.onsubmit=function(){
				var els=this.getElementsByTagName('input');
				if(els[0].value.length==0 || els[1].value.length==0 || els[2].value.length==0){
					alert(words.enterAllFields);
					return false;
				}
				if(els[1].value!==els[2].value){
					alert(words.passwordNoChk);
					return false;
				}
				if(els[1].value.replace(/[a-z]|\d/gi,'').length>0){
					alert(words.passwordBad);
					return false;
				}
				var doc=sendSync(urlPasswd,'auth='+user.auth+'&old='+md5("\r\n"+els[0].value)+'&new='+md5("\r\n"+els[1].value)+'&cmd=0&'+randStr(2));
				if(doc && doc.documentElement){
					if(doc.documentElement.textContent=='ok'){
						alert(words.passwordSaved);
						els[0].value=''; els[1].value=''; els[2].value='';
						return false;
					}else if(doc.documentElement.textContent=='denied'){
						alert(words.passwordSaveErr);
						return false;
					}else if(doc.documentElement.textContent=='wait'){
						wait('pleaseWait');
						function waitForPwd() {
							var doc=sendSync(urlPasswd,'rnd='+randStr(3));
							if(doc && doc.documentElement){
								if(doc.documentElement.textContent=='ok'){
									alert(words.passwordSaved);
									wait();
								}else if(doc.documentElement.textContent=='denied'){
									alert(words.passwordSaveErr);
									wait();
								}else if(doc.documentElement.textContent=='wait'){
									setTimeout(waitForPwd,1000);
								}
							}else{
								alert(words.passwordSaveErr);
								wait();
							}
						}
						setTimeout(waitForPwd,1000);
						els[0].value=''; els[1].value=''; els[2].value='';
						return false;
					}
				}
/* Odzkouset */
				alert(words.passwordSaveErr);
				return false;
			}
			el.childNodes[1].cmd=1;
//			el.childNodes[2].cmd=2;
			el.childNodes[1].onsubmit=function(){
				var els=this.getElementsByTagName('input');
				if(els[0].value.length==0){
					alert(words.enterAllFields);
					return false;
				}
				var doc=sendSync(urlPasswd,'auth='+user.auth+'&old='+md5("\r\n"+els[0].value)+'&new=&cmd='+this.cmd+'&'+randStr(2));
				if(doc && doc.documentElement){
					if(doc.documentElement.textContent=='ok'){
						alert(words.passwordSaved);
						els[0].value='';
						return false;
					} else if(doc.documentElement.textContent=='denied'){
						alert(words.passwordSaveErr);
						return false;
					}else if(doc.documentElement.textContent=='wait'){
						wait('pleaseWait');
						function waitForPwd() {
							var doc=sendSync(urlPasswd,'rnd='+randStr(3));
							if(doc && doc.documentElement){
								if(doc.documentElement.textContent=='ok'){
									alert(words.passwordSaved);
									wait();
								}else if(doc.documentElement.textContent=='denied'){
									alert(words.passwordSaveErr);
									wait();
								}else if(doc.documentElement.textContent=='wait'){
									setTimeout(waitForPwd,1000);
								}
							}else{
								alert(words.passwordSaveErr);
								wait();
							}
						}
						setTimeout(waitForPwd,1000);
						els[0].value='';
						return false;
					}
				}
				alert(words.passwordSaveErr);
				return false;
			}
	//		el.childNodes[2].onsubmit=el.childNodes[1].onsubmit;
			break;
		default:
			alert("Unknown content type:"+content.type);
			break;
	}
	return el;
}

function createHoliday(){
	el=document.createElement('div');
	el.setAttribute('class', 'netSetup');
	el.oMonths=[];
	el.oDays=[];
	el.holidays=[];
	el.vacations=[];
	el.modeSet=1; // 1 - holiday, 2 - startVac, 3 - stopVac
	el.startVac=[];


	el.onDayClick=function(nM, nD){
		switch(this.modeSet){
			case 1:
				this.holidaySet(nM,nD);
				break;
			case 2:
				this.startVac=[nM, nD];
				this.setMode(3);
				this.vacationShow(nM, nD);
				break;
			case 3:
				this.vacationSet(this.startVac[0], this.startVac[1], nM, nD, 1);
				this.setMode(2);
				break;
		}
		this.refreshInfo();
	};
	el.onDayMove=function(nM, nD){
		if(this.modeSet==3){
			this.vacationShow(nM, nD);
		}
	}

	el.holidaySet=function(nM, nD, act){
		if(nD>0){
			var obj=this.oMonths[nM].oDays[nD-1], idx;
			if(obj.getAttribute('isHoliday')){
				obj.removeAttribute('isHoliday');
				for(idx=0; idx<this.holidays.length; idx++){
					if(this.holidays[idx][0]==nM*100+nD){
						this.holidays.splice(idx,1);
					}
				}
			}else{
				obj.setAttribute('isHoliday',(typeof(act)=='number'? act.toString():'1'));
				this.holidays.push([nM*100+nD, (typeof(act)=='number'? act:1)]);
			}
			if(typeof(act)!='number')
				this.refreshInfo();
		}
	};
	el.vacationShow=function(endM, endD){
		var obj, idx, nM, nD;
		for(nM=0; nM<12; nM++)
			for(nD=0; nD<this.oMonths[nM].oDays.length; nD++)
				this.oMonths[nM].oDays[nD].removeAttribute('vacOver');
		if(this.startVac[0]>endM || (this.startVac[0]==endM && this.startVac[1]>endD)){
			nM=endM;
			nD=endD;
			endM=this.startVac[0];
			endD=this.startVac[1];
		}else{

			nM=this.startVac[0];
			nD=this.startVac[1];
		}
		while(true){
			if((this.oMonths[nM].oDays[nD-1])){
				obj=this.oMonths[nM].oDays[nD-1];
				obj.setAttribute('vacOver', "1");
				if(nM==endM && nD==endD) break;
				nD++;
			}else{
				nM++;
				if(nM==12) nM=0;
				nD=1;
			}
		}
	};
	el.vacationSet=function(nM, nD, endM, endD, act){
		var obj, idx, iD, iM, tmp;
		if (typeof(act)!='number') act=1;
		if (nM*100+nD>endM*100+endD) {
			tmp=nM; nM=endM; endM=tmp;
			tmp=nD; nD=endD; endD=tmp;
		}
		this.vacations.push([nM*100+nD, endM*100+endD,act]);
		while(true){
			if((this.oMonths[nM].oDays[nD-1])){
				obj=this.oMonths[nM].oDays[nD-1];
				obj.setAttribute('isVacation', act);
				obj.removeAttribute('vacOver');
				if(nM==endM && nD==endD) break;
				nD++;
			}else{
				nM++;
				if(nM==12) nM=0;
				nD=1;
			}
		}
	};
	el.vacationUnset=function(i){
		var nM=Math.floor(this.vacations[i][0]/100),
			nD=this.vacations[i][0]-nM*100,
			endM=Math.floor(this.vacations[i][1]/100),
			endD=this.vacations[i][1]-endM*100;
		this.vacations.splice(i,1);
		while(true){
			if((this.oMonths[nM].oDays[nD-1])){
				obj=this.oMonths[nM].oDays[nD-1];
				for(i=0; i<this.vacations.length; i++){
					if(this.vacations[i][0]<=this.vacations[i][1]){
						if(this.vacations[i][0]<=nM*100+nD && this.vacations[i][1]>=nM*100+nD)
							break;
					}else{
						if(this.vacations[i][0]<=nM*100+nD || this.vacations[i][1]<=nM*100+nD)
							break;
					}
				}
				if(i==this.vacations.length)
					obj.removeAttribute('isVacation');
				if(nM==endM && nD==endD) break;
				nD++;
			}else{
				nM++;
				if(nM==12) nM=0;
				nD=1;
			}
		}
	}
	el.holidayRefresh=function(nM, nD, act){
		this.oMonths[nM].oDays[nD-1].setAttribute('isHoliday', act);
	}
	el.vacationRefresh=function(i){
		var nM=Math.floor(this.vacations[i][0]/100),
			nD=this.vacations[i][0]-nM*100,
			endM=Math.floor(this.vacations[i][1]/100),
			endD=this.vacations[i][1]-endM*100;
		while(true){
			if((this.oMonths[nM].oDays[nD-1])){
				obj=this.oMonths[nM].oDays[nD-1];
				obj.setAttribute('isVacation', this.vacations[i][2]);
				if(nM==endM && nD==endD) break;
				nD++;
			}else{
				if(nM==endM && nD==endD) break;
				nM++;
				if(nM==12) nM=0;
				nD=1;
			}
		}
	}
	el.refreshInfo=function(){
		var i=0, j, boxs;
		this.holidays.sort(function(a, b){return a[0]-b[0]});
		this.vacations.sort(function(a, b){return a[0]-b[0]});
		boxs=this.holBox.childNodes;
		for(j=0; j<boxs.length; j++){
			if(boxs[j].tagName=="DIV"){
				boxs[j].firstChild.innerHTML='';
				if((this.holidays[i])){
					boxs[j].date=this.holidays[i][0]-(Math.floor(this.holidays[i][0]/100))*100;
					boxs[j].month=Math.floor(this.holidays[i][0]/100);
					boxs[j].firstChild.appendChild(document.createTextNode(boxs[j].date+'.'+
							(boxs[j].month+1)+'.'));
					boxs[j].setAttribute('isSet','1');
					boxs[j].setAttribute('active', (this.holidays[i][1]?"1":"0"));
				}else{
					boxs[j].firstChild.appendChild(document.createTextNode('---'));
					boxs[j].date=0;
					boxs[j].removeAttribute('active');
					boxs[j].removeAttribute('isSet');
				}
				i++;
			}
		}
		boxs=this.vacBox.childNodes;
		i=0;
		for(j=0; j<boxs.length; j++){
			if(boxs[j].tagName=="DIV"){
				boxs[j].firstChild.innerHTML='';
				if((this.vacations[i])){
					boxs[j].startDate=this.vacations[i][0]-(Math.floor(this.vacations[i][0]/100))*100;
					boxs[j].startMonth=Math.floor(this.vacations[i][0]/100);
					boxs[j].endDate=this.vacations[i][1]-(Math.floor(this.vacations[i][1]/100))*100;
					boxs[j].endMonth=Math.floor(this.vacations[i][1]/100);
					boxs[j].firstChild.appendChild(document.createTextNode(boxs[j].startDate+'.'+(boxs[j].startMonth+1)+'. - '+
																			  boxs[j].endDate+'.'+(boxs[j].endMonth+1)+'.'));
					boxs[j].idx=i;
					boxs[j].setAttribute('active', (this.vacations[i][2]?"1":"0"));
					boxs[j].setAttribute('isSet','1');
				}else{
					boxs[j].firstChild.appendChild(document.createTextNode('---'));
					boxs[j].idx=-1;
					boxs[j].removeAttribute('isSet');
					boxs[j].removeAttribute('active');
				}
				i++
			}
		}
	}

	var d=new Date(), m=1, nY=d.getFullYear(), elM;
	d.setDate(1);
	d.setMonth(0);
	for(iM=0; iM<12; iM++){
		el.oMonths[iM]=newMonCal(iM, nY);
		el.appendChild(el.oMonths[iM]);
		if (iM-(Math.floor(iM/4)*4)==0) {
			el.lastChild.style.clear="left";
		}
	}

	var i, hex, nM, nD, nMTo, nDTo, hexTo, obj,
		cont=document.createElement('div');

	cont.setAttribute('class', 'holidayCont');
	cont.appendChild(document.createElement('h3'));
	cont.lastChild.appendChild(document.createTextNode(words.holidays));
	cont.onclick=function(){
		this.parentNode.setMode(1);
	};
	el.holBox=cont;
	el.appendChild(cont);
	el.holidays=[];
	for(i=18000; i<18016; i++){
		obj=document.createElement('div');
		obj.appendChild(document.createElement('span'));
		obj.appendChild(document.createElement('div'));
		obj.lastChild.setAttribute('class', 'icoDel');
		if (values['H'+i]) {
			hex=values['H'+i].toString(16);
			if (hex.length==3) hex='0'+hex;
			nM=Number('0x'+hex.substr(0,2));
			nD=Number('0x'+hex.substr(2,2));
			el.holidaySet(nM-1, nD, values['C'+i]);
		}
		obj.onclick=function(e){
			var el=e.srcElement || e.target, idx;
			if(el.getAttribute('class')=='icoDel'){
				this.parentNode.parentNode.setMode(1);
				this.parentNode.parentNode.holidaySet(this.month, this.date);
				this.parentNode.parentNode.refreshInfo();
			}else{
				if(this.date){
					var cont=this.parentNode.parentNode;
					for(idx=0; idx<cont.holidays.length; idx++){
						if(cont.holidays[idx][0]==this.month*100+this.date){
							if(cont.holidays[idx][1]==1){
								cont.holidays[idx][1]=0;
							}else{
								cont.holidays[idx][1]=1;
							}
							cont.holidayRefresh(this.month, this.date, cont.holidays[idx][1]);
							break;
						}
					}
					cont.refreshInfo();
				}
			}
		};
		cont.appendChild(obj);
	}

	cont=document.createElement('div');
	cont.setAttribute('class', 'vacationCont');
	cont.appendChild(document.createElement('h3'));
	cont.lastChild.appendChild(document.createTextNode(words.vacations));
	cont.onclick=function(){
		this.parentNode.setMode(2);
	};
	el.vacBox=cont;
	el.appendChild(cont);
	for(i=18100; i<18107; i=i+2){
		obj=document.createElement('div');
		obj.appendChild(document.createElement('span'));
		obj.appendChild(document.createElement('div'));
		obj.lastChild.setAttribute('class', 'icoDel');
		if (values['H'+i]) {
			hex=values['H'+i].toString(16);
			if (hex.length==3) hex='0'+hex;
			hexTo=values['H'+(i+1)].toString(16);
			if (hexTo.length==3) hexTo='0'+hexTo;

			nM=Number('0x'+hex.substr(0,2));
			nD=Number('0x'+hex.substr(2,2));
			nMTo=Number('0x'+hexTo.substr(0,2));
			nDTo=Number('0x'+hexTo.substr(2,2));
			el.vacationSet(nM-1, nD, nMTo-1, nDTo, values['C'+i]);
//			el.vacations.push([(nM-1)*100+nD, (nMTo-1)*100+nDTo,values['C'+i]]);
		}
		obj.onclick=function(e){
			var el=e.srcElement || e.target, idx;
			this.parentNode.parentNode.setMode(2);
			if(el.getAttribute('class')=='icoDel'){
				if(this.idx>=0){
					this.parentNode.parentNode.vacationUnset(this.idx);
				}
			}else{
				if(this.idx>=0){
					var cont=this.parentNode.parentNode;
					if(cont.vacations[this.idx][2]==1){
						cont.vacations[this.idx][2]=0;
					}else{
						cont.vacations[this.idx][2]=1;
					}
					this.setAttribute('active',cont.vacations[this.idx][2]);
					cont.vacationRefresh(this.idx);
				}

			}
			this.parentNode.parentNode.refreshInfo();
		};
		cont.appendChild(obj);
	}
	obj=document.createElement('div');
	obj.setAttribute('type', 'button');
	obj.setAttribute('id', 'cmdSave');
	obj.setAttribute('class', 'button');
	obj.appendChild(document.createTextNode(words['save']));
	obj.onclick=function(){
		var pars="", nD;
		for(i=0; i<16; i++){
			if(i>0) pars+='&';
			if((this.parentNode.holidays[i])){
				nM=Math.floor(this.parentNode.holidays[i][0]/100);
				nD=this.parentNode.holidays[i][0]-nM*100;
				pars+=getUrlPar('H'+(18000+i),Number('0x'+(nM+1).toString(16)+(nD<16?'0':'')+nD.toString(16)))+'&'+
						getUrlPar('C'+(18000+i),this.parentNode.holidays[i][1]);
			}else{
				pars+=getUrlPar('H'+(18000+i),0)+'&'+getUrlPar('C'+(18000+i),0);
			}
		}
		for(i=0; i<4; i++){
			pars+='&';
			if((this.parentNode.vacations[i])){
				nM=Math.floor(this.parentNode.vacations[i][0]/100);
				nD=this.parentNode.vacations[i][0]-nM*100;
				pars+=getUrlPar('H'+(18100+i*2),Number('0x'+(nM+1).toString(16)+(nD<16?'0':'')+nD.toString(16)))+'&';
				nM=Math.floor(this.parentNode.vacations[i][1]/100);
				nD=this.parentNode.vacations[i][1]-nM*100;
				pars+=getUrlPar('H'+(18100+i*2+1),Number('0x'+(nM+1).toString(16)+(nD<16?'0':'')+nD.toString(16)))+'&'+
						getUrlPar('C'+(18100+i*2),this.parentNode.vacations[i][2]);
			}else{
				pars+=getUrlPar('H'+(18100+i*2),0)+'&'+getUrlPar('H'+(18100+i*2+1),0)+'&'+
							getUrlPar('C'+(18100+i*2),0);
			}
		}
		send2Unit(pars);
		showOK();
	}
	el.setMode=function(mode){
		this.modeSet=mode;
		if (mode==1) {
			this.holBox.setAttribute('active','1');
			this.vacBox.removeAttribute('active');
		}else{
			this.holBox.removeAttribute('active');
			this.vacBox.setAttribute('active','1');
		}
	}
	el.setMode(1);
	el.appendChild(obj);
	el.refreshInfo();
	return el;
}

function createMenuDay(id) {
	var i, ts, cont, hdr, tmp, btn,
		el=document.createElement('div');
	el.setAttribute('id', id);
	for(ts=0; ts<2; ts++){
		cont=document.createElement('div');
		cont.setAttribute('class', 'tsCont');
		hdr=document.createElement('div');
		hdr.setAttribute('class', 'head');
		btn=document.createElement('div');
		btn.setAttribute('class', 'check');
		btn.setAttribute('checked', (activePage==(ts==0?'RTS':'RNS')?'1':'0'));
		hdr.appendChild(btn);
		tmp=document.createElement('span');
		tmp.appendChild(document.createTextNode(ts==0?words.heating:words.nonHeating));
		hdr.appendChild(tmp);
		hdr.value=(activePage==(ts==0?'RTS':'RNS')?true:false);
		hdr.onmouseup=function(){
			this.value=!this.value;
			this.childNodes[0].setAttribute('checked', this.value?1:0);
			for(var i=1; i<10; i++)
				this.parentNode.childNodes[i].setAttribute('enabled', this.value?'1':'0');
		}

		cont.appendChild(hdr);
		for(i=0; i<9; i++) {
			var tmp=document.createElement('div');
			tmp.setAttribute('class', 'dayBox');
			if(i==activeDay && activePage==(ts==0?'RTS':'RNS'))
				tmp.setAttribute('active','1');
			else{
				tmp.setAttribute('selected','0');
				tmp.setAttribute('enabled', (activePage==(ts==0?'RTS':'RNS')?'1':'0'));
				tmp.onmousedown=function(e) {
					if(this.getAttribute('enabled')=='1')
						this.setAttribute('selected',(this.getAttribute('selected')=='0'?'1':'0'));
				};
			}
			tmp.innerHTML=options['Days'].display(i);
			tmp.setAttribute('nDay', i);

			cont.appendChild(tmp);
		}
		el.appendChild(cont);
	}
	if(id=='copyDay') {
		tmp=document.createElement('div');
		tmp.setAttribute('class', 'button');
		tmp.innerHTML=words['copy'];
		tmp.style.marginTop="430px";
		tmp.onmousedown=function() {
			var j=0, dcount, days, sParms='',  cnt=0, ts, i, form, o;
			if (lastPrg=='izt') {
				for(i=0; i<4; i++) {
					o=document.getElementById('recIZT'+i.toString());
					if(o.getAttribute('class')=='rec') {
						sParms+=(sParms==''?'':'x')+o.values[1]+','+o.values[2]+','+formatTime(o.values[0]);
						cnt++;
					}
				}
			}else{
				for(i=0; i<8; i++) {
					o=document.getElementById('recVZT'+i.toString());
					if(o.getAttribute('class')=='rec') {
						sParms+=(sParms==''?'':'x')+
								formatVal(o.values[1], paramKeys['power'])+','+
								formatVal(o.values[2], paramKeys['mode'])+','+
								formatVal(o.values[3], paramKeys['zone'])+','+
								o.values[4]+','+formatTime(o.values[0]);
						cnt++;
					}
				}
			}
			for(ts=0; ts<2; ts++){
				dcount=0, days='';
				form=this.parentNode.childNodes[ts];
				for(i=0; i<9; i++) {
					if(form.childNodes[i+1].getAttribute('selected')=='1' && form.childNodes[i+1].getAttribute('enabled')=='1') {
						dcount++;
						days+=(days==''?'':',')+i;
						flyObj[j]=new showFly(j,form.childNodes[i+1], document.getElementById('mainBlock').childNodes[i]);
						j++;
					}
				}
				if(dcount>0){
					send2Unit('dcount='+dcount+'&days='+days+'&count='+cnt+'&values='+sParms,
								 urlWeekPrg[ts==0?'RTS':'RNS'][lastPrg][1]);
				}
			}
			closeDialog(this.parentNode);
		}

		el.appendChild(tmp);
		tmp=document.createElement('div');
		tmp.setAttribute('class', 'button');
		tmp.innerHTML=words['cancel'];
		tmp.onmousedown=function() {
			closeDialog(this.parentNode);
		}
		el.appendChild(tmp);
	}
	return el;
}
function closeDialog(o) {
	o.style.visibility='hidden';
	o.setAttribute('class', '');
	document.getElementById('smog').style.visibility='hidden';
	o.parentNode.removeChild(o);
}
function create(args) {
	//code
}

function createRestButton() {
	var el= document.createElement('div');
	el.setAttribute('class', 'restButton');
	el.innerHTML=words.restoreSettings;
	el.setAttribute('style', 'float:left;');
	el.onmousedown=function() {
		if (confirm(words.restoreSettings)) {
			send2Unit(getUrlPar((activePage=="RTS"?(lastPrg=='vzt'?'C11400':'C11414'):
										(lastPrg=='vzt'?'C11401':'C11415')), 1),urlDataSet);
			showOK();
			setTimeout("location.reload(true);",2000);
		}
	}
	return el;
}
function createCopyButton() {
	var el= document.createElement('div');
	el.setAttribute('class', 'topButton');
	el.innerHTML=words.copy;
	el.onmousedown=function() {
		document.getElementById('smog').style.visibility='visible';
		tmp=createMenuDay('copyDay');
		document.getElementById('mainBlock').appendChild(tmp);
	}
	return el;
}
/*
function setActiveDay(nDay) {
	if(activeDay!==nDay) {
		document.getElementById('menuDay').childNodes[activeDay].setAttribute('class','dayBox');
		activeDay=nDay;
		document.getElementById('menuDay').childNodes[activeDay].setAttribute('class','dayBoxAct');
		document.getElementById('topDay').setValue(activeDay);
		showRSVals();
	}
}
*/
function createACTemp(isIZT) {
	var el=document.createElement('div'), g=new Array(),
		isTemp=1;
	el.setAttribute('class', 'graphs');

	if (!isIZT) {
		var tmp=document.createElement('h3'), powerBox=false;
		tmp.appendChild(document.createTextNode(words['airCondSetup']));
		el.appendChild(tmp);
		var grBack=document.createElement('div');
		grBack.setAttribute('class', 'graphBack');
	/*	if(options[pwrType].count<8 || values[paramKeys['isTemp']]==0 || isTemp==0) g[0]=createGraph(options[pwrType], 1,1, 100);
		else g[0]=createGraph(options[pwrType], 2,2, 100);
	*/
		if(options[pwrType].type=='boxes')	g[0]=createGraph(options[pwrType], 3);
		else											g[0]=createGraph(options[pwrType], false,1, 100);
		g[0].style.backgroundImage="url('"+server+"style/images/graphPart.png')";
		grBack.appendChild(g[0]);
		g[1]=createGraph(options[modeType], 2);
		g[1].style.backgroundImage="url('"+server+"style/images/graphPart.png')";
		grBack.appendChild(g[1]);
		g[2]=createGraph(options['Zone'], 2);
		g[1].style.backgroundImage="url('"+server+"style/images/graphPart.png')";
		if(options[pwrType].type!='boxes') g[2].style.marginTop="-9px";
		grBack.appendChild(g[2]);
		el.appendChild(grBack);

	// legend
		// legends in window
		tmp=createElement('div','buttonSmallR', document.createTextNode(words.legend), {style:'margin:0 46px 0 0'});
		tmp.onclick=function(){
			var o=createWindow(words.legend), btn;
			o.setContent(this.myCont, true);
			btn=createElement('div', 'buttonSmallR', document.createTextNode(words.cancel), {type:'button'});
			btn.onmousedown=function() {this.parentNode.parentNode.close()};
			o.setFooter(btn, true);
			o.show();
		};
		el.appendChild(tmp);
		tmp.myCont=createElement('div', 'legend');
		var wrDivStyle='clear:left;width:100%;height:1px;margin: 10px auto 10px -21px; background-color:#666;box-shadow: 1px 1px 3px #666; padding:0;';

		if(options[pwrType].type=='boxes'){
			createLegend(options[pwrType], tmp.myCont);
			tmp.myCont.appendChild(createElement('div', false, false, {style: wrDivStyle}));
			powerBox=true;
		}

		createLegend(options[modeType], tmp.myCont);
		tmp.myCont.appendChild(createElement('div', false, false, {style: wrDivStyle}));
		createLegend(options['Zone'], tmp.myCont);
		tmp.myCont.appendChild(createElement('div', false, false, {style: 'clear:left;width:10px;height:1px;margin: 4px; padding:0'}));
		// legends in window - end


		if(isTemp){
			el.appendChild(createElement('h3', false, document.createTextNode(words['tempSetup'])));
			var grBack=document.createElement('div');
			grBack.setAttribute('class', 'graphBack');
			if(isTemp==1){
				g[3]=createGraph(options[tempType], 2,2, 100);
				grBack.appendChild(g[3]);
				el.appendChild(grBack);
			}else{
				g[3]=createGraph(options['OffEnabled'], 2);
				grBack.appendChild(g[3]);
				el.appendChild(grBack);
				var tmp=document.createElement('div');
				tmp.setAttribute('class', 'legend');
				createLegend(options['OffEnabled'], tmp);
				el.appendChild(tmp);
			}
		}
	}
// end legend
	if (isIZT) {
		el.appendChild(createElement('h3', false, document.createTextNode(words['tempSetup'])));
		var grBack=document.createElement('div');
		grBack.setAttribute('class', 'graphBack');
		g[0]=createGraph(options[tempIZT], 2,2, 100);
		grBack.appendChild(g[0]);
		el.appendChild(grBack);
		h=25;
	}else{
		var h=parseInt(([260,240,230][isTemp]-(powerBox?40:0))/((isTemp?g[3].childNodes.length:0)+g[0].childNodes.length));
	}
	for(i=0; i<g.length;i++) {
		g[i].setAttribute('id', 'graph'+(isIZT?'IZT':'VZT')+i.toString());
			for(j=0; j<g[i].childNodes.length; j++) {
				if(j<g[i].childNodes.length-1 || g[i].childNodes.length==1) {
					if(g[i].grType=='enum' || g[i].grType=='boxes'){
						g[i].childNodes[j].style.height=Math.max(h,8).toString()+'px';
						if(h<9 && g[i].childNodes[j].childNodes.length>0){
							g[i].childNodes[j].childNodes[0].style.fontSize='9px';
							g[i].childNodes[j].childNodes[0].style.marginTop='-4px';
						}
					}
					else{
						g[i].childNodes[j].style.height=h.toString()+'px';
						if(h<9 && g[i].childNodes[j].childNodes.length>0){
							if(g[i].childNodes[j].childNodes[0].style){
								g[i].childNodes[j].childNodes[0].style.fontSize='9px'
							}else{
//								g[i].childNodes[j].style.fontSize='9px'
							}
						}
					}
				}else{
					g[i].childNodes[j].style.height='0px';
				}
			}
	}

	var cntDiv=(isIZT?5:7);
//
/*tmp=document.createElement('h3');
	tmp.appendChild(document.createTextNode(words['airCond']));
/*}else{
		var cntDiv=4;
		tmp.appendChild(document.createTextNode(words['temperature']));
	}
	el.appendChild(tmp);
*/
	el.appendChild(createElement('div',false, false, {style:'width:100%; height:20px;'}))
	var mBox=createElement('div', 'recsBack', createElement('div', 'recsLeft')),
		cBox=createElement('div', 'recsCont'),
		vBox=createElement('div', 'recsView', cBox);

	mBox.appendChild(vBox);
	mBox.appendChild(createElement('div', 'recsRight'));
	if (isIZT) {
		mBox.childNodes[0].style.visibility='hidden';
		mBox.childNodes[2].style.visibility='hidden';
		cBox.style.width="100%";
		mBox.style.height="110px";
		vBox.style.height="105px";
	}else{
		mBox.childNodes[0].onmousedown=function(e) {this.parentNode.mover.move(false)};
		mBox.childNodes[2].onmousedown=function(e) {this.parentNode.mover.move(true)};
		mBox.mover={pos:0, records:3, cntRec:(isIZT?4:8), box:mBox.childNodes[1], cont:mBox.childNodes[1].childNodes[0],
			move:function(up){if(up) this.set(this.pos+1);else this.set(this.pos-1);},
			set:function(index){
				var scrollTo=0;
				if(index>this.cntRec) index=this.cntRec-1;
				else if(index<0) index=0;
				for(var i=0; i<this.cont.childNodes.length; i++){
					if(i==index){
						if(this.cont.childNodes[i].getAttribute('class')=='recD'){
							return false;
						}
						this.pos=index;
						this.cont.childNodes[i].setAttribute('class', 'recA');
					}else{
						if(this.cont.childNodes[i].getAttribute('class')=='recA')
							this.cont.childNodes[i].setAttribute('class', 'rec');
					}
				}
				if(index<=1) scroolTo=0;
				else if(index>=7) scrollTo=600;
				else{
					if(this.box.scrollLeft<(index-2)*150+75)
						scrollTo=(index-2)*150;
					else
						scrollTo=(index-1)*150;
				}
				this.box.scrollLeft=scrollTo;
			}
			};
	}

	box=document.createElement('div');
	box.setAttribute('class', 'rec');
	if (isIZT) {
		box.style.height="103px";
	}
	for(var i=0; i<cntDiv; i++) box.appendChild(document.createElement('div'));
	box.childNodes[0].setAttribute('class', 'title');
	box.childNodes[1].setAttribute('class', 'pen');
	for(var i=2; i<cntDiv; i++) box.childNodes[i].setAttribute('class', 'valBox');
	for(var i=0; i<(isIZT?4:8); i++) {
		var tmp=box.cloneNode(true);
		tmp.childNodes[1].onmousedown=function(e) {editRec(this.parentNode)};
		cBox.appendChild(tmp);
		cBox.childNodes[i].setAttribute('id', 'rec'+(isIZT?'IZT':'VZT')+i.toString());
		cBox.childNodes[i].setAttribute('index', i);
		cBox.childNodes[i].isIZT=isIZT;
	}

	el.appendChild(mBox);
	return el;
}

function createSlider(targetId, minVal, maxVal, step) {
	var o=document.createElement('div');
	o.setAttribute('class', 'sliderRow');
	o.setAttribute('targetId', targetId);
	o.setAttribute('minVal', minVal);
	o.minVal=minVal;
	o.setAttribute('maxVal', maxVal);
	o.maxVal=maxVal;

	var el=document.createElement('div');
	el.setAttribute('mDownX','');
	el.setAttribute('class', 'sliderButton')
	el.onmousedown=function(e) {
		if(checkRule(this.idVal)){
			e=window.event || e;
			this.mDownX=e.clientX-parseFloat('0'+this.style.left);
			document.onmousemove=function(e) {
				e=window.event || e;
				el=e.srcElement || e.target;
				if(el.getAttribute('class')) {
					if(el.getAttribute('class')!=='sliderButton' && el.childNodes.length>0) {
						el=el.childNodes[0];
					}
					if((el) && (el.getAttribute) && el.getAttribute('class')=='sliderButton') {
						var maxVal=el.parentNode.offsetWidth-43+6;
						var left=(Math.min(Math.max(e.clientX-el.mDownX,-6),maxVal-6))
						el.style.left=left.toString()+'px';
						left+=6;
						document.getElementById(el.parentNode.getAttribute('targetId')).value=
								parseInt((left/maxVal)*(el.parentNode.getAttribute('maxVal')-el.parentNode.getAttribute('minVal'))+parseFloat(el.parentNode.getAttribute('minVal')));
					}
				}
			}
		};
		document.onmouseup = function() {
			document.onmousemove=null;
			document.onmouseup=null;
			var e=window.event || event;
			el=e.srcElement;
			if(el.getAttribute('class')) {
				if(el.getAttribute('class')!=='sliderButton' && el.childNodes.length>0) {
					el=el.childNodes[0];
				}
				if(el.getAttribute('class')=='sliderButton') {
					el.mDownX=0;
				}
			}
		};
	}
	el.setAttribute('moveStop','');
	o.setVal=function(val) {
		var maxVal=this.offsetWidth-43+6;
		document.getElementById(this.getAttribute('targetId')).value=val;
		this.childNodes[0].style.left=parseInt(((parseFloat(val)-this.getAttribute('minVal'))/(this.getAttribute('maxVal')-this.getAttribute('minVal')))*maxVal).toString()+'px';
	}

	o.appendChild(el);
	return o;
}

function editRec(oSrc) {
	var form=document.createElement('div'), vals;
	form.setAttribute('class', 'recEdit');

	var tmp=document.createElement('div');
	tmp.setAttribute('class', 'title');
	tmp.innerHTML=oSrc.getElementsByTagName('div')[0].innerHTML;
	form.appendChild(tmp);
//alert(oSrc.id)
	var block=document.createElement('div');
	block.setAttribute('class', 'recEditBlock');

	var tmp=document.createElement('div');
	tmp.setAttribute('class', 'recEditObj');
	block.appendChild(tmp);
	var tmp=document.createElement('h3');
	tmp.innerHTML=words['allowed'];
	block.childNodes[0].appendChild(tmp);
	var tmp=document.createElement('input');
	tmp.setAttribute('type', 'checkbox');
	tmp.checked=true;
	block.childNodes[0].appendChild(tmp);
	if(oSrc.getAttribute('class')=='recD') vals=oSrc.isIZT?["",50,40]:["",(values.H10510==2?1:12),0,2,200];
	else vals=oSrc.values;
	if (!(vals)) return; // not readed

	if (oSrc.isIZT) {
		tmp=createSetupEl('', options[tempIZT].caption, tempIZT, vals[1]);
		tmp.setAttribute('class', 'recEditObj');
		block.appendChild(tmp);
		tmp=createSetupEl('', options[tempIZT].caption, tempIZT, vals[2]);
		tmp.setAttribute('class', 'recEditObj');
		block.appendChild(tmp);
		form.appendChild(block);
	}else{
		form.setAttribute('actType','0');
		values['edit1']='2';
		tmp=createSetupEl('', options[pwrType].caption, pwrType, vals[1]);
		tmp.setAttribute('class', 'recEditObj');
		block.appendChild(tmp);
		tmp=createSetupEl('', options[modeType].caption, modeType, vals[2]);
		tmp.setAttribute('class', 'recEditObj');
		if(values.C10509==1){
			tmp.onChange=function(){
				var M2ZRec;
				switch (Number(this.value)){
					case 4:
						M2ZRec=2;
						break;
					case 1: case 3:
						M2ZRec=3;
						break;
					case 0:
						M2ZRec=0;
						break;
					default: // 2,5,6,7
						M2ZRec=1;
						break;
				}
				options.Power.testRW();
				options.Power.onshow(M2ZRec,Number(this.previousSibling.value));
	//			this.previousSibling.setValue(options.Power.onshow(M2ZRec,Number(this.previousSibling.value)));

	/*			if(options.Power.onshow(M2ZRec,Number(this.previousSibling.value))){
					options.Power.testRW();
				}else{
					this.previousSibling.setValue(0);
				}
	*/
			}
		}
		block.appendChild(tmp);
		tmp.onChange();

		tmp=createSetupEl('', options['Zone'].caption, 'Zone', vals[3]);
		tmp.setAttribute('class', 'recEditObj');
		block.appendChild(tmp);
		tmp=createSetupEl('', options[tempType].caption, tempType, vals[4]);
		tmp.setAttribute('class', 'recEditObj');
		block.appendChild(tmp);

		form.appendChild(block);
	}
	var tmp=document.createElement('h3');
	tmp.innerHTML=words['activeFrom'];
	form.appendChild(tmp);

	var tmp=document.createElement('div');
	tmp.setAttribute('class', 'titleR');
	tmp.innerHTML=words['hours'];
	form.appendChild(tmp);
	var slH=createSlider('bigHours', 0, 23, 1);
	slH.style.width='80%';
	slH.style.marginLeft='10%';
	form.appendChild(slH);
	var tmp=document.createElement('input');
	tmp.setAttribute('type', 'text');
	tmp.setAttribute('id', 'bigHours');
	tmp.setAttribute('size', '2');
	tmp.value='0';
	form.appendChild(tmp);
	var tmp=document.createElement('input');
	tmp.setAttribute('type', 'text');
	tmp.setAttribute('id', 'bigMins');
	tmp.setAttribute('size', '2');
	tmp.value='0';
	form.appendChild(tmp);
	var tmp=document.createElement('div');
	tmp.setAttribute('class', 'titleR');
	tmp.innerHTML=words['minutes'];
	form.appendChild(tmp);
	var slM=createSlider('bigMins', 0, 59, 1);
	slM.style.width='80%';
	slM.style.marginLeft='10%';
	form.appendChild(slM);

//   form.appendChild(tmp);


	var tmp=document.createElement('div');
	tmp.setAttribute('type', 'button');
	tmp.setAttribute('id', 'cmdSave');
	tmp.setAttribute('class', 'button');
	tmp.appendChild(document.createTextNode(words['save']));
	tmp.isIZT=oSrc.isIZT;
	tmp.onmouseup=function() {
		var checked=true, finded=false, tChecked=false;
		var form=this.parentNode;
		var inputs=form.getElementsByTagName('input');
		var myTime=formatTime(inputs[1].value+':'+inputs[2].value);
		for(var i=0; i<(this.isIZT?4:8) && checked && !finded; i++) {
			var o=document.getElementById('rec'+(this.isIZT?'IZT':'VZT')+i.toString());
			if(o.getAttribute('class')=='rec') {
				tChecked=true;
				tTime=o.values[0];
			} else {
				tChecked=false;
				tTime='24:00'
			}
			if(inputs[0].checked && tChecked && tTime==myTime) {
				if(o.getAttribute('id')==form.getAttribute('targetId'))
					finded=true;
				else {
					alert(words['thisTimeExist']);
					checked=false;
				}
			} else if(inputs[0].checked && tChecked && tTime>myTime) {
				finded=true;
			} else if(inputs[0].checked && !tChecked && tTime>myTime) {
				finded=true;
			} else if(!inputs[0].checked && !tChecked && tTime>=myTime) {
				finded=true;
			} else if(i==(this.isIZT?3:7)) {
				finded=true;
			}
		}
		if(checked && finded) {
			i--;
			var iPlace=i;
			if(parseInt(form.getAttribute('targetId').substr(6))<i) i--;
			flyObj[0]=new showFly(0, this.parentNode, document.getElementById('rec'+(this.isIZT?'IZT':'VZT')+i.toString()));

			var sParms='', cnt=0, tmpVal;
			for(var i=0; i<(this.isIZT?4:8); i++) {
				if(i==iPlace & inputs[0].checked) {
					sParms+=(sParms==''?'':'x');
					divs=this.parentNode.childNodes[1].childNodes;
					if(this.isIZT){
						sParms+=divs[1].value+','+divs[2].value+',';
					}else{
			// mode, power,  zone, temp, 'hh:mm'
						sParms+=formatVal(divs[1].value, paramKeys['power'])+','+
									formatVal(divs[2].value, paramKeys['mode'])+','+
									formatVal(divs[3].value, paramKeys['zone'])+','+
									divs[4].value+',';
					}
					sParms+=formatTime(document.getElementById('bigHours').value+':'+document.getElementById('bigMins').value);
					cnt++;
				}
				var o=document.getElementById('rec'+(this.isIZT?'IZT':'VZT')+i.toString());
				if(o.getAttribute('id')!==this.parentNode.getAttribute('targetId')){
					var o=document.getElementById('rec'+(this.isIZT?'IZT':'VZT')+i.toString());
					if(o.getAttribute('class')=='rec') {
						sParms+=(sParms==''?'':'x');
						if (this.isIZT) {
							sParms+=o.values[1]+','+o.values[2]+',';
						}else{
							sParms+=formatVal(o.values[1], paramKeys['power'])+','+
								formatVal(o.values[2], paramKeys['mode'])+','+
								formatVal(o.values[3], paramKeys['zone'])+','+
								o.values[4]+',';
						}
						cnt++;
						sParms+=formatTime(o.values[0]);
					}

				}
			}
			this.parentNode.parentNode.removeChild(this.parentNode);
			send2Unit('dcount=1&days='+activeDay+'&count='+cnt+'&values='+sParms);
//			send2Unit('dcount=1&days='+activeDay+'&type='+this.parentNode.getAttribute('actType')+'&count='+cnt+'&values='+sParms);
		}
	};
	form.appendChild(tmp);

	var tmp=document.createElement('div');
	tmp.setAttribute('type', 'button');
	tmp.setAttribute('id', 'cmdCancel');
	tmp.setAttribute('class', 'button');
	tmp.appendChild(document.createTextNode(words['cancel']));
	tmp.onmousedown=function() {
		document.getElementById('smog').style.visibility="hidden";
		this.parentNode.parentNode.removeChild(this.parentNode);
	};
	form.appendChild(tmp);

	form.setAttribute('targetId',oSrc.getAttribute('id'));
	form.style.opacity='0';
	form.style.filter = 'alpha(opacity=0)';

	document.getElementById('mainBlock').appendChild(form);
	if(values.C10509==1){
		block.childNodes[2].onChange();
	}
	if(oSrc.values[0]){
		slH.setVal(oSrc.values[0].substr(0,oSrc.values[0].indexOf(':')));
		slM.setVal(oSrc.values[0].substr(oSrc.values[0].indexOf(':')+1,2));
	}
	flyObj[0]=new showFly(0, oSrc, form);
}
function formatVal(value, key) {
	if(params[key].type==0)
		return value;
	value=value*params[key].coef;
	return '0000'.substr(0,params[key].length-value.toString().length)+value.toString();
}

function showFly(index, oSrc, oTarget, showSmog) {
	this.target=oTarget;
	this.showSmog=showSmog;
	var lTargetTop=0, lTargetLeft=0;
	var o=oTarget;
	do {
		lTargetTop+=o.offsetTop;
		lTargetLeft+=o.offsetLeft;
		o=o.offsetParent;
	} while(o.tagName!=='BODY')
	var o=document.getElementById('mainBlock');
	do {
		lTargetTop-=o.offsetTop;
		lTargetLeft-=o.offsetLeft;
		o=o.offsetParent;
	} while(o.tagName!=='BODY')
	if(oSrc.offsetHeight==oTarget.offsetHeight && oSrc.offsetWidth==oTarget.offsetWidth) {
		 this.box=oSrc.cloneNode(true);
	}else{
		this.box=document.createElement('div');
		this.box.style.padding="0 0 0 0";
		this.box.style.height=oSrc.offsetHeight.toString()+'px';
		this.box.style.width=oSrc.offsetWidth.toString()+'px';
		this.box.style.background='white';
	}
	this.box.style.margin="0";
	this.box.style.display="block";

	this.box.style.position="absolute";
	var lTop=0, lLeft=0;
	var o=oSrc;
	do {
		lTop+=o.offsetTop;
		lLeft+=o.offsetLeft;
		o=o.offsetParent;
	} while(o.tagName!=='BODY')
	var o=document.getElementById('mainBlock');
	do {
		lTop-=o.offsetTop;
		lLeft-=o.offsetLeft;
		o=o.offsetParent;
	} while(o.tagName!=='BODY')
	this.box.style.top=lTop.toString()+'px';
	this.box.style.left=lLeft.toString()+'px';
	this.box.style.zIndex="5000";

	if(document.getElementById('smog').style.visibility=="visible")
		document.getElementById('smog').style.visibility="hidden";
	else
		document.getElementById('smog').style.visibility="visible";

	this.box.style.visibility="visible";
	document.getElementById('mainBlock').appendChild(this.box);
	this.steps=10
	this.stepY=(lTargetTop-this.box.offsetTop)/this.steps
	this.stepX=(lTargetLeft-this.box.offsetLeft)/this.steps
	this.stepW=(this.target.offsetWidth-this.box.offsetWidth)/this.steps
	this.stepH=(this.target.offsetHeight-this.box.offsetHeight)/this.steps

	this.onTime=function(index) {
		this.steps--;
		if(this.steps<=0) {
			this.box.parentNode.removeChild(this.box);
			this.target.style.visibility="visible";
			this.target.style.opacity='';
			this.target.style.filter = '';

		} else {
			eval("setTimeout('flyObj["+index+"].onTime("+index+")',40);");
			this.box.style.top=(this.box.offsetTop+this.stepY).toString()+'px';
			this.box.style.left=(this.box.offsetLeft+this.stepX).toString()+'px';
			this.box.style.width=(this.box.offsetWidth+this.stepW).toString()+'px';
			this.box.style.height=(this.box.offsetHeight+this.stepH).toString()+'px';
		}
	}
	eval("setTimeout('flyObj["+index+"].onTime("+index+")',40);");
}

function createLegend(opY, parent) {
	var tmp, el=createElement('div', false,document.createTextNode(opY.caption),
					  {style:'clear:left;margin:0 0 0 -42px; width:42px;overflow:hidden;padding:0;'});
	parent.appendChild(el);
	for(var i=0; i<opY.values.length;i++) {
		if((opY.values[i]) && (opY.values[i].rw!=='0' || values.C10509==1)){
			el=document.createElement('div', 'legItem');
			tmp=document.createElement('div');
			tmp.style.backgroundColor=opY.values[i].color;
			el.appendChild(tmp);
			el.appendChild(document.createTextNode(opY.display(i)));
			parent.appendChild(el);
		}
	}
}

function createGraph(opY, stepL, stepT, height) {
	if(opY.graph){
		opY=options[opY.graph];
		opY.graph;
	}
	var countY=0, yVals=new Array(), addUnit=true, key, i, maxVal=0;
	if((opY.unit) && opY.unit.length>2){
		var legendY=document.createElement('div');
		legendY.setAttribute('style',
				'position:absolute;margin-top:-21px;margin-left:20px;font-size:11px;font-weight:bold;');
		legendY.innerHTML=opY.unit;
		addUnit=false;
	}
	switch(opY.type) {
		case 'range':
			i=0;
			for(var val=opY.minVal; val<=opY.maxVal;val+=stepL) {
				yVals[i]=document.createElement('div');
				yVals[i].setAttribute('class', 'graphRow');
				yVals[i].setAttribute('value', val);
				if(i % stepT==0) {
					var tmp=document.createElement('div');
					tmp.setAttribute('class', 'title');
					tmp.innerHTML=val.toFixed((opY.dec)?opY.dec:0)+(addUnit?opY.unit:'&nbsp;');
					yVals[i].appendChild(tmp);
				}
				i++;
			}
			yVals[0].style.height='0';
			countY=yVals.length;

			break;
		case 'rangeEnum':
			i=0;
			var ops=opY.values;
			stepT=1;
			stepL=0;
			for(key in ops){
				if(ops[key].value) maxVal=Math.max(maxVal, ops[key].value)
				stepL++;
			}

			stepL=Math.max(Math.round(stepL/8),1);
			for(key in ops){
				if(i % stepL==0 || ops[key].value==maxVal) {
					yVals[countY]=document.createElement('div');
					yVals[countY].setAttribute('class', 'graphRow');
					yVals[countY].setAttribute('value', Number(key));
//					yVals[countY].setAttribute('value', Number(ops[key].value));
					if(countY % stepT==0  || ops[key].value==maxVal) {
						var tmp=document.createElement('div');
						tmp.setAttribute('class', 'title');
						tmp.innerHTML=ops[key].title+'&nbsp;';
//						tmp.innerHTML=ops[key].value.toFixed((opY.dec)?opY.dec:0)+'&nbsp;';
						yVals[countY].appendChild(tmp);
					}
					countY++;
				}
				i++;
			}

			yVals[0].style.height='0';
			break;
		case 'boxes':
		case 'enum':
			countY=1;
			// colorized
			yVals[0]=document.createElement('div');
			yVals[0].setAttribute('class', 'graphRow');
			var tmp=document.createElement('div');
			tmp.setAttribute('class', 'title');
			tmp.style.marginTop="-3px";
			tmp.appendChild(document.createTextNode(opY.caption));
			yVals[0].appendChild(tmp);
			break;
		default:
			alert('Unknown value for the chart generation '+opY.type);
			break;
	}
	el=document.createElement('div');
	el.setAttribute('class', 'graph');
	el.setAttribute('opY','');
	el.opY=opY;
	el.grType=opY.type;
	if(!addUnit) el.appendChild(legendY);
	for(var i=countY-1; i>=0;i--) {
		el.appendChild(yVals[i]);
	}
	return el;
}
function saveValues(pkey, pvalue, add) {
	var parms='', key, keyW, keys, keysW, value;
	if((pkey) && !(add)) {
		if((params[pkey]) && params[pkey].type==0){
			var parms=pkey+'='+escape(pvalue);
//			var parms=pkey+'='+pvalue;
		}else{
			parms+=getUrlPar(pkey, pvalue);
		}
	} else {
		var par,parms='';
		var oBoxs=document.getElementById('content').childNodes;
		for(var j=0; j<oBoxs.length; j++) {
			par='';
			if(oBoxs[j].getAttribute('idVal')) {
			// && values[oBoxs[j].getAttribute('idVal')]) {
				key=oBoxs[j].getAttribute('idVal');
				if(oBoxs[j].getAttribute('idValW'))
					keyW=oBoxs[j].getAttribute('idValW');
				else
					keyW=key;

				if(key.match(',')){
					keys=key.split(',');
					keysW=keyW.split(',');

					for(var i=0;i<keysW.length;i++){
						par='';
//						key=keys[i];
						keyW=keysW[i];
						value=oBoxs[j].values[keys[i]];
						if(!(params[keyW])){
//							alert('Undefined parameter '+key);
							par=getUrlPar(keyW, value);
							if(par) parms+=(parms==''?'':'&')+par;
						}else{
							if(params[keyW].type==0){
			//					parms+=(parms==''?'':'&')+key+'=';
			//					parms+=oBoxs[j].value;
							}else{
								par=getUrlPar(keyW, value);
								if(par) parms+=(parms==''?'':'&')+par;
							}
						}
					}
				}else{
					if(!(params[key])){
//						alert('Undefined parameter '+key);
						value=null;
						if(oBoxs[j].saveVal)
							value=oBoxs[j].saveVal(oBoxs[j].value);
						else if(oBoxs[j].value || typeof(oBoxs[j].value)=='number' || typeof(oBoxs[j].value)=='string')
							value=oBoxs[j].value;

						if(value!==null){
							par=getUrlPar(key, value);
							if(par) parms+=(parms==''?'':'&')+par;
						}
					}else{
						if(params[key].type==0){
		//					parms+=(parms==''?'':'&')+key+'=';
		//					parms+=oBoxs[j].value;
						}else{
							value=null;
							if(oBoxs[j].saveVal)
								value=oBoxs[j].saveVal(oBoxs[j].value);
							else if(oBoxs[j].value || typeof(oBoxs[j].value)=='number' || typeof(oBoxs[j].value)=='string')
								value=oBoxs[j].value;

							if(value!==null){
								par=getUrlPar(key, value);
								if(par) parms+=(parms==''?'':'&')+par;
							}
						}
					}
				}
			}
		}
		if((document.getElementById('content').confirmId))
			parms+='&'+getUrlPar(document.getElementById('content').confirmId, 1);
		if(pkey)
			parms+='&'+getUrlPar(pkey, pvalue);
	}
//	alert(parms)
	if(parms){
		send2Unit(parms);
	}
	showOK();
	document.getElementById('content').setAttribute('dataLoaded', '0');
}
function formatTime(cTime) {
	var tmp=cTime.split(':');
	return (tmp[0].length==1?'0':'')+tmp[0]+':'+(tmp[1].length==1?'0':'')+tmp[1];
}


function createSetupEl(idVal, caption, idOpt, value, onPage) {
	var oSet=document.createElement('div');
	var forDialog=(idVal=='');
	oSet.setAttribute('value','');
	oSet.value=value;
	oSet.setAttribute('idVal', idVal);
	oSet.idVal=idVal;
	oSet.setAttribute('idOption',idOpt);

	oSet.setAttribute('enabled','');
	oSet.enabled=true;
	oSet.setAttribute('setEnabled','');
	oSet.setAttribute('setValue','');
	oSet.setAttribute('changeValue','');
	oSet.setAttribute('onChange','');
	oSet.onChange=function() {

	}
	if(options[idOpt].type=='enum' || ((forDialog || onPage) && options[idOpt].type=='boxes')) {
		oSet.setAttribute('class', 'boxLongBig');
		oSet.setValue=function(value, refresh) {
			this.value=value;
			var cubes= this.getElementsByTagName('div')[2].getElementsByTagName('div');
			for(var i=0; i<cubes.length; i++) cubes[i].setAttribute('class', (cubes[i].idVal==value?'iconSel':'iconNoSel'));
			this.getElementsByTagName('div')[1].getElementsByTagName('span')[0].innerHTML=options[this.getAttribute('idOption')].display(this.value);
			this.onChange();
		};
		oSet.changeValue=function(direction) {
			if(checkRule(this.idVal))
				this.setValue(options[this.getAttribute('idOption')].getPrevNextVal(this.value, direction));
		};
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
			this.getElementsByTagName('span')[0].color=(enabled?'':'#ccc');
		}
	}else if(options[idOpt].type=='dateTime') {
		oSet.setAttribute('class', 'boxLongBig');
		oSet.values=new Array();
		oSet.idVal=oSet.idVal.split(",");
		oSet.display=function(){
//			var keys=this.getAttribute('idVal').split(',');
			var keys=this.idVal;
			if(keys.length>4 && !isNaN(this.values[keys[4]]))
				this.childNodes[1].innerHTML=this.values[keys[2]]+'.'+(this.values[keys[1]]+0)+'.'+this.values[keys[0]]+' '+
				(values[keys[3]]<10?'0':'')+this.values[keys[3]]+':'+(values[keys[4]]<10?'0':'')+this.values[keys[4]];
		}
		oSet.setValue=function(key, value, refresh) {
			this.values[key]=value;
			this.display();
		}
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
//			this.getElementsByTagName('span')[0].color=(enabled?'':'#ccc');
		}
		oSet.type='input';
	}else if(options[idOpt].type=='filterChange') {
		oSet.setAttribute('class', 'boxLongBig');
		oSet.values=new Array();

		oSet.display=function(dt){
			var keys=this.getAttribute('idVal').split(',');
			if(keys.length==2 && !isNaN(this.values[keys[1]])){
				if(!dt){
					dt=new Date();
					var now=new Date();
					dt.setTime((this.values[keys[0]]*65536+(this.values[keys[1]]<0?this.values[keys[1]]+65535:this.values[keys[1]]))*1000);
					dt.setHours(0);
					dt.setMinutes(0);
					dt.setSeconds(0);
				}
//				this.childNodes[1].childNodes[1].innerHTML=dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear();
				this.childNodes[1].innerHTML='<span class="descript">'+words.dtFilterChange+':</span><span>'+dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear()+'</span>';
				if(dt.getTime()<now.getTime()){
					var btn=createElement('div', 'button', document.createTextNode(words.confirmFilter));
					btn.setAttribute('style', 'float:right; margin-top:-5px;');
					btn.onmouseup=function(e){
						if(confirm(words.confFilterQuest+'?')){
							var dt=new Date();
							dt=new Date(dt.getFullYear(), dt.getMonth()+3, dt.getDate());
							var utc=Math.floor(dt.getTime()/1000),
									h=Math.floor(utc/65536), l=utc-(h*65536);
							var keys=this.parentNode.parentNode.getAttribute('idVal').split(',');
							values[keys[0]]=h; values[keys[1]]=l;
							send2Unit(getUrlPar(keys[0], h)+'&'+getUrlPar(keys[1], l));
							this.parentNode.parentNode.display(dt);
						}
					}
					this.childNodes[1].appendChild(btn);
				}
			}
		}
		oSet.setValue=function(key, value, refresh) {
			this.values[key]=value;
			this.display();
		}
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
//			this.getElementsByTagName('span')[0].color=(enabled?'':'#ccc');
		}
		oSet.type='input';
	}else if(options[idOpt].type=='boxes'){
		oSet.setAttribute('class', 'boxBigBig');
		oSet.setValue=function(value, refresh) {
			this.value=value;
			this.onChange();
		};
		oSet.changeValue=function(direction) {
			if(checkRule(this.idVal))
				this.setValue(options[this.getAttribute('idOption')].getPrevNextVal(this.value, direction));
		};
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
			if(this.getElementsByTagName('span').length>0)
			this.getElementsByTagName('span')[0].color=(enabled?'':'#ccc');
		}
	}else if(options[idOpt].type=='range' || options[idOpt].type=='rangeEnum'){
		oSet.setAttribute('class', 'boxLongBig');
		oSet.setValue=function(value, refresh) {
			this.value=value;
			if(refresh) {this.changeValue(0);}
			this.onChange();
		};
		oSet.changeValue=function(direction) {
			if(checkRule(this.idVal)){
				this.value=options[this.getAttribute('idOption')].getPrevNextVal(parseFloat(this.value), direction);
				slider=this.getElementsByTagName('div')[3];
				var maxVal=slider.parentNode.offsetWidth-33;
				slider.style.marginLeft='0';
				slider.style.left=((options[this.getAttribute('idOption')].getValueRatio(parseFloat(this.value))*maxVal)-5).toString()+'px';
				this.getElementsByTagName('span')[0].innerHTML=options[this.getAttribute('idOption')].display(this.value);
			}
		};
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
			this.getElementsByTagName('span')[0].color=(enabled?'':'#ccc');
		}
	} else if(options[idOpt].type=='input') {
		oSet.setAttribute('class', 'boxLongBig');
		oSet.setValue=function(value, refresh) {
			this.value=value;
			this.getElementsByTagName('input')[0].setAttribute('value',value);
			this.onChange();
		};
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
		}
		oSet.type='input';
	}else if(options[idOpt].type=='select') {
		oSet.setAttribute('class', 'boxLongBig');
		oSet.setValue=function(value, refresh) {
			this.value=value;
//			this.getElementsByTagName('select')[0].setAttribute('value',value.toString());
			this.getElementsByTagName('select')[0].value=value;
			this.onChange();
		};
		oSet.setEnabled=function(enabled) {
			this.enabled=enabled;
		}
		oSet.type='input';
	}

	oSet.setAttribute('setValueRatio', '');
	oSet.setValueRatio=function(ratio) {
		this.value=options[this.getAttribute('idOption')].getValueFromRatio(ratio);
		this.getElementsByTagName('span')[0].innerHTML=options[this.getAttribute('idOption')].display(this.value);
	}
	if(options[idOpt].type=='enum' || ((forDialog || onPage) && options[idOpt].type=='boxes')){
		var oStat=document.createElement('div');
		oStat.setAttribute('class', 'statusBoxs')
		for(idVal in options[idOpt].values) {
			if(options[idOpt].values[idVal].rw!=='0'){
				var el=document.createElement('div');
				el.setAttribute('class', (idVal==value?'iconSel':'iconNoSel'));
				el.idVal=idVal;
				oStat.appendChild(el);
			}
		}
		oStat.style.marginLeft='-'+(oStat.childNodes.length*13).toString()+'px';
	}else if(options[idOpt].type=='boxes') {
		oSet.setValue=function(value, el) {
			var boxs= this.getElementsByTagName('div');

			if(this.value!=='' && getElVal(boxs, this.value)) getElVal(boxs, this.value).setAttribute('class', 'buttonBig');
			this.value=value;
			el.setAttribute('class', 'buttonBigSel');
			this.onChange();
		};
		var xVal
		for(idVal in options[idOpt].values) {
			if(options[idOpt].values[idVal].rw!=='0'){
				var el=document.createElement('div');
				xVal=(typeof(options[idOpt].values[idVal].val)=='number'?options[idOpt].values[idVal].val:idVal)
				el.setAttribute('class', (xVal==value?'buttonBigSel':'buttonBig'))
				var tmp=document.createElement('div');
				tmp.setAttribute('class', 'vCenterBox');
				var tmp1=document.createElement('div');
				tmp1.setAttribute('class', 'vCenter');
				tmp1.appendChild(document.createTextNode(options[idOpt].display(idVal)));
				tmp.appendChild(tmp1);
				el.appendChild(tmp);
				el.setAttribute('value', '');
				el.value=xVal;
				el.onmousedown=function() {
					this.parentNode.setValue(this.value, this);
				}
				oSet.appendChild(el);
			}
		}

		switch (oSet.childNodes.length){
			case 2:
				oSet.childNodes[0].style.marginLeft='100px';
				oSet.childNodes[1].style.marginLeft='90px';
				break;
			case 4:
				oSet.childNodes[3].style.marginLeft='262px';
				break;
			case 5:
				oSet.childNodes[3].style.marginLeft='131px';
				break;
		}
	}else if(options[idOpt].type=='range' || options[idOpt].type=='rangeEnum') {
		var oStat=document.createElement('div');
		oStat.setAttribute('class', 'sliderBox');
		var el=document.createElement('div');
		el.setAttribute('mDownX','');
		el.setAttribute('class', 'slider')
		el.onmousedown=function(event) {
			if(checkRule(this.idVal)){
				var e=event || window.event;
				this.mDownX=e.clientX-parseFloat('0'+this.style.left);
				document.onmousemove=function(event) {
					var e=window.event || event;
					el=(e.srcElement?e.srcElement:e.target);
					if(el.getAttribute('class')) {
						if(el.getAttribute('class')!=='slider' && el.childNodes.length>0) {
							el=el.childNodes[0];
						}
						try {
							if(typeof(el)=='object' && el.getAttribute('class') && el.getAttribute('class')=='slider') {
								var maxVal=el.parentNode.offsetWidth+5-43+6;
								var left=(Math.min(Math.max(e.clientX-el.mDownX,-5),maxVal-5))
								el.style.left=left.toString()+'px';
								left+=6;
								try {
									el.parentNode.parentNode.parentNode.setValueRatio((parseInt(el.style.left)+5)/(maxVal));
								} catch(e) {};
							}
						}catch(e){
//							alert(typeof(el));
						}
					}
				}
			};
			document.onmouseup = function(event) {
				document.onmousemove=null;
				document.onmouseup=null;
				var e=window.event || event;
				el=(e.srcElement?e.srcElement:e.target);
				if(el.getAttribute('class')) {
					if(el.getAttribute('class')!=='sliderButton' && el.childNodes.length>0) {
						el=el.childNodes[0];
					}
					if(el.getAttribute('class')=='sliderButton') {
						el.mDownX=0;
					}
				}
			};
		}
		oStat.appendChild(el);
	}
	var tmp=document.createElement('h3');
	tmp.appendChild(document.createTextNode(caption));
	oSet.appendChild(tmp);
	if(options[idOpt].type=='enum' || options[idOpt].type=='range' || options[idOpt].type=='rangeEnum' ||
			((onPage || forDialog) && options[idOpt].type=='boxes')){
		var tmp=document.createElement('div');
		tmp.setAttribute('class','leftBig');
		if(options[idOpt].type=='range' || options[idOpt].type=='rangeEnum'){
			oSet.changeTimer=function(direction, oRow){
				document.valTimer={started:false, id:0, caller:oRow, direction:direction,
					start:function(){
						this.started=true;
						this.id=setInterval('document.valTimer.onTime()',70);
					},
					clear:function(){
						if(this.started) clearInterval(this.id);
						else clearTimeout(this.id);
						document.onmouseup=null;
						this.caller.onmouseout=null;
					},
					onTime:function(){
						this.caller.parentNode.changeValue(this.direction);
					}
				}
				oRow.onmouseout=function(){document.valTimer.clear();};
				document.onmouseup=function(){document.valTimer.clear();};
				document.valTimer.id=setTimeout('document.valTimer.start();',500);
			}
		}
		tmp.onmousedown=function() {this.parentNode.changeValue(-1); if(this.parentNode.changeTimer) this.parentNode.changeTimer(-1, this);};
		oSet.appendChild(tmp);
		var tmp=document.createElement('div');
		tmp.setAttribute('class', 'dispStat');
		tmp.innerHTML='<span>'+options[idOpt].display(value)+'</span>';
		tmp.appendChild(oStat);
		oSet.appendChild(tmp);
		var tmp=document.createElement('div');
		tmp.setAttribute('class','rightBig');
		tmp.onmousedown=function() {this.parentNode.changeValue(1); if(this.parentNode.changeTimer) this.parentNode.changeTimer(1, this);};
		oSet.appendChild(tmp);
	}else if(options[idOpt].type=='input') {
		var tmp=document.createElement('input');
		tmp.setAttribute('type', 'text');
		if(params[idVal].length) tmp.setAttribute('maxlength',params[idVal].length);
		tmp.setAttribute('value',oSet.value);
		oSet.value=function() {return this.getElementsByTagName('input')[0].value;};
		oSet.appendChild(tmp);
	}else if(options[idOpt].type=='select') {
		var tmp=document.createElement('select'), i;
		for(i=0; i<options[idOpt].values.length; i++){
			tmp.appendChild(document.createElement('option'));
			tmp.lastChild.value=i;
			tmp.lastChild.appendChild(document.createTextNode(options[idOpt].values[i].title));
			if(options[idOpt].values[i].rw==0) tmp.lastChild.setAttribute("disabled","1");
		}
		tmp.setAttribute('value',oSet.value);
		tmp.onchange=function(){this.parentNode.value=Number(this.value)}
//		oSet.value=function() {return this.getElementsByTagName('select')[0].value;};
		oSet.appendChild(tmp);
	}else if(options[idOpt].type=='dateTime') {
		oSet.getValue=function(){
			var keys=this.idVal;
			return new Date(this.values[keys[0]], this.values[keys[1]]-1, this.values[keys[2]], this.values[keys[3]], this.values[keys[4]]);
		}
		oSet.setDateTime=function(dt){
//			alert(dt)
/*			this.value=dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear()+
				(dt.getHours()<9?' 0':' ')+dt.getHours()+(dt.getMinutes()<9?':0':':')+dt.getMinutes();*/
			var keys=this.getAttribute('idVal').split(',');
			this.values[keys[0]]=dt.getFullYear();
			this.values[keys[1]]=dt.getMonth()+1;
			this.values[keys[2]]=dt.getDate();
			this.values[keys[3]]=dt.getHours();
			this.values[keys[4]]=dt.getMinutes();
			this.display();
		}
		oSet.onclick=function(){
			this.calendar=new calendar(this);
		}


		var tmp=document.createElement('span');
		tmp.setAttribute('class', 'info');
		oSet.appendChild(tmp);
		keys=idVal;
		//idVal.split(',');
		for(var i=0;i<keys.length;i++) oSet.setValue(keys[i], values[keys[i]]);

/*		tmp.onchange=function(){
			var err=false, dt=false, arrAll=this.value.replace(/[^0123456789.: ]/g,".").split(" "),
				arr=arrAll[0].split(".")
			if(arr.length<2)
				err=true;
			else{
				var now=new Date();
				if(arr.length<3){
						var dt=new Date(now.getFullYear()+'/'+(Number(arr[1]))+'/'+arr[0]);
				}else{
					arr[2]=Number(arr[2]);
					if(arr[2]=='' || isNaN(arr[2]))
						arr[2]=now.getFullYear();
					else if((arr[2]>0) && (arr[2]<100))
						arr[2]=2000+arr[2];
					else if((arr[2]>2099))
						arr[2]=now.getFullYear();
					else if((arr[2]<1000))
						arr[2]=now.getFullYear();
					var dt=new Date(arr[2]+'/'+(Number(arr[1]))+'/'+arr[0]);
				}
			}
			if(dt && !isNaN(dt)){
				if(arrAll.length==2){
					arr=arrAll[1].split(":");
					if(arr && arr.length>0){
						dt.setHours(Number(arr[0]));
						if(arr.length>1) dt.setMinutes(Number(arr[1]));
						else dt.setMinutes(0);
					}else{
						dt.setHours(now.getHours());
						dt.setMinutes(now.getMinutes());
					}
				}else{
					dt.setHours(now.getHours());
					dt.setMinutes(now.getMinutes());
				}
			}
			if(dt && !isNaN(dt)){
				this.value=dt.getDate()+'.'+(dt.getMonth()+1)+'.'+dt.getFullYear()+
					(dt.getHours()<9?' 0':' ')+dt.getHours()+(dt.getMinutes()<9?':0':':')+dt.getMinutes();
				var keys=this.parentNode.getAttribute('idVal').split(',');
				this.parentNode.values[keys[0]]=dt.getFullYear();
				this.parentNode.values[keys[1]]=dt.getMonth();
				this.parentNode.values[keys[2]]=dt.getDate();
				this.parentNode.values[keys[3]]=dt.getHours();
				this.parentNode.values[keys[4]]=dt.getMinutes();
			}else err=true;
			if(err){
				alert(words['badInput']);
				return false;
			}
			return true;
		}
*/
	}else if(options[idOpt].type=='filterChange') {
		var tmp=createElement('div','fullArea', createElement('span', 'descript'));
		tmp.appendChild(createElement('span', 'value'))
		oSet.appendChild(tmp);
	}
	return oSet;
}
function getElVal(els, value) {
	for(i=0; i<els.length; i++) if(els[i].value && els[i].value==value) return els[i];
}

function setupOption(idVal, caption, idOpt, value, srcEl) {
	var oSet=createSetupEl(idVal, caption, idOpt, value)
/// next is buttons save & cancel
	oSet.appendChild(document.createElement('br'));
	var o=document.createElement('div');
	o.setAttribute('class', 'wrap');
	oSet.appendChild(o);

	var o=document.createElement('div');
	o.setAttribute('type', 'button');
	o.setAttribute('id', 'cmdSave');
	o.setAttribute('class', 'buttonLeft');
	o.appendChild(document.createTextNode(words['save']));
	o.setAttribute('targetEl','');
	o.targetEl=srcEl;
	o.onmouseup=function() {
		saved=false;
		flyDown=true;
		if(this.targetEl.onChange){
			try {
				this.targetEl.onChange(this.parentNode.value());
			}catch(e){
				this.targetEl.onChange(this.parentNode.value);
			}
		}
		if(!saved){
			if(typeof(this.parentNode.idVal)=='object' && (this.parentNode.idVal.length)){
				var parms='';
				for(var i=0; i<this.parentNode.idVal.length; i++)
					parms+=(parms==''?'':'&')+getUrlPar(this.parentNode.idVal[i], this.parentNode.values[this.parentNode.idVal[i]]);
				document.getElementById('content').dateChanged=true;
				send2Unit(parms);
				showOK();
				document.getElementById('content').setAttribute('dataLoaded', '0');
			}else{
				try {
					saveValues(this.parentNode.getAttribute('idVal'), this.parentNode.value());
				}catch(e){
					saveValues(this.parentNode.getAttribute('idVal'), this.parentNode.value);
				}
			}
		}
		if(flyDown)
			flyObj[0]=new showFly(0, this.parentNode, this.targetEl);
		else
			document.getElementById('smog').style.visibility="visible";
		oSet.parentNode.removeChild(oSet);
	};
	oSet.appendChild(o);

	var o=document.createElement('div');
	o.setAttribute('type', 'button');
	o.setAttribute('id', 'cmdSave');
	o.setAttribute('class', 'buttonLeft');
	o.appendChild(document.createTextNode(words['cancel']));
	o.onmousedown=function() {document.getElementById('smog').style.visibility="hidden";oSet.parentNode.removeChild(oSet);};
	oSet.appendChild(o);

	oSet.style.zIndex="5000";
//	document.getElementById('smog').style.visibility="visible";
	document.getElementById('mainBlock').appendChild(oSet);
	oSet.style.visibility="hidden";
	flyObj[0]=new showFly(0, srcEl, oSet);
	if(options[idOpt].type=='range' || options[idOpt].type=='rangeEnum') oSet.changeValue(0);
}

// x************ end Visualisation
function checkRule(affect, silent) {
	var result=true;
	for(var i in rules) {
		if(rules[i].affect==affect && values[rules[i].check]==rules.ruleVal) {
//			if(!(silent)) messages[rules[i].msgId].display();
			result=rules[i].result;
		}
	}
	return result;
}

var status=0,
	words=new Array(), options=new Array(), values=new Array(), params=new Array(), langs=new Array(),
	body={menus:new Array, content:new Array()}, activePage='', activeContent='', activeDay=0,
	messages=new Array(), rules=new Array(), locHash='.', timeZones=[], alarmKeys=new Array(), warnKeys=new Array(),
	activeAlarm=false, activeWarning=false, activeUpdate=false, tmp,
	pwrType=false, modeType='Mode', comm={source:'',target:'',demo:false,debug:false}, user={auth:'', loged:false};
var flyObj=new Array();

function locationFix() {
	if(location.hash!==locHash) {
		locHash=location.hash.substr(1);
		var tmp=locHash.split('.');
		if(!(tmp[1])) tmp[1]='';
		if(activePage!==tmp[0] || activeContent!==tmp[1]) {
			activePage=tmp[0];
			activeContent=tmp[1];
			showPage();
		} else {
			var sel ;
			if(document.getElementById('smog').style.visibility=="hidden"){
				if(document.selection && document.selection.empty){
					document.selection.empty() ;
				} else if(window.getSelection) {
					sel=window.getSelection();
					if(sel && sel.removeAllRanges)
					sel.removeAllRanges() ;
				}
			}
		}
	}
	setTimeout('locationFix()',400);
}

function dataRefresh() {
	if(activeUpdate){
		var v=getFileContent('verpckg.txt');
		if((v) && Number(v) && Number(v)>2000000 && v!==activeUpdate)
			location.reload(true);
	}else{
		rq('getSetting');
	}
 setTimeout('dataRefresh()',10000);
}

function send2Unit(pars, dataFile, debug){
	var elBody=document.getElementsByTagName('body')[0];
	if(!(dataFile) && body.menus[activePage] && body.menus[activePage].menus[activeContent].content.target)
		dataFile=body.menus[activePage].menus[activeContent].content.target;
	if(dataFile){
		target=server+dataFile;
	}else target=server+urlDataSet;
	if(pars.indexOf('auth')<0) pars='auth='+user.auth+'&'+pars;
if((debug)) alert(target+' <-- '+pars);

	if(webMode){
		if(!(elBody.imgSet)){
			elBody.imgSet=document.createElement('img');
			elBody.imgSet.style.visibility="hidden";
			elBody.appendChild(elBody.imgSet);
		}
		elBody.imgSet.src=target+'?'+pars;
	}else{
		sendSync(target, pars, null);
	}
	 setTimeout("rq('getSetting')",200);

}

function onLoadBody(e){
	var loc=window.location.toString(), isAuth=false, docVals;
	if(loc.match('lng=')){
		testLng=loc.substr(loc.lastIndexOf('lng=')+4,1);
		document.getElementById('srvcLink').setAttribute('href','srvcmain.htm?lng='+testLng);
		values[idLNG]=testLng;
	}else{
		if(demoMode)
			values[idLNG]='0';
		else{
			values[idLNG]=sendSync(urlLogin).documentElement.getAttribute('lng');
//			if (values[idLNG]===null) values[idLNG]='0';
		}
		testLng=false;
	}
	if(loc.match('sid')){
		docVals=sendSync(urlDataRead,'auth='+loc.substr(loc.lastIndexOf('sid=')+4,5)+'&'+randStr(2));
		if((docVals) && (docVals.documentElement) &&
				(docVals.documentElement.getElementsByTagName('RD5').length>0)) isAuth=true;
	}
	if(isAuth){
		user.loged=true;
		user.auth=loc.substr(loc.lastIndexOf('sid=')+4,5);
		var els=document.getElementsByTagName('a');
		for(var i=0; i<els.length; i++){
			if(els[i].getAttribute('href')=='index.htm')
				els[i].setAttribute('href','index.htm?sid='+user.auth);
			else	if(els[i].getAttribute('href')=='srvcmain.htm')
				els[i].setAttribute('href','srvcmain.htm?sid='+user.auth);
		}
	}else{
		loadLang();
		showLogin();
		return;
	}
	if(docVals && docVals.documentElement){
		loadRD5Values(docVals.documentElement.getElementsByTagName('RD5')[0], true);
	}


/*	var loc=window.location.toString(),
		docVals=sendSync(urlDataRead,randStr(2));
	if(loc.match('lng=')){
		testLng=loc.substr(loc.lastIndexOf('lng=')+4,1);
		document.getElementById('srvcLink').setAttribute('href','srvcmain.htm?lng='+testLng);
	}
*/
	var doc=sendSync('user/params.xml',randStr(2));
	if((doc) && (doc.documentElement))
		loadParams(doc.documentElement.getElementsByTagName('params')[0]);
	loadLang();

	var doc=sendSync('lang/userCtrl.xml',randStr(2))
	if(doc && doc.documentElement){
		loadLayout(doc.documentElement.getElementsByTagName('layout')[0]);
//		var doc=sendSync('lang/params_.xml',randStr(2))
	}
	var doc=sendSync('lang/tz.xml',randStr(2));
	if((doc) && (doc.documentElement))
		loadTZ(doc.documentElement);

	if(docVals && docVals.documentElement)
		loadRD5Values(docVals.documentElement.getElementsByTagName('RD5')[0]);


	if(webMode) var doc=sendSync('config/texts.php','auth='+user.auth+'&'+randStr(2));
	else var doc=sendSync('config/texts.xml','auth='+user.auth+'&'+randStr(2))
	if(doc && doc.documentElement){
		loadTexts(doc.documentElement.getElementsByTagName('texts')[0]);
	}
//	var doc=sendSync('lang/user_'+values[idLNG]+'.xml',randStr(2))
//	if(doc && doc.documentElement){
//		loadLayout(doc.documentElement.getElementsByTagName('layout')[0]);
		showPage();
//	}
//	dataFile='lang/content_'+values[idLNG]+'.xml?'+randStr(2)+'.xml';
	setTimeout('dataRefresh()',7000);
	document.getElementById('alarmIco').onmousedown=function(e){
		activeContent='';
		activePage='AL';
		showPage();
	}

}

function testWhen(valKey){
	if(!(valKey)) return true;
	if(valKey.match(/\(/) || valKey.match('values')) {
		try{
			eval('var ret=('+valKey+');');
		}catch(e){
//			alert(valKey)
		}
		return ret;
	}else if(valKey.match('=')) {
		value=valKey.substr(valKey.indexOf('=')+1);
		valKey=valKey.substr(0,valKey.indexOf('='));
	}else value=1;
	return values[paramKeys[valKey]]==value;
}

function	sendTempRequired(val){
	switch(values.H11017){
		case 0:
			send2Unit(getUrlPar('H11017', 2)+'&'+getUrlPar('H11021', val));
			break;
		case 1:
			send2Unit(getUrlPar('H11010', val)+'&'+getUrlPar('H11021', val));
			break;
		default:
			send2Unit(getUrlPar('H11021', val));
			break;
	}
}
function mode2Z(){
	switch (values.H10715){
		case 4:
			return 2;
		case 1: case 3:
			return 3;
		case 0:
			return 0;
		default: // 2,5,6,7
			return 1;
	}
}
//<!-- RpEnd -->