optionSeries = []
chart = null;

$(document).ready(function() {

	const chartOptions = { height:450, 
								 layout: { textColor: 'black', 
											 background: { type: 'solid', color: 'white' } 
											}, 
								 timeScale: { 
									 rightOffset: 10,
									 visible: true,
									 timeVisible: true,
									 secondsVisible: true,
									 shiftVisibleRangeOnNewBar: true,
									 ticksVisible: false
								 },
								 rightPriceScale: { visible: true },
								 leftPriceScale: { visible: true, ticksVisible: true },
								 crosshair: {mode : 0}
								};
	chart = LightweightCharts.createChart(document.getElementById('chart'), chartOptions);
	
	optionSeries = chart.addCandlestickSeries(
		{ priceScaleId: 'right', upColor: '#26a69a', downColor: '#ef5350', 
		 borderVisible: false, wickUpColor: '#26a69a', wickDownColor: '#ef5350' 
		});

	optionSeries.setData([]);

	futuresSeries = chart.addCandlestickSeries(
		{ priceScaleId: 'left', upColor: '#bbbbbf', downColor: '#585859', 
		 borderVisible: false, wickUpColor: '#bbbbbf', wickDownColor: '#585859' 
		});

	futuresSeries.setData([]);
	
	futuresSeries.priceScale().applyOptions({
		scaleMargins: {
			top: 0.1, // highest point of the series will be 80% away from the top
			bottom: 0.5,
		},
	});

	//Volume Data
	optionSeries.priceScale().applyOptions({
		scaleMargins: {
			top: 0.1,
			bottom: 0.2,
		},
		priceFormat: {
			type: 'price', precision: 2, minMove: 0.05, formatter: price => parseFloat(price).toFixed(2),
		}
	});
	volumeSeries = chart.addHistogramSeries({
		color: '#C5C5C5',
		priceFormat: {
			type: 'volume',
		},
		priceScaleId: '', // set as an overlay by setting a blank priceScaleId
		
	});
	volumeSeries.priceScale().applyOptions({
		scaleMargins: {
			top: 0.8, // highest point of the series will be 80% away from the top
			bottom: 0,
		},
	});


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
				

			const futurePrice = param.seriesData.get(futuresSeries);
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
	
	if(isApiConnected){
		//loadReferenceChart(true);
		chart.timeScale().fitContent();
		socket.emit('subscribeQuotes', 'NIFTY BANK', '1second')
		//decouple this refChartTickListener function
		socket.on('NIFTY BANK-1second', refChartTickListener);
	}
	

});


