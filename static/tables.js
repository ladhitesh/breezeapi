$(document).ready(function() {
	$('#orderList').dynatable({
		features: {
			paginate: false,
			recordCount: false,
			sort: false,
			search: false
		},
		table : { headRowClass: 'dynatable-header' },
	});
	$('#openPositions').dynatable({
		features: {
			paginate: false,
			recordCount: false,
			sort: false,
			search: false
		},
		table : { headRowClass: 'dynatable-header' },
	});
	$('#watchList').dynatable({
		features: {
			paginate: false,
			recordCount: false,
			sort: false,
			search: false
		},
		table : { headRowClass: 'dynatable-header', copyHeaderClass: true },
		writers: {
			_rowWriter: myDynaRowWriter
		},
	});

	// Initialize the plugin
	$('#JPO').popup({
		color: 'white',
		opacity: 1,
		transition: '0.3s',
		scrolllock: true
	});

	// Set default `pagecontainer` for all popups (optional, but recommended for screen readers and iOS*)
	$.fn.popup.defaults.pagecontainer = '#page'
	
	if (isApiConnected){
		//populate existing data
		populateOpenPositions()
		populateOrderList()
		socket.on('order_notification', orderNotification)
	}
	
})

function myDynaRowWriter(rowIndex, record, columns, cellWriter) {
	var tr = '';

	// grab the record's attribute for each column
	for (var i = 0, len = columns.length; i < len; i++) {
		tr += cellWriter(columns[i], record);
	}

	return '<tr rowindex="'+rowIndex+'" draggable="true" ondragstart="start()"  ondragover="dragover()" >' + tr + '</tr>';
};


//Table row drag drop start
var row;

function start(){  
	row = event.target; 
}

function dragover(){
	var e = event;
	e.preventDefault(); 

	let children= Array.from(e.target.parentNode.parentNode.children);

	if(children.indexOf(e.target.parentNode)>children.indexOf(row))
		e.target.parentNode.after(row);
	else
		e.target.parentNode.before(row);
}

//Table row drag drop end



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

async function makeOrderRecord(hiddenDivObj,orderId,orderTime,stock,action,qty,price,stoploss,orderType,orderStatus){
	var orderId = orderId
	var orderTime = orderTime
	var stock = stock
	var action = action
	var qty = qty
	var price = price
	var orderType = orderType
	var orderStatus = orderStatus
	modifyButton=""
	if(orderStatus == "Ordered"){
		//modifyButton = "<button id='modifyOrdBtn-"+orderId+"' onClick='populateModifyOrder(this,\""+action+"\",\""+qty+"\",\""+price+"\",\""+orderSl+"\")'>Modify</button>"
	
		modifyButton = `<img id='modifyOrdBtn-${orderId}' onClick='populateModifyOrder(this,"${action}","${qty}","${price}","${orderSl}")' src='/static/images/modify.png' width='20' height='20' />`
	}
	if(orderStatus.toLowerCase() != "executed"){
		if (orderType.toLowerCase() == "market")
			price = "Mkt"
	}
	
	cancelButton=""
	if(orderStatus.toLowerCase() != "cancelled" && orderStatus.toLowerCase() != "executed" )
		cancelButton=`<img id='cancelOrdBtn-${orderId}' onClick='cancelOrder("${orderId}")' src='/static/images/cancel.png' width='20' height='20'/>`
	
	record = new Object();
	record.hiddenColumn=hiddenDivObj.outerHTML;
	record.id=orderTime
	record.stock=stock
	record.qty=qty
	record.type=action
	record.status="<div id='status-"+orderId+"'>"+orderStatus+"</div>"
	record.x=cancelButton
	record.modify=modifyButton
	record.price="<div id='price-"+orderId+"'>"+price+"</div>"
	record.sl=stoploss
	return record
}

async function makePositionRecord(hiddenDivObj,stock,action,qty,price){	
	var action = action
	var qty = qty
	var price = price
	exitButton = `<img onClick='squareoffStock("${stock}","${hiddenDivObj.id}","${qty}")' src="/static/images/exit.png" width="40" height="20"/>`
	ltpDiv = `<div priceType='openPosition' id='${hiddenDivObj.dataset.token}-price'>${price}</div>`
	record = new Object();
	record.hiddenColumn=hiddenDivObj.outerHTML;
	record.stock=stock
	record.type=action
	record.qty=qty
	record.price=price
	record.ltp=ltpDiv
	record.pnl=""
	record.x=exitButton	
	return record
}

