$(document).ready(function() {
	
	//direct websocket datafeed
	//global variable
	sio = io('wss://breezeapi.icicidirect.com', {
		autoConnect: false,
		path: '/ohlcvstream/',
		transports: ['websocket'],
		auth: { user: userId, token: sessionKey },
		extraHeaders: { 'User-Agent': 'node-socketio[client]/socket' },
		upgrade: true,
		rememberUpgrade: true,
		withCredentials: true
	});
	sio.on("connect_error", (err) => {
		try{
			let errorMessage = err.message
			$('#chartStatus').css("background-color",'rgb(255, 191, 180)');
			$('#output')[0].innerHTML = "<span style='color:red'>error connecting to direct data feed: " + errorMessage + "</span>"
			console.log(`error connecting directly to breezeapi: ${errorMessage}`)
			console.log(err)
			if(err.data && err.data.content)
				console.log(err.data.content)
		}catch(e){console.log(e)}
	});
	sio.on('disconnect', function () {
		$('#chartStatus').css("background-color",'rgb(255, 191, 180)');
		$('#output')[0].innerHTML = "<span style='color:red'>disconnected from direct data feed.Kindly reconnect.</span>"
		setTimeout(function () {
			console.log("disconnected from direct breezeapi websocket.")
		}, 10000);
	});
	sio.on('connect', function () {
		$('#chartStatus').css("background-color",'rgb(183, 250, 183)');
		$('#output')[0].innerHTML = "<span style='color:black'>connected directly to breezeapi websocket for chart tick data</span>"
		console.log("connected directly to breezeapi websocket for chart tick data")
		console.log(sio)
		//direct feed
		//fetch expiry dates for futures dropdown
		runWhenDataproviderConnected();
		//subscribeDirectOHLCV('NIFTY BANK',{'stockCode':'CNXBAN'},ltpListener)
		console.log("if this is reconnection, subscribing other tokens")
		for(channel in allSubscriptions){
			//console.log(channel)
			allSubscriptions[channel].forEach(function(value,index,arr){
				//console.log(subscription)
				productObj = value
				subscribeDirectOHLCV(productObj['token'],channel,productObj,productObj['callback'])
			});			
		}
	});
	sio.on('1SEC', oneSecChannelListener)
	sio.on('1MIN', oneMinChannelListener)
	sio.on('5MIN', fiveMinChannelListener)
	sio.on('30MIN', thirtyMinChannelListener)

	if(isApiConnected){
		sio.connect();
	}
	else{
		console.log("not logged in. direct feed not connected.")
		console.log(sio)
	}
	
});

//global variables
stockCodeTokenDict = {};
tokenStockDict = {};

tickSubscriptions = []
tickSubscriptions.push({'token':'NIFTY BANK','stockCode':'CNXBAN','callback':ltpListener});
tickSubscriptions.push({'token':'NIFTY 50','stockCode':'NIFTY','callback':ltpListener});
tickSubscriptions.push({'token':'INDIA VIX','stockCode':'INDVIX','callback':ltpListener});
allSubscriptions = {'1SEC':tickSubscriptions}
allSubscriptions['1MIN'] = []
allSubscriptions['5MIN'] = []
allSubscriptions['30MIN'] = []


function getStockName(stockCode, expiry, strike, right ){
	let stockName = stockCode + '-' + (expiry ?? '') + '-' + (strike ?? '') + '-' + (right ?? '')
	return stockName;
}

function subscribeDirectOHLCV(token, interval, productObj, callback){
	console.log("subscribing direct feed for " + token)
	//response = sio.emit('leave', '4.1!'+token)
	//console.log(response)
	let stockName;
	if (! (token in tokenStockDict)){
		if(productObj){
			stockName = getStockName(productObj.stockCode,productObj.expiry,productObj.strike,productObj.right)
			tokenStockDict[token] = stockName
			stockCodeTokenDict[stockName] = token
			productObj['token'] = token
			productObj['callback'] = callback
		}
		else{
			let stockCode = ""
			console.log('fetching stock details based on token')
			//call api
			//
			//stockName = getStockName(stockCode,expiry,strike,right)
			tokenStockDict[token] = stockName
			stockCodeTokenDict[stockName] = token
			productObj = {'token':token,'stockCode':stockCode,'callback':callback,'channel':'1SEC'};
		}
	}
	console.log(Object.keys(stockCodeTokenDict))
	console.log(Object.keys(tokenStockDict))
	if(allSubscriptions[interval].findIndex(obj => obj.token==token)==-1){
		console.log("adding new new subscription");
		allSubscriptions[interval].push(productObj)
		console.log(allSubscriptions[interval])
	}
	else{console.log("subscription already exist")}
	sio.emit('join', '4.1!'+token);
}

