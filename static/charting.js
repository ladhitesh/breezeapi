optionSeries = []
chart = null;

$(document).ready(function() {

	const chartOptions = { height:450, 
			layout: { textColor: 'black', background: { type: 'solid', color: 'white' } }, 
			timeScale: { rightOffset: 10,visible: true,timeVisible: true,secondsVisible: false,shiftVisibleRangeOnNewBar: true,
									 ticksVisible: true },
			rightPriceScale: { visible: true }, leftPriceScale: { visible: true, ticksVisible: true }, crosshair: {mode : LightweightCharts.CrosshairMode.Normal}
			};
	chart = LightweightCharts.createChart(document.getElementById('chart'), chartOptions);
	const myTickMarkFormatter = (time, tickMarkType, locale) => {
		return moment.tz(time,"Asia/Kolkata").format("LTS");
	};
	//chart.timeScale().applyOptions({tickMarkFormatter : myTickMarkFormatter}) 

	optionSeries = chart.addSeries(LightweightCharts.CandlestickSeries,
		{ priceScaleId: 'right', upColor: '#26a69a', downColor: '#ef5350', 
		 borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' 
		});
	optionSeries.setData([]);

	refDataSeries = chart.addSeries(LightweightCharts.CandlestickSeries,
		{ priceScaleId: 'left', upColor: '#bbbbbf', downColor: '#585859', 
		 borderVisible: false, wickUpColor: '#bbbbbf', wickDownColor: '#585859' 
		});
	refDataSeries.setData([]);
	refDataSeries.priceScale().applyOptions({ scaleMargins: {top: 0.1, bottom: 0.5,} });

	//Volume Data
	optionSeries.priceScale().applyOptions({ scaleMargins: { top: 0.1,bottom: 0.2,},
		priceFormat: {type: 'price', precision: 2, minMove: 0.05, formatter: price => parseFloat(price).toFixed(2),}
	});
	volumeSeries = chart.addSeries(LightweightCharts.HistogramSeries,{ color: '#C5C5C5',priceFormat: {type: 'volume',}, priceScaleId: ''});
	volumeSeries.priceScale().applyOptions({ scaleMargins: {top: 0.8, bottom: 0,} });

	//Legend
	optionsStockName = "Option Chart";
	indexName = "BANKNIFTY";
	const container = document.getElementById('chart');
	const [firstRowStockOHLCVDiv, secondRowStockOHLCVDiv  ] = drawChartLegend(container)

	var optionPriceFormatted = '';
	var futurePriceFormatted = '';

	chart.subscribeCrosshairMove(param => {
		if (param.time) {
			const optionPrice = param.seriesData.get(optionSeries);
			if (optionPrice != undefined && optionPrice.open !=0){
				var O = optionPrice.open
				var H = optionPrice.high
				var L = optionPrice.low
				var C = optionPrice.close
				optionPriceFormatted = `O<div style="display:inline-block;width:60px;">${O}</div> `
				optionPriceFormatted = optionPriceFormatted + `H<div style="display:inline-block;width:60px;">${H}</div> `
				optionPriceFormatted = optionPriceFormatted + `L<div style="display:inline-block;width:60px;">${L}</div> `
				optionPriceFormatted = optionPriceFormatted + `C<div style="display:inline-block;width:60px;">${C}</div>` 
			}
				

			const futurePrice = param.seriesData.get(refDataSeries);
			if(futurePrice != undefined && futurePrice.open !=0){
				var O = futurePrice.open
				var H = futurePrice.high
				var L = futurePrice.low
				var C = futurePrice.close
				futurePriceFormatted = `O<div style="display:inline-block;width:60px;">${O}</div> `
				futurePriceFormatted = futurePriceFormatted + `H<div style="display:inline-block;width:60px;">${H}</div> `
				futurePriceFormatted = futurePriceFormatted + `L<div style="display:inline-block;width:60px;">${L}</div> `
				futurePriceFormatted = futurePriceFormatted + `C<div style="display:inline-block;width:60px;">${C}</div>` 
			}
		}
		firstRowStockOHLCVDiv.innerHTML = optionPriceFormatted;
		secondRowStockOHLCVDiv.innerHTML = futurePriceFormatted;
	});
	
	/*
	if(isApiConnected){

		//update expiry and token details for non index stocks
		$("#refChart option[product='futures']").each(function() {
			updateRefChartSelectOptions($(this))
				.then(result => {
					if($(this).is(':selected')){
						//load ref chart once token and expiry is updated
						currentRefChartToken = $(this).attr("token")
						console.log("loading default selected ref chart: " + currentRefChartToken)	
						loadReferenceChart(true);
						chart.timeScale().fitContent();
					}});
		});

		//load ref chart id selected chart is not index or futures
		if($("#refChart :selected").attr("product")!= "futures"){
			currentRefChartToken = $("#refChart :selected").attr("token")
			console.log("loading default selected ref chart: " + currentRefChartToken)	
			loadReferenceChart(true);
			chart.timeScale().fitContent();
		}
		
	}
	*/
	intervalLookup = {}
	intervalLookup["1MIN"] = "1minute"
	intervalLookup["5MIN"] = "5minute"
	intervalLookup["30MIN"] = "30minute"
	intervalRevLookup = {}
	intervalRevLookup["1minute"] = "1MIN"
	intervalRevLookup["5minute"] = "5MIN"
	intervalRevLookup["30minute"] = "30MIN"

});