function calculatePnl(ltpDivObj){
	console.log("calculating Pnl")
	console.log(ltpDivObj)
}

async function getStockToken(hiddenDivObj){
	var stockTokenArr
	fnotype = hiddenDivObj.dataset.fnotype
	if(fnotype == "OPT")
		fnotype = "Options"
	right = hiddenDivObj.dataset.right
	if(right == "CE"){right="Call"}else if (right=="PE"){right="Put"}
	
	var stockTokenParams = new URLSearchParams({
			'stockCode' : hiddenDivObj.dataset.stockcode,
			'strike' : hiddenDivObj.dataset.strike,
			'expiryDate' : hiddenDivObj.dataset.expiry,
			'rightType' : right,
			'productType' : fnotype,
			'exchangeCode' : hiddenDivObj.dataset.exchangecode,
		})
	var stockTokenUrl = baseServerUrl + '/getStockToken?'+stockTokenParams
	await callApi(stockTokenUrl).then(result => {stockTokenArr=result});
	//console.log(stockTokenArr)
	return stockTokenArr
}

async function populateOpenPositions(){
	$("#openPositions tbody").empty();
	var openPositionsJsonArr;
	var openPositionsUrl = baseServerUrl + '/getOpenPositions'
	await callApi(openPositionsUrl).then(result => {openPositionsJsonArr=result});
	
	openPositionsJsonArr = openPositionsJsonArr["Success"]
	//console.log(openPositionsJsonArr)
	//console.log("openposition ^^^")
	const positionRecords = []
	for( openPositionIndex in openPositionsJsonArr){
		
		action = openPositionsJsonArr[openPositionIndex]["action"]
		if(action == "NA")
			continue;
		
		quantity = openPositionsJsonArr[openPositionIndex]["quantity"]
		price = openPositionsJsonArr[openPositionIndex]["average_price"]
		
		//stock name
		product = openPositionsJsonArr[openPositionIndex]["product_type"]
		if(product=="Options"){product="OPT"}
		stockCode = openPositionsJsonArr[openPositionIndex]["stock_code"]
		expiry = openPositionsJsonArr[openPositionIndex]["expiry_date"]
		strike = openPositionsJsonArr[openPositionIndex]["strike_price"]
		exchangecode = openPositionsJsonArr[openPositionIndex]["exchange_code"]
		right = openPositionsJsonArr[openPositionIndex]["right"]
		if(right == "Call"){right = "CE"} else if(right=="Put"){right="PE"}
									  
		stockName = product+'-'+stockCode+'-'+expiry+'-'+strike+'-'+right
		//console.log(stockName)
		var hiddenDivObj = document.createElement("div");
		hiddenDivObj.setAttribute("id","op-"+stockName)
		hiddenDivObj.setAttribute("data-stockcode",stockCode)
		hiddenDivObj.setAttribute("data-code",stockName)
		hiddenDivObj.setAttribute("data-expiry",expiry)
		hiddenDivObj.setAttribute("data-strike",strike)
		hiddenDivObj.setAttribute("data-right",right)
		hiddenDivObj.setAttribute("data-fnotype",product)
		hiddenDivObj.setAttribute("data-exchangecode",exchangecode)
		
		var stockTokenDict
		await getStockToken(hiddenDivObj).then(result => stockTokenDict = result);
		const token = stockTokenDict["quotesToken"].split("!")[1]
		console.log("token for openposition: "+token)
		hiddenDivObj.setAttribute("data-token",token)
		
		await makePositionRecord(hiddenDivObj,stockName,action,quantity,price).then(result => {positionRecords[openPositionIndex]=result});
		console.log("subscribing to token:"+token)
		socket.emit('subscribeQuotes', token, "1second")
		socket.on(token+"-1second", function (ohlcvData){
			ohlcvDataDict = JSON.parse(ohlcvData);
			selectorStr = '[id='+token+'-price]'
			ltpElemArr = $(selectorStr);
			for(elementIndex in ltpElemArr){
				ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
			}
		});

	}
	
	obj = new Object();
	obj.records = positionRecords;
	if(openPositionsJsonArr != null){
		obj.queryRecordCount = openPositionsJsonArr.length + 1;
		obj.totalRecordCount = openPositionsJsonArr.length + 1;
	}
	var openPositionsTable = $('#openPositions').data('dynatable');
	openPositionsTable.records.updateFromJson(obj)
	openPositionsTable.dom.update();
		
}