function refChartTickListener(ltpData){
	//console.log(ltpData)
	let selectedRefChartOption = $("#refChart :selected")[0];
	let token = selectedRefChartOption.getAttribute("token")
	ltpDataDict = JSON.parse(ltpData);

	ltpDatatoken = ltpDataDict['token']
	if(ltpDatatoken !== token){
		//unsubscribe unwanted redchart tick data
		socket.emit('unsubscribeQuotes', ltpDatatoken, '1second')
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
	if (interval != "30minute"){
		divisor = 60
		if(interval == "5minute"){
			divisor = divisor * 5
		}
		tickDataStr = updateTimeNVolumeInTickData(ltpData,false)
		tickDataDict = JSON.parse(tickDataStr)
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
			try{
				//console.log(closestMinuteTime +":"+differenceInTime)
				futuresSeries.update(tickDataDict);
			}catch(e){console.log(e)}
		}
	}
	//console.log(tickDataDict["time"])

	
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
	const firstRowStockNameDiv = document.createElement('div');
	firstRowStockNameDiv.id = 'optionsChartStockName'
	firstRowStockNameDiv.innerText = optionsStockName;
	firstRowStockNameDiv.style.color = 'black';
	firstRowStockNameDiv.style.textAlign = 'left';
	firstRowStockNameDiv.style.display = 'inline-block';
	firstRowStockNameDiv.style.fontWeight = "bold"
	firstRowStockNameDiv.style.fontSize = '12px'
	firstRowStockNameDiv.style.backgroundColor="#fcfcde"
	firstRowStockNameDiv.style.width = "230px"
	firstRowStockNameDiv.style.paddingLeft = "3px"
	const firstRowStockLtpDiv = document.createElement('div');
	firstRowStockLtpDiv.id = 'set-in-chart-populate-function';
	firstRowStockLtpDiv.style.textAlign = 'left';
	firstRowStockLtpDiv.style.display = 'inline-block';
	firstRowStockLtpDiv.style.color = 'blue';
	firstRowStockLtpDiv.style.width = '70px';
	firstRowStockLtpDiv.style.marginLeft = '10px';
	const firstRowStockOHLCVDiv = document.createElement('div');
	firstRowStockOHLCVDiv.style.color = 'black';
	firstRowStockOHLCVDiv.style.textAlign = 'left';
	firstRowStockOHLCVDiv.style.display = 'inline';
	firstRowStockOHLCVDiv.style.fontSize = '12px'

	firstRow.appendChild(firstRowStockNameDiv)
	firstRow.appendChild(firstRowStockLtpDiv)
	firstRow.appendChild(firstRowStockOHLCVDiv)
	
	legend.appendChild(firstRow);

	const secondRow = document.createElement('div');
	secondRow.style.textAlign = 'left';
	
	
	const secondRowStockNameSelect = document.createElement('select');
	secondRowStockNameSelect.id="refChart"
	secondRowStockNameSelect.style.color = 'black';
	secondRowStockNameSelect.style.backgroundColor="#fcfcde"
	secondRowStockNameSelect.style.textAlign = 'left';
	secondRowStockNameSelect.style.display = 'inline-block';
	secondRowStockNameSelect.style.width = '230px';
	secondRowStockNameSelect.style.fontSize = '12px'
	secondRowStockNameSelect.style.padding = "0px"
	secondRowStockNameSelect.style.margin = "0px"
	secondRowStockNameSelect.style.border = "0px"
	secondRowStockNameSelect.style.fontWeight = "bold"
	secondRowStockNameSelect.setAttribute('onchange','updateReferenceChart();');
	const secondRowOption1 = document.createElement('option');
	secondRowOption1.text = "BANKNIFTY"
	secondRowOption1.value = "CNXBAN"
	secondRowOption1.setAttribute("token","NIFTY BANK")
	secondRowOption1.setAttribute("exchangeCode","NSE")
	secondRowOption1.setAttribute("product","")
	secondRowOption1.setAttribute("expiry","")
	secondRowOption1.selected = "selected"
	const secondRowOption2 = document.createElement('option');
	secondRowOption2.text = "BANKNIFTY FUT"
	secondRowOption2.value = "CNXBAN"
	secondRowOption2.setAttribute("exchangeCode","NFO")
	secondRowOption2.setAttribute("product","futures")
	secondRowStockNameSelect.appendChild(secondRowOption1)
	secondRowStockNameSelect.appendChild(secondRowOption2)
	
	const secondRowStockLtpDiv = document.createElement('div');
	secondRowStockLtpDiv.id = 'NIFTY BANK-price';
	secondRowStockLtpDiv.style.textAlign = 'left';
	secondRowStockLtpDiv.style.display = 'inline-block';
	secondRowStockLtpDiv.style.color = 'blue';
	secondRowStockLtpDiv.style.width = '70px';
	secondRowStockLtpDiv.style.marginLeft = '10px';
	const secondRowStockOHLCVDiv = document.createElement('div');
	secondRowStockOHLCVDiv.style.color = 'black';
	secondRowStockOHLCVDiv.style.textAlign = 'left';
	secondRowStockOHLCVDiv.style.display = 'inline';
	secondRowStockOHLCVDiv.style.fontSize = '12px'
	
	//secondRow.appendChild(secondRowStockNameDiv)
	secondRow.appendChild(secondRowStockNameSelect)
	secondRow.appendChild(secondRowStockLtpDiv)
	secondRow.appendChild(secondRowStockOHLCVDiv)
	
	legend.appendChild(secondRow);
	return [firstRowStockOHLCVDiv,secondRowStockOHLCVDiv];
}

var toggleRefChartVisible = true
var interval = "5minute"

async function resetInterval(event, newInterval){
	clearOptionsChartData();
	clearRefChartData();
	interval = newInterval
	await loadReferenceChart(true).then(result => {console.log(result)});
	await loadOptionsData(currentHiddenDataDivId)
}

fromDateStr = moment().format("YYYY-MM-DD")+"T09:15:00.000Z"
toDateStr = moment().format("YYYY-MM-DD")+"T19:30:00.000Z"