//will be set on document ready
currentRefChartToken = null;
isrefChartNonIndexStockDataUpdated = false

function runWhenDataproviderConnected(){
	//update expiry and token details for non index stocks
	if (!isrefChartNonIndexStockDataUpdated){
		$("#refChart option[product='future']").each(function() {
			updateRefChartSelectOptions($(this))
				.then(result => {
					if($(this).is(':selected')){
						//load ref chart once token and expiry is updated
						currentRefChartToken = $(this).attr("token")
						console.log("loading default selected ref chart: " + currentRefChartToken)	
						loadReferenceChart(true);
						chart.timeScale().fitContent();
					}});
		});
	}
	isrefChartNonIndexStockDataUpdated = true
	//load ref chart id selected chart is not index or futures
	if($("#refChart :selected").attr("product")!= "future"){
		currentRefChartToken = $("#refChart :selected").attr("token")
		console.log("loading default selected ref chart: " + currentRefChartToken)	
		loadReferenceChart(true);
		chart.timeScale().fitContent();
	}
}

function updateRefChartSelectOptions(option){
	searchStr = "FUTURE " + option.val()
	//searchStr = "FUT " + option.value
	//console.log(searchStr)
	strict="True"
	return fetchDPStocks(strict,searchStr).then(result => {
			let token = result[0]["token"]
			//console.log(token)
			let expiry = result[0]["expiry"]
			//let expiry1806Format = moment(expiry,"DD-MMM-YYYY").format("YYYY-MM-DD")+"T19:30:00.000Z"
			//option.setAttribute("token",token)
			//option.setAttribute("expiry",expiry)
			//option.text = (option.text + " " + expiry)
			option.attr("token",token)
			option.attr("expiry",expiry)
			option.text(option.text() + " " + expiry)
		});
}