async function populateOrderList(){
	$("#orderList tbody").empty();
	var orderListJsonArr;
	var orderListUrl = baseServerUrl + '/getOrderList'
	await callApi(orderListUrl).then(result => {orderListJsonArr=result});
	
	
	//console.log(orderListJsonArr["Success"])
	orderListJsonArr = orderListJsonArr["Success"]
	
	const orderRecords = []
	for( orderIndex in orderListJsonArr){

		
		orderId = orderListJsonArr[orderIndex]["order_id"]
		orderTime = orderListJsonArr[orderIndex]["order_datetime"]
		quantity = orderListJsonArr[orderIndex]["quantity"]
		price = orderListJsonArr[orderIndex]["price"]
		status = orderListJsonArr[orderIndex]["status"]
		if(status=="Executed")
			price = orderListJsonArr[orderIndex]["average_price"]
		action = orderListJsonArr[orderIndex]["action"]
		orderType = orderListJsonArr[orderIndex]["order_type"]
		pendingQuantity = orderListJsonArr[orderIndex]["pending_quantity"]
		//stock name
		product = orderListJsonArr[orderIndex]["product_type"]
		if(product=="Options"){product="OPT"}
		stockCode = orderListJsonArr[orderIndex]["stock_code"]
		expiry = orderListJsonArr[orderIndex]["expiry_date"]
		strike = orderListJsonArr[orderIndex]["strike_price"]
		exchangecode = orderListJsonArr[orderIndex]["exchange_code"]
		stoploss = orderListJsonArr[orderIndex]["stoploss"]
		right = orderListJsonArr[orderIndex]["right"]
		if(right == "Call"){right = "CE"} else if(right=="Put"){right="PE"}
									  
		stockName = product+'-'+stockCode+'-'+expiry+'-'+strike+'-'+right
		//console.log(stockName)
		var hiddenDivObj = document.createElement("div");
		hiddenDivObj.setAttribute("id","ol-"+orderId)
		hiddenDivObj.setAttribute("orderId",orderId)
		hiddenDivObj.setAttribute("data-stockcode",stockCode)
		hiddenDivObj.setAttribute("data-code",stockName)
		hiddenDivObj.setAttribute("data-expiry",expiry)
		hiddenDivObj.setAttribute("data-strike",strike)
		hiddenDivObj.setAttribute("data-right",right)
		hiddenDivObj.setAttribute("data-fnotype",product)
		hiddenDivObj.setAttribute("data-exchangecode",exchangecode)
		await makeOrderRecord(hiddenDivObj,orderId,orderTime,stockName,action,quantity,price,stoploss,orderType,status).then(result => {orderRecords[orderIndex]=result});
		//console.log(orderRecords[orderIndex].id)
	
	}
	
	obj = new Object();
	obj.records = orderRecords;
	if(orderListJsonArr != null){
		obj.queryRecordCount = orderListJsonArr.length + 1;
		obj.totalRecordCount = orderListJsonArr.length + 1;
	}
	var orderListTable = $('#orderList').data('dynatable');
	orderListTable.records.updateFromJson(obj)
	orderListTable.dom.update();
		
	/*
	    {
    "Error": null,
    "Status": 200,
    "Success": [
        {
            "LTP": null,
            "SLTP_price": null,
            "action": "Buy",
            "average_price": "0",
            "cancelled_quantity": "15",
            "cutoff_price": null,
            "disclosed_quantity": "0",
            "exchange_acknowledge_number": null,
            "exchange_acknowledgement_date": null,
            "exchange_code": "NFO",
            "exchange_order_id": "1500000215309443",
            "expiry_date": "26-Oct-2023",
            "initial_limit": null,
            "intial_sltp": null,
            "limit_offset": null,
            "mbc_flag": null,
            "modification_number": null,
            "order_datetime": "25-Oct-2023 14:19:02",
            "order_id": "202310251500031281",
            "order_type": "Limit",
            "parent_order_id": "",
            "pending_quantity": "15",
            "price": "1",
            "product_type": "Options",
            "quantity": "15",
            "right": "Call",
            "status": "Cancelled",
            "stock_code": "CNXBAN",
            "stoploss": "0",
            "strike_price": 43000,
            "user_remark": null,
            "validity": "Day",
            "validity_date": null
        },

	
	
	*/
}