function unsubscribeDirectOHLCV(token){
	sio.emit('leave', '4.1!'+token);
	
	console.log(tickSubscriptions)
	index = allSubscriptions['1SEC'].findIndex(obj => obj.token==token)
	tickSubscriptions.splice(index,1)
	console.log(tickSubscriptions)	
}

function unsubscribeDirectOHLCV(token,interval){
	if(interval == '1second')
		interval = '1SEC'
	else if(interval == '1minute')
		interval = '1MIN'
	else if(interval == '5minute')
		interval = '5MIN'
	else if (interval == '30minute')
		interval = '30MIN'

	console.log("checking whether we can unsubscribe token: "+token)
	//check if any ltp listeners exist
	//check for refchart
	//check for optionChart
	if(!isLtpListenerExist(token) && !isRefChartToken(token) && !isOptionChartToken(token)){
		console.log("unsubscribing token from direct feed: "+token)
		sio.emit('leave', '4.1!'+token);
		//remove subscription from list
		mySubscriptions = allSubscriptions[interval]
		index = mySubscriptions.findIndex(obj => obj.token==token)
		mySubscriptions.splice(index,1)
	}else{
		console.log("token is in use hence not unsubscribing: "+token)
	}

	//if none then leave
}

function isLtpListenerExist(token){
	let selectorStr = '[id="'+token+'-price"]'
	let ltpElemArr = $(selectorStr).get();
	console.log("ltp listener("+ltpElemArr.length+") exists for token("+token+"): " + (ltpElemArr.length > 0))
	return (ltpElemArr.length > 0)
}

function isRefChartToken(token){
	let selectedRefChartOption = $("#refChart :selected")[0];
	let refChartToken = selectedRefChartOption.getAttribute("token")
	console.log("is it ref chart token("+token+"): " + (refChartToken == token))
	return (refChartToken == token);
}

function isOptionChartToken(token){
	console.log("is it option chart token("+token+"): " + (previousOptionsDataToken == token))
	return (previousOptionsDataToken == token);
}

function oneSecChannelListener(data){
	let ohlcvDataDict = parseTicks(data);
	//ensure errors in each of methods are handled internally and not propogated up
	ltpListener(ohlcvDataDict);
	refChartTickListener(ohlcvDataDict)
	optionChartTickListener(ohlcvDataDict);
}

function oneMinChannelListener(data){
	let ohlcvDataDict = parseTicks(data);
	//console.log("received 1 min data for token:" + ohlcvDataDict["token"])
	let dataInterval = ohlcvDataDict["interval"]
	let dataToken = ohlcvDataDict["token"]
	if(allSubscriptions[dataInterval] != null && allSubscriptions[dataInterval].findIndex(obj => obj.token==dataToken)!=-1){
		refChartFeedDataListener(ohlcvDataDict);
		optionChartFeedDataListener(ohlcvDataDict);
	}
	//else{console.log("ignoring token as not subscribed to this interval")}
}

function fiveMinChannelListener(data){
	let ohlcvDataDict = parseTicks(data);
	console.log("received 5 min data for token:" + ohlcvDataDict["token"])
	let dataInterval = ohlcvDataDict["interval"]
	let dataToken = ohlcvDataDict["token"]
	if(dataToken == undefined)
		console.log(data)
	if(allSubscriptions[dataInterval] != null && allSubscriptions[dataInterval].findIndex(obj => obj.token==dataToken)!=-1){
		refChartFeedDataListener(ohlcvDataDict);
		optionChartFeedDataListener(ohlcvDataDict);
	}
	else{console.log("ignoring token as not subscribed to this interval")}
}

