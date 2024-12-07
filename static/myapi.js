$(document).ready(function() {
	socket = io('ws://127.0.0.1:5000',{
		autoConnect: true,
		transports: ['websocket'],
		extraHeaders: { 'User-Agent': 'node-socketio[client]/socket' },
		upgrade: true,
		rememberUpgrade: true
	});
	socket.on('connect', function() {
        console.log("websocket connected to api server")
   });
	socket.on("connect_error", (err) => {
		try{
			let errorMessage = err
			$('#output')[0].innerHTML = "<span style='color:red'>error connecting websocket to api server: " + err + "</span>"
			console.log(`error connecting websocket to api server: ${errorMessage}`)
			console.log(err)
		}catch(e){console.log(e)}
	});
	socket.on('disconnect', function() {
        console.log("websocket disconnected to api server")
   });
	socket.on('order_notification', orderNotification)
	socket.on('chart_session_key', processChartSessionKey)
	
});

async function callApi(url){
	var resultData
	console.log("calling url:" + url)
	await fetch(url,{method : "GET"})
		.then((res) => { 
								if (res.ok) { return res.json(); }
								throw new Error('Error in fetching api response');
		})
		.then((data) => {
								//console.log("response text:"+JSON.stringify(data,undefined, 4))
								//$('#output')[0].innerHTML = "<pre>"+JSON.stringify(data,undefined, 4)+"</pre>";
								resultData = data
		})
		.catch(error => { console.log(error);throw error });
	return resultData
}

stockTokenCache = {};
//need async here DO NOT REMOVE ASYNC
async function fetchStockToken(stockCode,exchangeCode,product,expiry,strike,right){
	let rightLong = right;
	if(right == "CE"){
		rightLong = "Call"
	}else if(right == "PE"){
		rightLong = "Put"
	}


	cacheKey = stockCode +'-'+ exchangeCode +'-'+ product +'-'+ expiry +'-'+ strike +'-'+ rightLong
	if(stockTokenCache[cacheKey]){
		token = stockTokenCache[cacheKey]
		console.log('token retrieved from cache:'+token)
		return new Promise((resolve, reject) => {
  					setTimeout(() => { resolve(token);}, 10);
				});
	}
	
	let stockTokenParams = new URLSearchParams({
			'stockCode' : stockCode,
			'exchangeCode' : exchangeCode,
			'productType' : product,
			'expiryDate' : expiry,
			'strike' : strike,
			'rightType' : rightLong
		})
	let stockTokenUrl = baseServerUrl + '/getStockToken?'+stockTokenParams
	result = await callApi(stockTokenUrl)
		.then(result => { 
			let token = result["quotesToken"].split("!")[1]; 
			stockTokenCache[cacheKey] = token;
			return token});
	return result;
}

function fetchOpenPositions(){
	var openPositionsUrl = baseServerUrl + '/getOpenPositions'
	return callApi(openPositionsUrl)
		.then(result => {
			return result["Success"];
	});
	
	
	/*
	//  DO NOT DELETE
	//spoof data
	const openPositionsJsonArr = [new Object(), new Object()]
	openPositionsJsonArr[0]["action"]="Buy"
	openPositionsJsonArr[0]["quantity"]="15"
	openPositionsJsonArr[0]["average_price"]="300"
	openPositionsJsonArr[0]["product_type"]="Options"
	openPositionsJsonArr[0]["stock_code"]="CNXBAN"
	openPositionsJsonArr[0]["expiry_date"]="13-Dec-2023"
	openPositionsJsonArr[0]["strike_price"]="45500"
	openPositionsJsonArr[0]["exchange_code"]="NFO"
	openPositionsJsonArr[0]["right"]="Call"
	openPositionsJsonArr[1]["action"]="Buy"
	openPositionsJsonArr[1]["quantity"]="45"
	openPositionsJsonArr[1]["average_price"]="350"
	openPositionsJsonArr[1]["product_type"]="Options"
	openPositionsJsonArr[1]["stock_code"]="CNXBAN"
	openPositionsJsonArr[1]["expiry_date"]="13-Dec-2023"
	openPositionsJsonArr[1]["strike_price"]="44500"
	openPositionsJsonArr[1]["exchange_code"]="NFO"
	openPositionsJsonArr[1]["right"]="Put"

	const promise = new Promise((resolve, reject) => {
	  setTimeout(() => {
	    resolve(openPositionsJsonArr);
	  }, 300);
	});
	return promise*/
	
}