async function modifyOrder(){
	//validate order related data
	hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		console.log("hiddenDataColumnId is empty. Do not have data to place order.")
		captionObj = $("#orderMessages")[0]
		captionObj.innerHTML="Select stock from watchlist to place order."
		return
	}
	
	hiddenDivObj = $("#"+hiddenDivId)[0]
	var hiddenOlDivObj = null;
	var modifyOrder = true
	var hiddenOrderId = $("#hiddenOrderId")[0].innerText
	hiddenOlDivId = "ol-"+hiddenOrderId
	hiddenOlDivObj = $("#"+hiddenOlDivId)[0]
	var stock = $('#orderStock')[0].innerText;
	var qty = $('#orderQty')[0].value;
	var action = $('#orderAction')[0].innerText;;
	var price = $('#orderPrice')[0].value;
	var orderSl = $('#orderSl')[0].value;
	var orderId = moment().format("DDMMYYYYHHmmss")
	orderId = hiddenOrderId
	orderStatus = $('#status-'+orderId)[0].innerText;
	if(orderStatus != "Ordered"){
		clearOrder()
		return;
	}
	var exchangeCode = hiddenOlDivObj.dataset.exchangecode
	var modifyOrderParams = new URLSearchParams({
		'orderId' : orderId,
		'exchangeCode' : exchangeCode,
		'price' : price,
		'quantity' : qty,
		'stoploss' : orderSl
	})
	var orderResultJsonArr = null
	var modifyOrderUrl = baseServerUrl + '/modifyOrder?' + modifyOrderParams
	console.log(modifyOrderUrl)
	await callApi(modifyOrderUrl).then(result => {orderResultJsonArr=result});
	errorStatus = orderResultJsonArr["Error"]
	captionObj = $("#orderMessages")[0]
	if(errorStatus != null && errorStatus != ""){
		captionObj.innerHTML=errorStatus
		return;
	}
	else{
		captionObj.innerHTML=orderResultJsonArr["Success"]["message"]
	}

	orderId = orderResultJsonArr["Success"]["order_id"]
	var orderListTable = $('#orderList').data('dynatable');
	var existingRecords = orderListTable.records.getFromTable()
	
	var myRecords = null;
	var recordIndex = 0;
	for(record in existingRecords){
		hiddenColumnDiv = existingRecords[record].hiddenColumn	
		if(hiddenColumnDiv.includes(hiddenOrderId)){
			recordIndex = record
			myRecords = existingRecords;
		}
	}
	orderTime = moment().format("DD-MM-YYYY HH:mm:ss")
	
	//modifyBtn = "<button id='modifyOrdBtn-"+orderId+"' onClick='populateModifyOrder(this,\""+action+"\",\""+qty+"\",\""+price+"\",\""+orderSl+"\")'>Modify</button>"
	
	modifyBtn = `<img id='modifyOrdBtn-${orderId}' onClick='populateModifyOrder(this,"${action}","${qty}","${price}","${orderSl}")' src='/static/images/modify.png' width='20' height='20' />`
	cancelBtn = `<img id='cancelOrdBtn-${orderId}' onClick='cancelOrder("${orderId}")' src='/static/images/cancel.png' width='20' height='20'/>`

	//myRecords = JSON.parse($records.text());
	myRecords[recordIndex].hiddenColumn=hiddenOlDivObj.outerHTML
	myRecords[recordIndex].id=orderTime
	myRecords[recordIndex].stock=stock
	myRecords[recordIndex].qty=qty
	myRecords[recordIndex].type=action
	myRecords[recordIndex].status="<div id='status-"+orderId+"'></div>"
	myRecords[recordIndex].x=cancelBtn
	myRecords[recordIndex].modify=modifyBtn	

	if (price == 0)
		myRecords[recordIndex].price = "Mkt"
	else
		myRecords[recordIndex].price = price
	
	myRecords[recordIndex].sl=orderSl
	obj = new Object();
	obj.records = myRecords;
	obj.queryRecordCount = existingRecords.length + 1;
	obj.totalRecordCount = existingRecords.length + 1;
	orderListTable.records.updateFromJson(obj)
	orderListTable.dom.update();

	//reset
	clearOrder()
}