async function setChartRange(days){
	fromDateStr = moment().subtract(days,'d').format("YYYY-MM-DD")+"T09:15:00.000Z"
	await loadReferenceChart(true).then(result => {console.log(result)});
	await loadOptionsData(currentHiddenDataDivId)
}

async function updateReferenceChart(){
	
	let selectedRefChartOption = $("#refChart :selected");
	let selectedRefChartText = selectedRefChartOption.text();
	let selectedRefChartStockCode = selectedRefChartOption.val();
	console.log("updating reference chart-"+selectedRefChartStockCode+":"+selectedRefChartText)
	//console.log($("#refChart")[0])
	//update token
	let product = selectedRefChartOption[0].getAttribute("product")
	let searchStr = ""
	if(product == "futures"){
		searchStr = "FUT "
		searchStr = searchStr + selectedRefChartStockCode
		let fnoStocksUrl = baseServerUrl + '/getFnOStocks?' + new URLSearchParams({'searchStr': searchStr})
		await callApi(fnoStocksUrl).then(result => {fnOJsonArr=result});
		//console.log(fnOJsonArr[0])
		let token = fnOJsonArr[0]["token"]
		let expiry = fnOJsonArr[0]["expiry"]
		expiry1806Format = moment(expiry,"DD-MMM-YYYY").format("YYYY-MM-DD")+"T19:30:00.000Z"
		selectedRefChartOption[0].setAttribute("token",token)
		selectedRefChartOption[0].setAttribute("expiry",expiry1806Format)
		if(!selectedRefChartOption.text().includes(expiry)){
			selectedRefChartOption.text(selectedRefChartOption.text() + " " + expiry)
		}
		//update id for tick data
		let ltpDivObj = $("#refChart")[0].nextSibling
		ltpDivObj.id = token + "-price"
	}
	resetRefChartTickOpeningLevels();
	loadReferenceChart(true);

}

async function getHistoricalData(stockCode,exchangeCode,product,expiry,strike,right){

	//interval = "5minute"
	//console.log(exchangeCode)

	var hDataParams = new URLSearchParams({
		'fromDate' : fromDateStr,
		'toDate' : toDateStr,
		'stockCode' : stockCode,
		'interval' : interval,
		'strike' : strike,
		'expiry' : expiry,
		'right' : right,
		'product' : product,
		'exchangeCode' : exchangeCode
	})
	var hDataResultJsonArr = null
	var hDataUrl = baseServerUrl + '/getHistoricalData?' + hDataParams
	//console.log(hDataUrl)
	await callApi(hDataUrl).then(result => {hDataResultJsonArr=result});
	errorStatus = hDataResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		return;
	}
	hDataArr = hDataResultJsonArr["Success"]
	return hDataArr;
}

prevRefChartToken = "";

//var refChartVisible = false
async function loadReferenceChart(refChartVisible){
	try{
		
		let selectedRefChartOption = $("#refChart :selected")[0];
		let stockCode = selectedRefChartOption.value
		let exchangeCode = selectedRefChartOption.getAttribute("exchangeCode")
		let token = selectedRefChartOption.getAttribute("token")
		let product = selectedRefChartOption.getAttribute("product")
		let expiry = selectedRefChartOption.getAttribute("expiry")
		
		if (refChartVisible!= undefined && !refChartVisible){
			socket.emit('unsubscribeQuotes', token, interval)
			socket.emit('unsubscribeQuotes', token, "1second")
			futuresSeries.setData([]);
			return;
		}
		
		if(prevRefChartToken != "" && token != prevRefChartToken ){
			socket.emit('unsubscribeQuotes', prevRefChartToken, interval)
			socket.emit('unsubscribeQuotes', prevRefChartToken, "1second")
		}
		
		hDataArr = []
		await getHistoricalData(stockCode,exchangeCode,product,expiry,"","").then(result => {hDataArr=result});
		//console.log(hDataArr)
		futuresSeries.setData(hDataArr);
		//chart.timeScale().fitContent();

		socket.emit('subscribeQuotes', token, interval)
		socket.emit('subscribeQuotes', token, '1second')
		socket.on(token+'-'+interval, function (ohlcvData){
			updateIndexChart(ohlcvData)
		});
		socket.on(token+'-1second', refChartTickListener);
		
		prevRefChartToken = token
		
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
		socket.emit('unsubscribeQuotes', previousOptionsDataToken, interval);
	}
	previousOptionsDataToken = null
	optionSeries.setData([]);
	volumeSeries.setData([]);
	//chart.timeScale().fitContent();
}