function refChartTickListener(ltpDataDict){
	try{
		//console.log(ltpData)
		//check token of feed data with current selected token and then process data
		if(typeof ltpDataDict == 'string')
			ltpDataDict = JSON.parse(ltpDataDict);
		
		let selectedRefChartOption = $("#refChart :selected")[0];
		let token = selectedRefChartOption.getAttribute("token")
		//ltpDataDict = JSON.parse(ltpData);
	
		ltpDatatoken = ltpDataDict['token']
		if(ltpDatatoken !== token){
			//unsubscribe unwanted redchart tick data
			//socket.off('unsubscribeQuotes', ltpDatatoken, '1second')
			//ignore this data
			return;
		}
		//update tick ltp on chart legend
		
		selectorStr = '[id="'+token+'-price"]'
		ltpElemArr = $(selectorStr);
		for(elementIndex in ltpElemArr){
			ltpElemArr[elementIndex].innerHTML = ltpDataDict["close"]
		}
	
		//realtime tick update in chart
		if (interval != "30minute" && interval != "30MIN"){
			divisor = 60
			if(interval == "5minute" || interval == "5MIN" ){
				divisor = divisor * 5
			}
			tickDataDict = updateTimeNVolumeInTickData(ltpDataDict,false)
			//console.log(tickDataDict["time"])
			var currentTime = Number(tickDataDict["time"])
			var closestMinuteTime = Math.floor(Number(tickDataDict["time"])/divisor)*divisor
			var differenceInTime = currentTime - closestMinuteTime
	
			if(indexTickOpen == 0)
				indexTickOpen = tickDataDict["open"]
			if(differenceInTime == 2){
				indexTickOpen = tickDataDict["open"]
				indexTickLow = tickDataDict["low"]
				indexTickHigh = tickDataDict["high"]
				indexTickClose = tickDataDict["close"]
			}
			indexTickLow = Math.min(indexTickLow,Number(tickDataDict["low"]) )
			indexTickHigh = Math.max(indexTickHigh,Number(tickDataDict["high"]) )
			indexTickClose = tickDataDict["close"]
			tickDataDict["open"] = indexTickOpen
			tickDataDict["low"] = indexTickLow
			tickDataDict["high"] = indexTickHigh
			tickDataDict["close"] = indexTickClose
			//console.log(closestMinuteTime +":"+differenceInTime)
			tickDataDict["time"] = closestMinuteTime
	
			if (differenceInTime > 5 && differenceInTime < (divisor - 5)){
					//console.log(closestMinuteTime +":"+differenceInTime)
					refDataSeries.update(tickDataDict);
			}
		}
		//console.log(tickDataDict["time"])
	}catch(e){console.log("error in refChartTickListener");console.log(e)}
	
}

indexTickOpen = 0
indexTickLow = 99999 
indexTickHigh = 0
indexTickClose = 0
function resetRefChartTickOpeningLevels(){
	indexTickOpen = 0
	indexTickLow = 99999 
	indexTickHigh = 0
	indexTickClose = 0	
}

function drawChartLegend(chartContainer){
	const legend = document.createElement('div');
	legend.style = 'position:relative; left: 10px; z-index: 1; font-size: 14px; font-family: sans-serif; line-height: 18px; font-weight: 300;';
	chartContainer.insertBefore(legend, chartContainer.firstChild);

	const firstRow = document.createElement('div');
	firstRow.style.textAlign = 'left';
	
	let firstRowStockNameDivHtml = `<div id='optionsChartStockName' style='color:black;text-align:left;display:inline-block;font-weight:bold;font-size:12px;background-color:#fcfcde;width:230px;padding-left:3px'>${optionsStockName}</div>`
	const firstRowStockNameDiv = new DOMParser().parseFromString(firstRowStockNameDivHtml, 'text/html').querySelector("div");

	let firstRowStockLtpDivHtml = "<div id='' style='text-align:left;display:inline-block;color:blue;width:67px;margin-left:10px'></div>"
	const firstRowStockLtpDiv = new DOMParser().parseFromString(firstRowStockLtpDivHtml, 'text/html').querySelector("div");

	let firstRowStockOHLCVDivHtml = "<div style='color:black;text-align:left;display:inline;font-size:12px'></div>"
	const firstRowStockOHLCVDiv = new DOMParser().parseFromString(firstRowStockOHLCVDivHtml, 'text/html').querySelector("div");

	firstRow.appendChild(firstRowStockNameDiv)
	firstRow.appendChild(firstRowStockLtpDiv)
	firstRow.appendChild(firstRowStockOHLCVDiv)
	
	legend.appendChild(firstRow);

	const secondRow = document.createElement('div');
	secondRow.style.textAlign = 'left';
	
	let secondRowStockNameSelect = getRefChartStockSelectHTMLElement()
	let secondRowStockLtpDivHtml = "<div id='NIFTY BANK-price' style='text-align:left;display:inline-block;color:blue;width:70px;margin-left:10px'></div>"
	const secondRowStockLtpDiv = new DOMParser().parseFromString(secondRowStockLtpDivHtml, 'text/html').querySelector("div");

	let secondRowStockOHLCVDivHtml = "<div style='color:black;text-align:left;display:inline;font-size:12px'></div>"
	const secondRowStockOHLCVDiv = new DOMParser().parseFromString(secondRowStockOHLCVDivHtml, 'text/html').querySelector("div");
	
	//secondRow.appendChild(secondRowStockNameDiv)
	secondRow.appendChild(secondRowStockNameSelect)
	secondRow.appendChild(secondRowStockLtpDiv)
	secondRow.appendChild(secondRowStockOHLCVDiv)
	
	legend.appendChild(secondRow);
	return [firstRowStockOHLCVDiv,secondRowStockOHLCVDiv];
}