async function addOrder(){
	
	//validate order related data
	hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		console.log("hiddenDataColumnId is empty. Do not have data to place order.")
		captionObj = $("#orderMessages")[0]
		captionObj.innerHTML="Select stock from watchlist to place order."
		return
	}
	
	hiddenDivObj = $("#"+hiddenDivId)[0]
	
	
	var hiddenOlDivObj = null;
	var modifyOrder = false
	
	var hiddenOrderId = $("#hiddenOrderId")[0].innerText
	
	modifyOrder = false
	var stock = $('#orderStock')[0].innerText;
	var qty = $('#orderQty')[0].value;
	var action = $('#orderAction')[0].innerText;;
	var price = $('#orderPrice')[0].value;
	var orderSl = $('#orderSl')[0].value;
	var orderId = moment().format("DDMMYYYYHHmmss")
	
	//call api to place order and fetch order id
	if(!modifyOrder){
		//new order
		var newOrderParams = new URLSearchParams({
			'stockCode' : hiddenDivObj.dataset.stockcode,
			'strike' : hiddenDivObj.dataset.strike,
			'expiryDate' : hiddenDivObj.dataset.expiry,
			'action' : action.toLowerCase(),
			'rightType' : hiddenDivObj.dataset.right,
			'price' : price,
			'quantity' : qty,
			'stoploss' : orderSl
		})
		
		var orderResultJsonArr = null
		var newOrderUrl = baseServerUrl + '/placeOrder?' + newOrderParams
		console.log(newOrderUrl)
		await callApi(newOrderUrl).then(result => {orderResultJsonArr=result});
		errorStatus = orderResultJsonArr["Error"]
		captionObj = $("#orderMessages")[0]
		if(errorStatus != null && errorStatus != ""){
			captionObj.innerHTML=errorStatus
			clearOrder()
			return;
		}
		else{
			captionObj.innerHTML=orderResultJsonArr["Success"]["message"]
		}
			
		orderId = orderResultJsonArr["Success"]["order_id"]
		
	}
		
	var orderListTable = $('#orderList').data('dynatable');
	var existingRecords = orderListTable.records.getFromTable()
	
	var myRecords = null;
	var recordIndex = 0;
	if(!modifyOrder) {
		hiddenOlDivObj = $(hiddenDivObj).clone()[0];
		hiddenOlDivObj.setAttribute('id','ol-' + orderId)
		//hardcoding fetch orderid from json response to place order
		hiddenOlDivObj.setAttribute('orderId',orderId)
		myRecords = [new Object()];
	}
	
	orderTime = moment().format("DD-MM-YYYY HH:mm:ss")
	
	//modifyBtn = "<button id='modifyOrdBtn-"+orderId+"' onClick='populateModifyOrder(this,\""+action+"\",\""+qty+"\",\""+price+"\",\""+orderSl+"\")'>Modify</button>"
	
	modifyBtn = `<img id='modifyOrdBtn-${orderId}' onClick='populateModifyOrder(this,"${action}","${qty}","${price}","${orderSl}")' src='/static/images/modify.png' width='20' height='20' />`
	cancelBtn = `<img id='cancelOrdBtn-${orderId}' onClick='cancelOrder("${orderId}")' src='/static/images/cancel.png' width='20' height='20'/>`

	//myRecords = JSON.parse($records.text());
	myRecords[recordIndex].hiddenColumn=hiddenOlDivObj.outerHTML
	myRecords[recordIndex].id=orderTime
	myRecords[recordIndex].stock=stock
	myRecords[recordIndex].qty=qty
	myRecords[recordIndex].type=action
	myRecords[recordIndex].status="<div id='status-"+orderId+"'></div>"
	myRecords[recordIndex].x=cancelBtn
	myRecords[recordIndex].modify=modifyBtn	

	if (price == 0)
		myRecords[recordIndex].price = "Mkt"
	else
		myRecords[recordIndex].price = price
	
	myRecords[recordIndex].sl=orderSl
	if(!modifyOrder){
		myRecords = myRecords.concat(existingRecords);
	}
	
	obj = new Object();
	obj.records = myRecords;
	obj.queryRecordCount = existingRecords.length + 1;
	obj.totalRecordCount = existingRecords.length + 1;
	orderListTable.records.updateFromJson(obj)
	orderListTable.dom.update();

	//reset
	clearOrder()
}
async function cancelOrder(cancelOrderId){
	var captionObj = $("#orderMessages")[0]
	var orderStatus = $("#status-"+cancelOrderId)[0]
	if(orderStatus.innerText.toLowerCase() == "cancelled")	{
		captionObj.innerHTML="Order is already cancelled:"+cancelOrderId
		orderStatus.parentNode.nextSibling.innerHTML=""
		return
	}
		
	
	var cancelOrderParams = new URLSearchParams({
			'orderId' : cancelOrderId
		})		
		var orderResultJsonArr = null
		var cancelOrderUrl = baseServerUrl + '/cancelOrder?' + cancelOrderParams
		console.log(cancelOrderUrl)
		await callApi(cancelOrderUrl).then(result => {orderResultJsonArr=result});
		errorStatus = orderResultJsonArr["Error"]
		
		if(errorStatus != null && errorStatus != ""){		
			captionObj.innerHTML=errorStatus
		}else{
			captionObj.innerHTML=orderResultJsonArr["Success"]["message"]
			cancelTdObj = orderStatus.parentNode.nextSibling
			modifyTdObj = cancelTdObj.nextSibling
			cancelTdObj.innerHTML=""
			modifyTdObj.innerHTML=""
			
		}

}
function populateModifyOrder(modifyButtonObj,action,qty,price,sl){
	trObj = $(modifyButtonObj).closest("tr")[0]
	hiddenDivObj = trObj.firstChild.firstChild
	modifyOrderId = hiddenDivObj.getAttribute('orderid')
	$('#hiddenOrderId')[0].innerText=modifyOrderId
	$('#hiddenDataColumnId')[0].innerText=hiddenDivObj.getAttribute("id")
	$('#orderStock')[0].innerText=hiddenDivObj.dataset.code
	$('#orderAction')[0].innerText = action;
	$('#orderQty')[0].valueAsNumber = qty;
	$('#orderPrice')[0].valueAsNumber = price;
	$('#orderSl')[0].valueAsNumber = sl;
	$('#orderButton')[0].value="Modify"
	$('#orderButton')[0].onclick=modifyOrder
	
}
function clearOrder(){
	$("#hiddenOrderId")[0].innerText=""
	$("#hiddenDataColumnId")[0].innerText=""
	$('#orderStock')[0].innerText=""
	$('#orderAction')[0].innerText = "";
	$('#orderQty')[0].valueAsNumber = 15;
	$('#orderPrice')[0].valueAsNumber = 0;
	$('#orderSl')[0].valueAsNumber = 0;
	$('#orderButton')[0].value="Order"
}
function refreshOrderList(){
	populateOrderList();
}
function refreshOpenPositions(){
	populateOpenPositions();
}
function clearWatchList(){
	var watchListTableObj = $('#watchList')[0]
	for (var i = 1, row; row = watchListTableObj.rows[i]; i++) {
		for (var j = 0, col; col = row.cells[j]; j++) {
		  	hiddenDivObj = col.firstChild
			token = hiddenDivObj.dataset.token
			console.log("unsubscribe token: "+token)
			response = socket.emit('unsubscribeQuotes', token, "1second")	
			//console.log(response)
			break;
		}  
	}
	
	$("#watchList tbody").empty();
}
			