function fetchMargins(){
	let marginUrl = baseServerUrl + '/getMargin'
	//console.log(marginUrl)
	return callApi(marginUrl)
		.then(result => {
			//console.log(result)
			errorStatus = result["Error"]
			if(errorStatus != null && errorStatus != ""){
				if(errorStatus == "Not connected"){
					console.log("API server not connected")
				}
				return null;
			}
			return result["Success"]
		});
}

async function fetchRealisedPnl(fromDateStr, toDateStr){
	let realisedPnlParams = new URLSearchParams({
			'fromDate' : fromDateStr,
			'toDate' : toDateStr
		})
	let realisedPnlUrl = baseServerUrl + '/getRealisedPnL?' + realisedPnlParams
	//console.log(realisedPnlUrl)
	let pnlResultJsonArr;
	await callApi(realisedPnlUrl).then(result => {pnlResultJsonArr=result});
	//console.log(pnlResultJsonArr)
	errorStatus = pnlResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		if(errorStatus == "No Data Found"){
			console.log("No data for realised pnl")
		}
		return null;
	}
	return pnlResultJsonArr["Success"]
}

async function fetchBrokerage(stockCode,exchangeCode,product,strike,expiryDate,action,rightType,price,quantity,stoploss){
	//call api for brokerage
	var brokerageParams = new URLSearchParams({
		'stockCode' : hiddenDivObj.dataset.stockcode,
		'exchangeCode' : hiddenDivObj.dataset.exchangecode,
		'product' : hiddenDivObj.dataset.product, 
		'strike' : hiddenDivObj.dataset.strike,
		'expiryDate' : hiddenDivObj.dataset.expiry,
		'action' : action.toLowerCase(),
		'rightType' : hiddenDivObj.dataset.right,
		'price' : price,
		'quantity' : quantity,
		'stoploss' : stoploss
	})

	let brokerageResultJsonArr = null
	let brokeragePath = '/getBrokerages'
	let brokerageUrl = baseServerUrl + brokeragePath + '?' + brokerageParams
	//console.log(brokerageUrl)
	await callApi(brokerageUrl).then(result => {brokerageResultJsonArr=result});
	errorStatus = brokerageResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		console.log(errorStatus)
		return null;
	}
	return brokerageResultJsonArr["Success"]	
}

function fetchOrderList(orderDate){
	let orderListParams = new URLSearchParams({
		'orderDate' : orderDate
	})
	let orderListUrl = baseServerUrl + '/getOrderList?' + orderListParams
	return callApi(orderListUrl).then(
		result => {
			return result["Success"]
		});
}

function fetchStocks(searchStr){
	let fnoStocksUrl = baseServerUrl + '/getFnOStocks?' + new URLSearchParams({'searchStr': searchStr})
	return callApi(fnoStocksUrl)
		.then(result => {
			return result;
		});
}

function fetchDPStocks(strict,searchStr){
	let dpStocksUrl = baseServerUrl + '/getDPStocks?' + new URLSearchParams({'strict':strict,'searchStr': searchStr})
	return callApi(dpStocksUrl)
		.then(result => {
			return result;
		});
}

async function sendModifyOrder(orderId,exchangeCode,price,quantity,stoploss){

	var modifyOrderParams = new URLSearchParams({
		'orderId' : orderId,
		'exchangeCode' : exchangeCode,
		'price' : price,
		'quantity' : quantity,
		'stoploss' : stoploss
	})	
	var modifyOrderUrl = baseServerUrl + '/modifyOrder?' + modifyOrderParams
	console.log(modifyOrderUrl)
	return await callApi(modifyOrderUrl)
		.then(result => {
			return result;
		});
}