function getRefChartStockSelectHTMLElement(){
	let secondRowStockNameSelectHtml = "<select id='refChart' style='color:black;background-color:#fcfcde;text-align:left;display:inline-block;width:230px;font-size:12px;padding:0px;margin:0px;border:0px;font-weight:bold' onchange='updateReferenceChart();'>"
	const secondRowStockNameSelect = new DOMParser().parseFromString(secondRowStockNameSelectHtml, 'text/html').querySelector("select");

	let secondRowOption1Html = "<option value='CNXBAN' token='NIFTY BANK' exchangeCode='NSE' product='' expiry='' selected>BANKNIFTY</option>";
	const secondRowOption1 = new DOMParser().parseFromString(secondRowOption1Html, 'text/html').querySelector("option");

	let secondRowOption2Html = "<option value='CNXBAN' exchangeCode='NFO' product='future' >BANKNIFTY FUT</option>";
	const secondRowOption2 = new DOMParser().parseFromString(secondRowOption2Html, 'text/html').querySelector("option");

	let secondRowOption3Html = "<option value='NIFTY' token='NIFTY 50' exchangeCode='NSE' product='equity' expiry=''>NIFTY 50</option>";
	const secondRowOption3 = new DOMParser().parseFromString(secondRowOption3Html, 'text/html').querySelector("option");
	
	let secondRowOption4Html = "<option value='NIFTY' exchangeCode='NFO' product='future'>NIFTY FUT</option>";
	const secondRowOption4 = new DOMParser().parseFromString(secondRowOption4Html, 'text/html').querySelector("option");
	
	secondRowStockNameSelect.appendChild(secondRowOption1)
	secondRowStockNameSelect.appendChild(secondRowOption2)
	secondRowStockNameSelect.appendChild(secondRowOption3)
	secondRowStockNameSelect.appendChild(secondRowOption4)
	return secondRowStockNameSelect
}

var toggleRefChartVisible = true
var interval = "5minute"

function resetInterval(event, newInterval){
	clearOptionsChartData();
	clearRefChartData();
	interval = newInterval
	loadReferenceChart(true);
	loadOptionsChart(currentHiddenDataDivId, optionsChartVisible)
}

fromDateStr = moment().format("YYYY-MM-DD")+"T09:15:00.000Z"
toDateStr = moment().format("YYYY-MM-DD")+"T19:30:00.000Z"

function setChartRange(days){
	if(days > 15 && interval != "1day"){
		alert("Select daily interval to display data more than 15 days")
		return
	}

	fromDateStr = moment().subtract(days,'d').format("YYYY-MM-DD")+"T09:15:00.000Z"
	loadReferenceChart(true);
	loadOptionsChart(currentHiddenDataDivId, optionsChartVisible)
}

function updateReferenceChart(){
	let selectedRefChartOption = $("#refChart :selected");
	let selectedRefChartText = selectedRefChartOption.text();
	let selectedRefChartStockCode = selectedRefChartOption.val();
	console.log("updating reference chart-"+selectedRefChartStockCode+":"+selectedRefChartText)
	//console.log($("#refChart")[0])
	let token = selectedRefChartOption[0].getAttribute("token")
	//update id for tick data
	let ltpDivObj = $("#refChart")[0].nextSibling
	ltpDivObj.id = token + "-price"
	resetRefChartTickOpeningLevels();
	loadReferenceChart(true);
}

prevRefChartToken = "";