async function getWatchListStocks(){

	var fnOJsonArr
	searchStr = $('#seachStock')[0].value
	fnoStocksUrl = baseServerUrl + '/getFnOStocks?' + new URLSearchParams({'searchStr': searchStr})
	await callApi(fnoStocksUrl).then(result => {fnOJsonArr=result});
	
	$("#stock-selection").empty()

	fnOJsonArr.forEach(function(eachStock) { 
		optionObj = $('<option/>')
		for (const [key, value] of Object.entries(eachStock)) {	
			optionObj.attr("data-"+key,value)
			//console.log(key, value);
		}
		optionObj.attr("value",eachStock.token).text(eachStock.code).appendTo('#stock-selection');
	});

}

function addToWatchList() {
	var watchListTable = $('#watchList').data('dynatable');
	var selectedStock = $('#stock-selection').find(":selected")[0]
	if(selectedStock.value == 0)
		return;
	
	var hiddenDivObj = document.createElement("div");
	for (data in selectedStock.dataset) {
		hiddenDivObj.setAttribute("data-"+data,selectedStock.dataset[data])
	}
	token = selectedStock.value
	stockName = selectedStock.text

	hiddenDivId = "wl-"+token
	if($("#" + hiddenDivId).length > 0) {
		alert('stock already in watchlist')
		return;
	}
	
	hiddenDivObj.setAttribute("id",hiddenDivId)
	
	//buyAction = `<button onClick='buyStock("${stockName}","${hiddenDivId}")'>Buy</button> `
	//sellAction = `<button onClick='sellStock("${stockName}","${hiddenDivId}")'>Sell</button> `
	//remove = "<button onClick='removeFromWatchList(this)'>X</button>"
	buyAction = `<img width='40' height='25' src="/static/images/buy1.png" alt="Buy" onClick='buyStock("${stockName}","${hiddenDivId}")'/> `
	sellAction = `<img width='40' height='25' src="/static/images/sell1.png" alt="Sell" onClick='sellStock("${stockName}","${hiddenDivId}")'/> `
	remove = "<img width='20' height='18' src='/static/images/bin.png' alt='Remove' onClick='removeFromWatchList(this)'/>"
	
	showChart = "&nbsp;<img onClick='loadOptionsData(\""+hiddenDivId+"\")' src='/static/images/chart.png' width='18' height='18' alt='Show Chart'>"
	
	myRecords = [new Object()];
	myRecords[0].hiddenColumn=hiddenDivObj.outerHTML
	myRecords[0].stock=stockName + showChart
	myRecords[0].price = "<div id='"+token+"-price'></div>"
	myRecords[0].action = buyAction + sellAction
	myRecords[0].x = remove	


	existingRecords = watchListTable.records.getFromTable()
	myRecords = myRecords.concat(existingRecords);
	obj = new Object();
	obj.records = myRecords;
	obj.queryRecordCount = existingRecords.length + 1;
	obj.totalRecordCount = existingRecords.length + 1;

	watchListTable.records.updateFromJson(obj);
	watchListTable.dom.update();
	const inputToken = token
	subscribeQuotesFeed(inputToken)
	
}