function clearRefChartData(){
	let selectedRefChartOption = $("#refChart :selected")[0];
	let token = selectedRefChartOption.getAttribute("token")
	socket.emit('unsubscribeQuotes', token, interval);
	futuresSeries.setData([]);
	//chart.timeScale().fitContent();
}

var currentHiddenDataDivId = null;
async function loadOptionsData(hiddenDataDivId){
		try{
			
			newHiddenDataDivId = hiddenDataDivId
			hiddenDivObj = $("#"+newHiddenDataDivId)[0]
			if(hiddenDivObj == null)
				return;
			
			if(newHiddenDataDivId == currentHiddenDataDivId){
				//clear options chart data
				optionSeries.setData([]);
				volumeSeries.setData([]);
				currentHiddenDataDivId = null;
				return;
			}
				
				
			currentHiddenDataDivId = newHiddenDataDivId
			//console.log(hiddenDivObj)

			stockCode = hiddenDivObj.dataset.stockcode
			exchangeCode = hiddenDivObj.dataset.exchangecode
			fnotype = hiddenDivObj.dataset.fnotype
			product = hiddenDivObj.dataset.product
			expiry = hiddenDivObj.dataset.expiry
			expiry = moment(expiry,"DD-MMM-YYYY").format("YYYY-MM-DD")+"T00:00:00.000Z"
			strike = hiddenDivObj.dataset.strike
			right = hiddenDivObj.dataset.right
			if(right == "CE"){right="Call"}else if (right=="PE"){right="Put"}
			
			if(fnotype == "OPT")
				fnotype = "Options"
			else if(fnotype == "FUT"){
				fnotype = "Futures"
				strike = ""
				right = ""
			}
			
			token = hiddenDivObj.dataset.token
			
			//set stock name in chart legend
			$("#optionsChartStockName")[0].innerHTML = hiddenDivObj.dataset.code +"&nbsp;&nbsp;&nbsp;&nbsp;"
			$("#optionsChartStockName")[0].nextSibling.id=token+"-price"

			hDataArr = []
			await getHistoricalData(stockCode,exchangeCode,product,expiry,strike,right).then(result => {hDataArr=result});
			
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
				socket.emit('unsubscribeQuotes', previousOptionsDataToken, interval);
				socket.off(previousOptionsDataToken+'-1second', updateOptionChartRealTime);
				optionTickOpen = 0
				optionTickLow = 99999 
				optionTickHigh = 0
				optionTickClose = 0
			}
			
			socket.emit('subscribeQuotes', this.token, interval);
			socket.on(this.token+'-'+interval, function (ohlcvData){
				updateOptionChart(ohlcvData)
			});
			socket.on(this.token+'-1second', updateOptionChartRealTime);
			
			//socket.emit('unsubscribeQuotes', "NIFTY BANK", "1second")
			previousOptionsDataToken = token;

		}
		catch(error){
			console.log("error:" + error)
		}

}

function updateTimeNVolumeInTickData(data,addColorToData){
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
	tickData = JSON.stringify(data,undefined, 4)
	tickData = tickData.replaceAll('datetime','time')
	tickData = tickData.replaceAll('volume','value')
	return tickData
}

function updateIndexChart(data){
	tickData = updateTimeNVolumeInTickData(data,false)
	try{
		futuresSeries.update(JSON.parse(tickData));
	}catch(e){console.log(e)}
}

function updateOptionChart(data){
	var vtickData = JSON.parse(JSON.stringify(data))
	var tickData = updateTimeNVolumeInTickData(data,false)
	vtickData = updateTimeNVolumeInTickData(vtickData,true)
	try{
		optionSeries.update(JSON.parse(tickData));
		volumeSeries.update(JSON.parse(vtickData));
	}catch(e){console.log(e)}
	//chart.timeScale().fitContent();
}

optionTickOpen = 0
optionTickLow = 99999 
optionTickHigh = 0
optionTickClose = 0

function updateOptionChartRealTime(data){
	var tickDataStr = updateTimeNVolumeInTickData(data,false)
	if (interval != "30minute"){
		divisor = 60
		if(interval == "5minute"){
			divisor = divisor * 5
		}
		tickDataDict = JSON.parse(tickDataStr)
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