//var refChartVisible = false
function loadReferenceChart(refChartVisible){
	try{
		let selectedRefChartOption = $("#refChart :selected")[0];
		let stockCode = selectedRefChartOption.value
		let exchangeCode = selectedRefChartOption.getAttribute("exchangeCode")
		let token = selectedRefChartOption.getAttribute("token")
		let product = selectedRefChartOption.getAttribute("product")
		let expiry = selectedRefChartOption.getAttribute("expiry")
		//console.log("expiry: " + expiry)
		let expiryFormatted = ""
		if(expiry != null && expiry != ""){
			expiryFormattedForOHLCVSubs = moment(expiry,"YYYY-MM-DD").format("DD-MMM-YYYY")
			expiryFormatted = expiry+"T00:00:00.000Z"
		}
		
		if (refChartVisible!= undefined && !refChartVisible){
			//socket.emit('unsubscribeQuotes', token, interval)
			unsubscribeDirectOHLCV(token,interval);
			//socket.off(token+"-1second")
			refDataSeries.setData([]);
			return;
		}
		
		if(prevRefChartToken != "" && token != prevRefChartToken ){
			//socket.emit('unsubscribeQuotes', prevRefChartToken, interval)
			//socket.off(prevRefChartToken+"-1second")
			unsubscribeDirectOHLCV(prevRefChartToken,interval);
		}
		
		hDataArr = []
		fetchHistoricalData(stockCode,exchangeCode,product,expiryFormatted,"","")
			.then(result => {
				hDataArr = result;
				//console.log(hDataArr)
				refDataSeries.setData(hDataArr);
				//chart.timeScale().fitContent();

				//socket.emit('subscribeQuotes', token, interval)
				subscribeDirectOHLCV(token,intervalRevLookup[interval],{'token':token,'stockCode':stockCode,'expiry':expiryFormattedForOHLCVSubs,'strike':"",'right':""},"")
				//socket.emit('subscribeQuotes', token, '1second')
				subscribeDirectOHLCV(token,"1SEC",{'token':token,'stockCode':stockCode,'expiry':expiryFormattedForOHLCVSubs,'strike':"",'right':""},"")
				//socket.on(token+'-'+interval, function (ohlcvData){
				//	refChartFeedDataListener(ohlcvData)
				//});
				//socket.on(token+'-1second', function (ohlcvData) {
				//	refChartTickListener(ohlcvData)
				//});
				prevRefChartToken = token
			});
		
		//socket.emit('unsubscribeQuotes', "NIFTY BANK", "1second")

	}
	catch(error){
		console.log("error:" + error)
	}
	return "bank nifty "+interval+"data loaded"

}

var previousOptionsDataToken = null

function clearOptionsChartData(){
	//unsubscribe first so old token data do not override new token data
	if(previousOptionsDataToken != null){
		//socket.emit('unsubscribeQuotes', previousOptionsDataToken, interval);
		unsubscribeDirectOHLCV(previousOptionsDataToken,interval);
	}
	previousOptionsDataToken = null
	optionSeries.setData([]);
	volumeSeries.setData([]);
	//chart.timeScale().fitContent();
}

function clearRefChartData(){
	let selectedRefChartOption = $("#refChart :selected")[0];
	let token = selectedRefChartOption.getAttribute("token")
	//socket.emit('unsubscribeQuotes', token, interval);
	unsubscribeDirectOHLCV(token,interval);
	refDataSeries.setData([]);
	//chart.timeScale().fitContent();
}

var currentHiddenDataDivId = null;
var optionsChartVisible = true;
function loadOptionsData(hiddenDataDivId){
	newHiddenDataDivId = hiddenDataDivId
	if(newHiddenDataDivId == currentHiddenDataDivId){
		//clear options chart data
		optionSeries.setData([]);
		volumeSeries.setData([]);
		currentHiddenDataDivId = null;
		optionsChartVisible = false;
		return;
	}
	optionsChartVisible = true;
	loadOptionsChart(hiddenDataDivId, optionsChartVisible)
}