function removeFromWatchList(removeButtonObj) {
	trObj = $(removeButtonObj).closest("tr")[0]
	hiddenDivObj = trObj.firstChild.firstChild
	token = hiddenDivObj.getAttribute('data-token')
	ltpElemArr = $('#'+token+'-price');
	if(ltpElemArr.length < 2)
		response = socket.emit('unsubscribeQuotes', token, "1second")
	$(removeButtonObj).closest("tr").remove();
}
function buyStock(stockToBuy,hiddenDivId){
	clearOrder()
	$("#orderStock")[0].innerText = stockToBuy
	$("#orderAction")[0].innerText = "Buy"
	$($("#orderAction")[0]).css("color","green")
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="Buy"
	$('#orderButton')[0].onclick=addOrder
}

//adjust this function to call squareoff api
function squareoffStock(stockToSell,hiddenDivId,qty){
	clearOrder()
	$("#orderStock")[0].innerText = stockToSell
	$("#orderAction")[0].innerText = "Sell"
	$("#orderQty")[0].valueAsNumber = qty;
	$($("#orderAction")[0]).css("color","red")
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="squareoff"
	$('#orderButton')[0].onclick=squareoffOpenPosition
}

function squareoffOpenPosition(){
	addOrder();
}

function sellStock(stockToSell,hiddenDivId){
	clearOrder()
	$("#orderStock")[0].innerText = stockToSell
	$("#orderAction")[0].innerText = "Sell"
	$($("#orderAction")[0]).css("color","red")
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="Sell"
	$('#orderButton')[0].onclick=addOrder
}
function subscribeQuotesFeed(token){
	//alert("subscribing to quotes feed for token: "+token)
	response = socket.emit('subscribeQuotes', this.token, "1second")
	//socket.emit('unsubscribeQuotes', "NIFTY BANK", "1second")

	const inputToken = this.token
	socket.on(inputToken+'-1second', function (ohlcvData){
		ohlcvDataDict = JSON.parse(ohlcvData);
		selectorStr = '[id='+inputToken+'-price]'
		ltpElemArr = $(selectorStr);
		for(elementIndex in ltpElemArr){
			ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
		}
	});
	
	
}