function thirtyMinChannelListener(data){
	let ohlcvDataDict = parseTicks(data);
	console.log("received 30 min data for token:" + ohlcvDataDict["token"])
	let dataInterval = ohlcvDataDict["interval"]
	let dataToken = ohlcvDataDict["token"]
	if(allSubscriptions[dataInterval] != null && allSubscriptions[dataInterval].findIndex(obj => obj.token==dataToken)!=-1){
		refChartFeedDataListener(ohlcvDataDict);
		optionChartFeedDataListener(ohlcvDataDict);
	}
	else{console.log("ignoring token as not subscribed to this interval")}
}

function ltpListener(ohlcvDataDict){
	try{
		let mytoken = ohlcvDataDict['token']
		let selectorStr = '[id="'+mytoken+'-price"]'
		let ltpElemArr = $(selectorStr);
		for(elementIndex in ltpElemArr){
			ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
		}
	}catch(e){console.log('error in method ltpListener');console.log(e)}
}

function parseTicks(ticks){
	//console.log(ticks)
	/* Sample Data
	index: NSE,CNXBAN,43768.55,43768.55,43768.55,43768.55,0,2023-11-21 09:21:42,1SEC
	futures: NFO,CNXBAN,30-Nov-2023,43820.0,43823.9,43823.9,43820.0,675,2141520,2023-11-21 11:13:34,1SEC
	options: NFO,CNXBAN,22-Nov-2023,44000.0,CE,49.7,49.8,49.8,49.7,165,4635675,2023-11-21 11:26:52,1SEC
	*/
	let ticksArr = ticks.split(',')
	//console.log(ticksArr)
	let ticksDict = {}
	ticksDict['exchange_code'] = ticksArr[0]
	ticksDict['stock_code'] = ticksArr[1]
	
	if (ticksArr.length == 9){
		//index data
		ticksDict['low'] = ticksArr[2]
		ticksDict['high'] = ticksArr[3]
		ticksDict['open'] = ticksArr[4]
		ticksDict['close'] = ticksArr[5]
		ticksDict['volume'] = ticksArr[6]
		ticksDict['datetime'] = ticksArr[7]
		ticksDict['interval'] = ticksArr[8]
	}else if (ticksArr.length == 11){
		//futures data
		ticksDict['expiry'] = ticksArr[2]
		ticksDict['low'] = ticksArr[3]
		ticksDict['high'] = ticksArr[4]
		ticksDict['open'] = ticksArr[5]
		ticksDict['close'] = ticksArr[6]
		ticksDict['volume'] = ticksArr[7]
		ticksDict['oi'] = ticksArr[8]
		ticksDict['datetime'] = ticksArr[9]
		ticksDict['interval'] = ticksArr[10]
	}else if (ticksArr.length == 13){
		ticksDict['expiry'] = ticksArr[2]
		ticksDict['strike'] = ticksArr[3].split('.')[0]
		ticksDict['right'] = ticksArr[4]
		ticksDict['low'] = ticksArr[5]
		ticksDict['high'] = ticksArr[6]
		ticksDict['open'] = ticksArr[7]
		ticksDict['close'] = ticksArr[8]
		ticksDict['volume'] = ticksArr[9]
		ticksDict['oi'] = ticksArr[10]
		ticksDict['datetime'] = ticksArr[11]
		ticksDict['interval'] = ticksArr[12]
	}
	let tickStockName = getStockName(ticksDict['stock_code'],ticksDict['expiry'],ticksDict['strike'],ticksDict['right'])
	//console.log(tickStockName)
	//console.log(stockCodeTokenDict)
	let tickToken = stockCodeTokenDict[tickStockName]
	ticksDict['token'] = tickToken
	//console.log(ticksDict)
	return ticksDict
}


function loginForChartData(myuserId,mysessionKey,broker){
	console.log("******************************login credentials for chart**********************")
	console.log(myuserId)
	console.log(mysessionKey)
	sio.auth.user = myuserId;
	sio.auth.token = mysessionKey;
	sio.connect();
	// Tell the backend Socket.IO to plug in the data provider!
   socket.emit('init_dataprovider', { broker: broker });
}