function loadOptionsChart(hiddenDataDivId, optionsChartVisible){
		try{
			
			newHiddenDataDivId = hiddenDataDivId
			hiddenDivObj = $("#"+newHiddenDataDivId)[0]
			if(hiddenDivObj == null)
				return;
			
			if(newHiddenDataDivId == currentHiddenDataDivId && optionsChartVisible){
				//clear options chart data
				optionSeries.setData([]);
				volumeSeries.setData([]);
			}
				
			currentHiddenDataDivId = newHiddenDataDivId
			//console.log(hiddenDivObj)

			stockCode = hiddenDivObj.dataset.stockcode
			exchangeCode = hiddenDivObj.dataset.exchangecode
			fnotype = hiddenDivObj.dataset.fnotype
			product = hiddenDivObj.dataset.product
			expiry = hiddenDivObj.dataset.expiry
			expiryFormattedForOHLCVSubs = moment(expiry,"YYYY-MM-DD").format("DD-MMM-YYYY")
			expiryFormatted = expiry+"T00:00:00.000Z"
			strike = hiddenDivObj.dataset.strike
			right = hiddenDivObj.dataset.right
			rightLong = right
			if(right == "CE"){rightLong="Call"}else if (right=="PE"){rightLong="Put"}
			
			token = hiddenDivObj.dataset.token
			
			//set stock name in chart legend
			$("#optionsChartStockName")[0].innerHTML = hiddenDivObj.dataset.code +"&nbsp;&nbsp;&nbsp;&nbsp;"
			$("#optionsChartStockName")[0].nextSibling.id=token+"-price"

			hDataArr = []
			fetchHistoricalData(stockCode,exchangeCode,product,expiryFormatted,strike,rightLong)
				.then(result => {

					hDataArr=result			
					var vDataArr = JSON.parse(JSON.stringify(hDataArr))
					const upColor='#82e3d9' 
					const downColor='#f6a3a2' 
					vDataArr.forEach(function(data){
						if(Number(data["open"]) < Number(data["close"])){
							data["color"] = upColor
						}else{
							data["color"] = downColor
						}
					});
					//console.log(hDataArr)
					
					optionSeries.setData(hDataArr);
					volumeSeries.setData(vDataArr);
					//chart.priceScale().fitContent();
					//chart.timeScale().fitContent();
					
					//unsubscribe first so old token data do not override new token data
					if(previousOptionsDataToken != null){
						//socket.emit('unsubscribeQuotes', previousOptionsDataToken, interval);
						//socket.off(previousOptionsDataToken+'-1second', optionChartTickListener);
						//let ltpElemArr = $('#'+token+'-price');
						//if(ltpElemArr.length < 2)
						//	unsubscribeDirectOHLCV(previousOptionsDataToken)
						unsubscribeDirectOHLCV(previousOptionsDataToken,interval)
						optionTickOpen = 0
						optionTickLow = 99999 
						optionTickHigh = 0
						optionTickClose = 0
					}
					
					//socket.emit('subscribeQuotes', this.token, interval);
					subscribeDirectOHLCV(token,intervalRevLookup[interval],{'token':token,'stockCode':stockCode,'expiry':expiryFormattedForOHLCVSubs,'strike':strike,'right':right},"")
					//socket.on(this.token+'-'+interval, function (ohlcvData){
					//	optionChartFeedDataListener(ohlcvData)
					//});
					resetOptionsChartTickOpeningLevels();
					//socket.on(this.token+'-1second', optionChartTickListener);
					subscribeDirectOHLCV(this.token,"1SEC",{'token':this.token,'stockCode':stockCode,'expiry':expiryFormattedForOHLCVSubs,'strike':strike,'right':right},"")
					
					previousOptionsDataToken = this.token;
				});

		}
		catch(error){
			console.log("error:" + error)
		}

}

function updateTimeNVolumeInTickData(data,addColorToData){
	if(typeof data == 'string')
		data = JSON.parse(data);
	//console.log(data)	
	datetimeStr = data["datetime"]
	if(addColorToData){
		var upColor='#82e3d9'
		var downColor='#f6a3a2'
		if(Number(data["open"]) < Number(data["close"])){
			data["color"] = upColor
		}else{
			data["color"] = downColor
		}
	}
	var toUTC = Math.floor((moment.tz(datetimeStr, "YYYY-MM-DD HH:mm:ss","Asia/Kolkata"))
								  .add(5,'h')
								  .add(30,'m')
								  .valueOf()/1000)
	data["datetime"] = toUTC
	//tickData = JSON.stringify(data,undefined, 4)
	//tickData = tickData.replaceAll('datetime','time')
	//tickData = tickData.replaceAll('volume','value')
	data["time"] = data["datetime"]
	data["value"] = data["volume"]
	return data
}