function orderNotification(notificationData){
	notificationDataDict = JSON.parse(notificationData);
	console.log("orderNotification-->" + notificationData)
	//$('#output')[0].innerHTML = "<pre>"+new Date().toLocaleString()+" : " + notificationDataDict + "</pre>"
	orderId = notificationDataDict["orderReference"];
	orderStatus = notificationDataDict["orderStatus"];
	//console.log(orderId+"-->"+orderStatus)
	//update status
	$('#status-'+orderId)[0].innerText = orderStatus
	if(orderStatus.toLowerCase() == "executed"){
		$('#cancelOrdBtn-'+orderId)[0].remove();
		$('#modifyOrdBtn-'+orderId)[0].remove();
		refreshOpenPositions();
		refreshFunds();
	}
	//$('#price-'+orderId)[0].innerText = orderStatus
}

async function getRealisedPnl(){
	var pnlResultJsonArr = null
	var fromDateStr = $($("#fromDatepicker")).val()
	var toDateStr = $($("#toDatepicker")).val()
	
	var realisedPnlParams = new URLSearchParams({
			'fromDate' : fromDateStr,
			'toDate' : toDateStr
		})
	var realisedPnlUrl = baseServerUrl + '/getRealisedPnL?' + realisedPnlParams
	console.log(realisedPnlUrl)
	await callApi(realisedPnlUrl).then(result => {pnlResultJsonArr=result});
	//console.log(pnlResultJsonArr)
	errorStatus = pnlResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		if(errorStatus == "No Data Found"){
			realisedPnl = "0";
			realisedPnlWithTaxes = "0";
		}
		else{return;}
	}
	else{
		realisedPnl = pnlResultJsonArr["Success"]["realised_pnl"]
		realisedPnlWithTaxes = pnlResultJsonArr["Success"]["realised_pnl_with_taxes"]
	}

	$("#realisedPnl")[0].innerHTML=realisedPnl;
	$("#realisedPnlWithTaxes")[0].innerHTML=realisedPnlWithTaxes;
}

async function refreshFunds(){
	
	fundsResultJsonArr = null
	var fundsUrl = baseServerUrl + '/getFunds'
	console.log(fundsUrl)
	await callApi(fundsUrl).then(result => {fundsResultJsonArr=result});
	//console.log(pnlResultJsonArr)
	errorStatus = fundsResultJsonArr["Error"]
	if(errorStatus != null && errorStatus != ""){
		if(errorStatus == "Not connected"){
			allocatedFnoFunds = "NA";
			blockedFnoFunds = "NA";
		}
		else{return;}
	}
	else{
		allocatedFnoFunds = fundsResultJsonArr["Success"]["allocated_fno"]
		blockedFnoFunds = fundsResultJsonArr["Success"]["block_by_trade_fno"]
	}

	$("#fnoAllocated")[0].innerHTML=allocatedFnoFunds;
	$("#fnoBlocked")[0].innerHTML=blockedFnoFunds;
	
}