async function sendPlaceOrder(stockcode,exchangeCode,product,strike,expiry,action,right,price,quantity,stoploss,instruIds){

	var newOrderParams = new URLSearchParams({
		'stockCode' : stockcode,
		'exchangeCode' : exchangeCode,
		'product' : product, 
		'strike' : strike,
		'expiryDate' : expiry,
		'action' : action.toLowerCase(),
		'rightType' : right,
		'price' : price,
		'quantity' : quantity,
		'stoploss' : stoploss
	})
	
	for (const [key, value] of Object.entries(instruIds)) {
		newOrderParams.set(key, value);
	}

	var newOrderUrl = baseServerUrl + '/placeOrder?' + newOrderParams
	console.log(newOrderUrl)
	var output = null;
	return await callApi(newOrderUrl)
		.then(result => {
			return result
		});
}

async function sendSquareOffOrder(stockcode,exchangeCode,product,strike,expiry,action,right,price,quantity,stoploss){

	var squareoffOrderParams = new URLSearchParams({
		'stockCode' : stockcode,
		'exchangeCode' : exchangeCode,
		'product' : product, 
		'strike' : strike,
		'expiryDate' : expiry,
		'action' : action.toLowerCase(),
		'rightType' : right,
		'price' : price,
		'quantity' : quantity,
		'stoploss' : stoploss
	})

	var squareoffOrderUrl = baseServerUrl + '/squareoff?' + squareoffOrderParams
	console.log(squareoffOrderUrl)
	return await callApi(squareoffOrderUrl)
		.then(result => {
			return result;
		});
}

function sendCancelOrder(cancelOrderId){
	let cancelOrderParams = new URLSearchParams({
			'orderId' : cancelOrderId
		})		
	let cancelOrderUrl = baseServerUrl + '/cancelOrder?' + cancelOrderParams
	//console.log(cancelOrderUrl)
	return callApi(cancelOrderUrl).then(result => {
		return result;
	});
}
function fetchHistoricalData(stockCode,exchangeCode,product,expiry,strike,right){
	let hDataParams = new URLSearchParams({
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
	let hDataResultJsonArr = null
	let hDataUrl = baseServerUrl + '/getHistoricalData?' + hDataParams
	//console.log(hDataUrl)
	return callApi(hDataUrl)
		.then(result => {
			hDataResultJsonArr=result
			errorStatus = hDataResultJsonArr["Error"]
			if(errorStatus != null && errorStatus != ""){
				return [];
			}
			hDataArr = hDataResultJsonArr["Success"]
			return hDataArr;
		});
}


async function fetchMarginCalculation(stockCode,exchangeCode,product,strike,expiryDate,action,rightType,price,quantity,includeOpenPositions){
	//call api for brokerage
	var marginCalculatorParams = new URLSearchParams({
		'stockCode' : hiddenDivObj.dataset.stockcode,
		'exchangeCode' : hiddenDivObj.dataset.exchangecode,
		'product' : hiddenDivObj.dataset.product, 
		'strike' : hiddenDivObj.dataset.strike,
		'expiryDate' : hiddenDivObj.dataset.expiry,
		'action' : action.toLowerCase(),
		'rightType' : hiddenDivObj.dataset.right,
		'price' : price,
		'quantity' : quantity,
		'includeOpenPositions' : includeOpenPositions
	})

	let marginCalculationResultJsonArr = null
	let marginCalculatorPath = '/marginCalculator'
	let marginCalculatorUrl = baseServerUrl + marginCalculatorPath + '?' + marginCalculatorParams
	//console.log(brokerageUrl)
	await callApi(marginCalculatorUrl).then(result => {marginCalculationResultJsonArr=result});
	errorStatus = marginCalculationResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		console.log(errorStatus)
		return null;
	}
	return marginCalculationResultJsonArr["Success"]	
}