function refChartFeedDataListener(data){
	try{
		if(typeof data == 'string')
			data = JSON.parse(data);
		//check token of feed data with current selected token and then process data
		let selectedRefChartOption = $("#refChart :selected")[0];
		let selectedToken = selectedRefChartOption.getAttribute("token")
		let dataInterval = data['interval']
				if (!dataInterval.includes("minute")){
			dataInterval = intervalLookup[data['interval']]
		}
		if(selectedToken != data['token'] || interval != dataInterval){
			console.log("refchart :ignoring token("+selectedToken+"): "+data["token"]+" as selected interval '"+interval+"' is different than data interval '"+dataInterval+"'")
			//unsubscribe minute feed data
			return;
		}
		tickData = updateTimeNVolumeInTickData(data,false)
		//refDataSeries.update(JSON.parse(tickData));
		refDataSeries.update(tickData);
	}catch(e){console.log("error in refChartFeedDataListener");console.log(e)}
}

function optionChartFeedDataListener(data){
	try{
		if(!optionsChartVisible)
			return;
		if(typeof data == 'string')
			data = JSON.parse(data);
		//console.log("option minute"+data['interval']+" listener token:"+data['token'])
		let dataInterval = data['interval']
		if (!dataInterval.includes("minute")){
			dataInterval = intervalLookup[data['interval']]
		}
		if(data['token'] != previousOptionsDataToken || interval != dataInterval ){
			console.log("datachart:ignoring token("+previousOptionsDataToken+"): "+data["token"]+" as selected interval "+interval+" is different than data interval "+dataInterval)
			//send unscubscribe message for appropriate interval
			return;
		}
		var vtickData = JSON.parse(JSON.stringify(data))
		//var vtickData = data
		var tickData = updateTimeNVolumeInTickData(data,false)
		vtickData = updateTimeNVolumeInTickData(vtickData,true)

		//optionSeries.update(JSON.parse(tickData));
		//volumeSeries.update(JSON.parse(vtickData));
		//console.log(vtickData)
		optionSeries.update(tickData);
		volumeSeries.update(vtickData);
		//chart.timeScale().fitContent();
	}catch(e){console.log("error in optionChartFeedDataListener");console.log(e)}

}

optionTickOpen = 0
optionTickLow = 99999 
optionTickHigh = 0
optionTickClose = 0

function resetOptionsChartTickOpeningLevels(){
	optionTickOpen = 0
	optionTickLow = 99999 
	optionTickHigh = 0
	optionTickClose = 0
}

function optionChartTickListener(data){
	if(!optionsChartVisible)
		return;
	if(typeof data == 'string')
		data = JSON.parse(data);
	if(data['token'] != previousOptionsDataToken)
		return;
	//var tickDataStr = updateTimeNVolumeInTickData(data,false)
	var tickDataDict = updateTimeNVolumeInTickData(data,false)
	if (interval != "30minute"){
		divisor = 60
		if(interval == "5minute"){
			divisor = divisor * 5
		}
		//tickDataDict = JSON.parse(tickDataStr)
		//console.log(tickDataDict["time"])
		var currentTime = Number(tickDataDict["time"])
		var closestMinuteTime = Math.floor(Number(tickDataDict["time"])/divisor)*divisor
		var differenceInTime = currentTime - closestMinuteTime

		if(optionTickOpen == 0)
			optionTickOpen = tickDataDict["open"]
		if(differenceInTime == 2){
			optionTickOpen = tickDataDict["open"]
			optionTickLow = tickDataDict["low"]
			optionTickHigh = tickDataDict["high"]
			optionTickClose = tickDataDict["close"]
		}
		optionTickLow = Math.min(optionTickLow,Number(tickDataDict["low"]) )
		optionTickHigh = Math.max(optionTickHigh,Number(tickDataDict["high"]) )
		optionTickClose = tickDataDict["close"]
		tickDataDict["open"] = optionTickOpen
		tickDataDict["low"] = optionTickLow
		tickDataDict["high"] = optionTickHigh
		tickDataDict["close"] = optionTickClose
		//console.log(closestMinuteTime +":"+differenceInTime)
		tickDataDict["time"] = closestMinuteTime
		
		if (differenceInTime > 5 && differenceInTime < (divisor - 5)){
			try{
				//console.log(closestMinuteTime +":"+differenceInTime)
				optionSeries.update(tickDataDict);
			}catch(e){console.log(e)}
		}
	}
	//chart.timeScale().fitContent();
}


