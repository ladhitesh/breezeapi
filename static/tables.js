$(document).ready(function() {
	$('#orderList').dynatable({
		features: {
			paginate: false,
			recordCount: true,
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
	
})

$(initIfConnected)

function initIfConnected(){
	
	searchStr = localStorage.getItem("searchStr")
	$('#searchStock').val(searchStr)
	populateWatchList()

	if (isApiConnected){
		//populate existing data
		populateOpenPositions()
		populateOrderList()		
		refreshMargins()	
		//sio.on('1SEC',ltpUpdateListener)
	}
}

function myDynaRowWriter(rowIndex, record, columns, cellWriter) {
	var tr = '';
	// grab the record's attribute for each column
	for (var i = 0, len = columns.length; i < len; i++) {
		tr += cellWriter(columns[i], record);
	}
	return '<tr rowindex="'+rowIndex+'" draggable="true" ondragstart="hideMarketDepth();start()"  ondragover="dragover()" >' + tr + '</tr>';
};


//Table row drag drop start
var row;
function start(){  
	row = event.target; 
}

function dragover(){
	var e = event; e.preventDefault(); 
	let children= Array.from(e.target.parentNode.parentNode.children);
	if(children.indexOf(e.target.parentNode)>children.indexOf(row))
		e.target.parentNode.after(row);
	else
		e.target.parentNode.before(row);
}
//Table row drag drop end

function attachLtpObservers(){
	//const currentDate = new Date(); const milliseconds = currentDate. getMilliseconds(); console. log(milliseconds); 
	//console.log("attached")
	//console.log($("[priceType^='op-']")[0])
	openPositionLtpObjArr = $("[priceType^='op-']").get()
	for(elementIndex in openPositionLtpObjArr){
		openPositionLtpObj = openPositionLtpObjArr[elementIndex];
		//console.log(openPositionLtpObj)
		try{
			let observer = new MutationObserver(calculateLivePnl);
			observer.observe(openPositionLtpObj, {characterData:true,childList:true,subtree:false});
			//console.log(openPositionLtpObj)
			//console.log(observer)
		}catch(e){console.log("Error in observer.");console.log(e)}
	}
}

function makeOrderRecord(hiddenDivObj,orderId,orderTime,stock,action,qty,price,stoploss,orderType,orderStatus){
	var orderId = orderId
	var orderTime = orderTime
	var stock = stock
	var action = action
	var qty = qty
	var price = price
	var orderType = orderType
	var orderStatus = orderStatus

	modifyButton=""
	if(orderStatus.toLowerCase() == "ordered" || orderStatus.toLowerCase() == "requested" ){
		modifyButton = `<img id='modifyOrdBtn-${orderId}' onClick='populateModifyOrder(this,"${action}","${qty}","${price}","${stoploss}")' src='/static/images/modify.png' width='20' height='20' />`
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
	record.edit=modifyButton
	record.price="<div id='price-"+orderId+"'>"+price+"</div>"
	record.sl=stoploss
	return record
}

function makePositionRecord(hiddenDivObj,stock,action,qty,price){	
	var action = action
	var qty = qty
	var price = price
	var exitButton = `<img onClick='squareoffStock("${stock}","${hiddenDivObj.id}","${qty}")' src="/static/images/exit.png" width="40" height="20"/>`

	var showChart = `&nbsp;<img onClick='loadOptionsData("${hiddenDivObj.id}")' src='/static/images/chart.png' width='18' height='18' alt='Show Chart' style='display:inline'>`
	
	//var ltpDiv = document.createElement('div');
	//ltpDiv.id = hiddenDivObj.dataset.token + '-price'
	//ltpDiv.setAttribute("priceType","op-"+stock)
	//ltpDiv.innerHTML = price
	//record.ltp=ltpDiv.outerHTML;

	record = new Object();
	record.hiddenColumn=hiddenDivObj.outerHTML;
	record.stock=stock + showChart
	record.type=action
	record.qty=qty
	record.price=price
	
	record.pnl=""
	record.x=exitButton	
	return record
}

function calculateLivePnl(mutationRecord){
	try{
		//console.log("calculating Pnl")
		//console.log(mutationRecord[0])
		ltp = mutationRecord[0].target.innerHTML
		quantity = mutationRecord[0].target.parentElement.previousSibling.previousSibling.innerHTML;
		cost = mutationRecord[0].target.parentElement.previousSibling.innerHTML;
		pnlObj = mutationRecord[0].target.parentElement.nextSibling
		pnl = (quantity*ltp) - (quantity*cost);
		pnl = Math.round(pnl * 100) / 100
		pnlObj.style.fontWeight = "bold"
		pnlObj.style.color = pnl < 0 ? "red" : "green"
		pnlObj.innerHTML = pnl
	}catch(e){console.log(e)}
}

function populateOpenPositions(){
	$("#openPositions tbody").empty();
	
	fetchOpenPositions().then(result => {
		let openPositionsJsonArr = result;	
		//console.log(openPositionsJsonArr)
		const positionRecords = []
		for( openPositionIndex in openPositionsJsonArr){
			
			action = openPositionsJsonArr[openPositionIndex]["action"]
			if(action == "NA")
				continue;
			
			quantity = openPositionsJsonArr[openPositionIndex]["quantity"]
			price = openPositionsJsonArr[openPositionIndex]["average_price"]
			
			//stock name
			product = openPositionsJsonArr[openPositionIndex]["product_type"].toLowerCase()
			if(product=="options"){fnotype="OPT"}
			if(product=="futures"){fnotype="FUT"}
			
			stockCode = openPositionsJsonArr[openPositionIndex]["stock_code"]
			expiry = openPositionsJsonArr[openPositionIndex]["expiry_date"]
			strike = openPositionsJsonArr[openPositionIndex]["strike_price"]
			exchangecode = openPositionsJsonArr[openPositionIndex]["exchange_code"]
			right = openPositionsJsonArr[openPositionIndex]["right"]
			if(right == "Call"){rightShort = "CE"} else if(right=="Put"){rightShort="PE"}
			
			stockName = fnotype+'-'+stockCode+'-'+expiry
			if(product == "options")
				stockName = stockName + '-'+strike+'-'+rightShort
	
			//console.log(stockName)
			let hiddenDivObj = document.createElement("div");
			hiddenDivObj.setAttribute("id","op-"+stockName)
			hiddenDivObj.setAttribute("data-stockcode",stockCode)
			hiddenDivObj.setAttribute("data-code",stockName)
			hiddenDivObj.setAttribute("data-expiry",expiry)
			hiddenDivObj.setAttribute("data-strike",strike)
			hiddenDivObj.setAttribute("data-right",rightShort)
			hiddenDivObj.setAttribute("data-fnotype",fnotype)
			hiddenDivObj.setAttribute("data-product",product)
			hiddenDivObj.setAttribute("data-exchangecode",exchangecode)

			


			
			//let stockTokenDict = fetchStockToken(stockCode,exchangecode,product,expiry,strike,right);
			//const token = stockTokenDict["quotesToken"].split("!")[1]
			//console.log("token for openposition: "+token)
			//hiddenDivObj.setAttribute("data-token",token)
			
			positionRecords[openPositionIndex] = makePositionRecord(hiddenDivObj,stockName,action,quantity,price);

			
			const opRecord = positionRecords[openPositionIndex];
			const hiddenId = "op-"+stockName
			fetchStockToken(stockCode,exchangecode,product,expiry,strike,right)
				.then(result => {
					let token = result
					//console.log("token for orderlist: "+token)
					$('#'+hiddenId)[0].dataset['token'] = token
					//console.log($('#'+hiddenId))
					//console.log(opRecord)
					
					var ltpDiv = document.createElement('div');
					ltpDiv.id = token + '-price'
					ltpDiv.setAttribute("priceType",hiddenId)
					ltpDiv.innerHTML = "0.00"
					//console.log(ltpDiv.outerHTML)

					opRecord.hiddenColumn=$('#'+hiddenId)[0].outerHTML;
					opRecord.ltp=ltpDiv.outerHTML;
					openPositionsTable.dom.update();
					
					console.log("subscribing to token:"+token)
					subscribeApiTickData(token, apiLtpListener)
				});
			
			//console.log("subscribing to token:"+token)
			//socket.emit('subscribeQuotes', token, "1second")
			//socket.on(token+"-1second", apiLtpListener);
			//subscribeApiTickData(token, apiLtpListener)
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
		//console.log("attaching")
		//const currentDate = new Date(); const milliseconds = currentDate. getMilliseconds(); console. log(milliseconds); 
		setTimeout(attachLtpObservers,3000);
	});
		
}

function populateWatchList(){
	//console.log(localStorage.length)
	for(i = 0;i<localStorage.length;i++){
		let key = localStorage.key(i);
		//console.log(key)
		if (key.includes("wl-")){
			
			let wl = localStorage.getItem(key);
			//console.log("fetched from local storage:"+wl)
			let wlObj = JSON.parse(wl)
			//console.log(wlObj)
			let hiddenDivObj = new DOMParser().parseFromString(wlObj.hiddenDivObj, 'text/html').querySelector("div");
			//console.log(hiddenDivObj)
			//console.log(hiddenDivObj.outerHTML)
			addToWatchList(wlObj.hiddenDivId,hiddenDivObj,wlObj.token,wlObj.stockName)
		}
	}
}

function subscribeApiTickData(token, callback){
	socket.emit('subscribeQuotes', token, "1second")
	socket.on(token+"-1second", callback);
	
}

function unsubscribeApiTickData(token, interval){
	socket.emit('unsubscribeQuotes', token, '1second')
}



function ltpUpdateListener(ohlcvData){
	//ohlcvDataDict = parseTicks(ohlcvData);
	ohlcvDataDict = JSON.parse(ohlcvData);
	let mytoken = ohlcvDataDict["token"]
	selectorStr = '[id='+mytoken+'-price]'
	ltpElemArr = $(selectorStr);
	for(elementIndex in ltpElemArr){
		ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
	}
}

function apiLtpListener(ohlcvData){
	ohlcvDataDict = JSON.parse(ohlcvData);
	let mytoken = ohlcvDataDict["token"]
	selectorStr = '[id='+mytoken+'-price]'
	ltpElemArr = $(selectorStr);
	for(elementIndex in ltpElemArr){
		ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
	}
}

function populateOrderList(){
	$("#orderList tbody").empty();
	let orderDate = moment().format("DD-MM-YYYY");
	//orderDate = '08-12-2023'
	fetchOrderList(orderDate).then(result => {
		let orderListJsonArr = result;	
		//console.log(orderListJsonArr)
		const orderRecords = []
		for( orderIndex in orderListJsonArr){
			orderId = orderListJsonArr[orderIndex]["order_id"]
			orderTime = moment(orderListJsonArr[orderIndex]["order_datetime"],"DD-MMM-YYYY HH:mm:ss").format("HH:mm:ss")
			quantity = orderListJsonArr[orderIndex]["quantity"]
			price = orderListJsonArr[orderIndex]["price"]
			status = orderListJsonArr[orderIndex]["status"]
			if(status=="Executed")
				price = orderListJsonArr[orderIndex]["average_price"]
			action = orderListJsonArr[orderIndex]["action"]
			orderType = orderListJsonArr[orderIndex]["order_type"]
			pendingQuantity = orderListJsonArr[orderIndex]["pending_quantity"]
			//stock name
			product = orderListJsonArr[orderIndex]["product_type"].toLowerCase()
			if(product=="options"){fnotype="OPT"}
			if(product=="futures"){fnotype="FUT"}
			stockCode = orderListJsonArr[orderIndex]["stock_code"]
			expiry = orderListJsonArr[orderIndex]["expiry_date"]
			strike = orderListJsonArr[orderIndex]["strike_price"]
			exchangecode = orderListJsonArr[orderIndex]["exchange_code"]
			stoploss = orderListJsonArr[orderIndex]["stoploss"]
			right = orderListJsonArr[orderIndex]["right"]
			if(right == "Call"){right = "CE"} else if(right=="Put"){right="PE"}
										  
			stockName = fnotype+'-'+stockCode+'-'+expiry
			if(product == "options")
				stockName = stockName + '-'+strike+'-'+right
			//console.log(stockName)
			var hiddenDivObj = document.createElement("div");
			hiddenDivObj.setAttribute("id","ol-"+orderId)
			hiddenDivObj.setAttribute("orderId",orderId)
			hiddenDivObj.setAttribute("data-stockcode",stockCode)
			hiddenDivObj.setAttribute("data-code",stockName)
			hiddenDivObj.setAttribute("data-expiry",expiry)
			hiddenDivObj.setAttribute("data-strike",strike)
			hiddenDivObj.setAttribute("data-right",right)
			hiddenDivObj.setAttribute("data-fnotype",fnotype)
			hiddenDivObj.setAttribute("data-product",product)
			hiddenDivObj.setAttribute("data-exchangecode",exchangecode)

			
			orderRecords[orderIndex] =  makeOrderRecord(hiddenDivObj,orderId,orderTime,stockName,action,quantity,price,stoploss,orderType,status);
			//console.log(orderRecords[orderIndex].id)
		}
		
		obj = new Object();
		obj.records = orderRecords;
		if(orderListJsonArr != null){
			obj.queryRecordCount = orderListJsonArr.length;
			obj.totalRecordCount = orderListJsonArr.length;
		}
		var orderListTable = $('#orderList').data('dynatable');
		orderListTable.records.updateFromJson(obj)
		orderListTable.dom.update();
	});
}


function modifyOrder(){
	//validate order related data
	hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		console.log("hiddenDataColumnId is empty. Do not have data to place order.")
		captionObj = $(".orderMessages")
		captionObj.html("Select stock from watchlist to place order.")
		return
	}
	//clear order messages
	$(".orderMessages").html("processing modify order...")
	
	hiddenDivObj = $("#"+hiddenDivId)[0]
	var hiddenOlDivObj = null;
	var hiddenOrderId = $("#hiddenOrderId")[0].innerText
	hiddenOlDivId = "ol-"+hiddenOrderId
	hiddenOlDivObj = $("#"+hiddenOlDivId)[0]
	var stockName = $('#orderStock')[0].innerText;
	var quantity = $('#orderQty')[0].value;
	var action = $('#orderAction')[0].innerText;;
	var price = $('#orderPrice')[0].value;
	var stoploss = $('#orderSl')[0].value;
	var orderId = moment().format("DDMMYYYYHHmmss")
	orderId = hiddenOrderId
	orderStatus = $('#status-'+orderId)[0].innerText;
	if(orderStatus.toLowerCase() != "ordered" && orderStatus.toLowerCase() != "requested"){
		clearOrder()
		return;
	}
	var exchangeCode = hiddenOlDivObj.dataset.exchangecode

	var orderResultJsonArr = null
	orderResultJsonArr = sendModifyOrder(orderId,exchangeCode,price,quantity,stoploss
		).then(result => {
			orderResultJsonArr = result
			errorStatus = orderResultJsonArr["Error"]
			captionObj = $(".orderMessages")
			if(errorStatus != null && errorStatus != ""){
				captionObj.html(errorStatus)
				return;
			}
			else{
				captionObj.html(orderResultJsonArr["Success"]["message"])
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
			
			//orderTime = moment().format("DD-MMM-YYYY HH:mm:ss")
			orderTime = moment().format("HH:mm:ss")
			orderType = "limit"
			if (price == 0)
				orderType = "market"
			
			
			myRecords[recordIndex] = makeOrderRecord(hiddenOlDivObj,orderId,orderTime,stockName,action,quantity,price,stoploss,orderType,orderStatus);
			
			obj = new Object();
			obj.records = myRecords;
			obj.queryRecordCount = existingRecords.length;
			obj.totalRecordCount = existingRecords.length;
			orderListTable.records.updateFromJson(obj)
			orderListTable.dom.update();

			//reset
			//sticky modify window
			//clearOrder()
			}
		)
}

function addOrder(newOrSquareoff){
	
	//validate order related data
	hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		console.log("hiddenDataColumnId is empty. Do not have data to place order.")
		captionObj = $(".orderMessages")
		captionObj.html("Select stock from watchlist to place order.")
		return
	}
	
	hiddenDivObj = $("#"+hiddenDivId)[0];
	hiddenDivObj = $(hiddenDivObj).clone()[0];

	var hiddenOlDivObj = null;
	var hiddenOrderId = $("#hiddenOrderId")[0].innerText
	
	var stockName = $('#orderStock')[0].innerText;
	var quantity = $('#orderQty')[0].value;
	var action = $('#orderAction')[0].innerText;;
	var price = $('#orderPrice')[0].value;
	var stoploss = $('#orderSl')[0].value;

	//reset immediately after reading values to avoid duplicate orders
	clearOrder()
	captionObj = $(".orderMessages")
	captionObj.html("processing add new order...")
	
	var orderId = moment().format("DDMMYYYYHHmmss")
	
	//call api to place order and fetch order id
	//new order

	newOrderStockCode = hiddenDivObj.dataset.stockcode
	newOrderExchangeCode = hiddenDivObj.dataset.exchangecode
	newOrderProduct = hiddenDivObj.dataset.product
	newOrderStrike = hiddenDivObj.dataset.strike
	newOrderExpiryDate = hiddenDivObj.dataset.expiry
	newOrderAction = action
	newOrderRightType = hiddenDivObj.dataset.right
	newOrderPrice = price
	newOrderQuantity = quantity
	newOrderStoploss = stoploss

	instruIds = {}

	for( var data in hiddenDivObj.dataset)
		if(data.includes("_id"))
			instruIds[data] = hiddenDivObj.dataset[data]

	//console.log("InstruIds added are")
	//console.log(instruIds)

	var orderResultJsonArr = null
	if(newOrSquareoff == "squareoff"){
		orderResultJsonArr = sendSquareOffOrder(newOrderStockCode,newOrderExchangeCode,newOrderProduct,
			newOrderStrike,newOrderExpiryDate,newOrderAction,newOrderRightType,
			newOrderPrice,newOrderQuantity,newOrderStoploss
		).then(result => {
			orderResultJsonArr = result
			errorStatus = orderResultJsonArr["Error"]
			if(errorStatus != null && errorStatus != ""){
				console.log("orderResultJsonArr:" + orderResultJsonArr)
				captionObj.html(errorStatus)
				clearOrder()
				return;
			}
			else{
				captionObj.html(orderResultJsonArr["Success"]["message"])
			}
		
			orderId = orderResultJsonArr["Success"]["order_id"]
			orderStatus = "Ordered"	
		
			hiddenOlDivObj = $(hiddenDivObj).clone()[0];
			hiddenOlDivObj.setAttribute('id','ol-' + orderId)
			//hardcoding fetch orderid from json response to place order
			hiddenOlDivObj.setAttribute('orderId',orderId)
			//orderTime = moment().format("DD-MMM-YYYY HH:mm:ss")
			orderTime = moment().format("HH:mm:ss")
			orderType = "limit"
			if (price == 0)
				orderType = "market"
			newRecord = makeOrderRecord(hiddenOlDivObj,orderId,orderTime,stockName,action,quantity,price,stoploss,orderType,orderStatus);
			refreshOrderListTable(newRecord)
		} )
	}
	else{
		sendPlaceOrder(newOrderStockCode,newOrderExchangeCode,newOrderProduct,
			newOrderStrike,newOrderExpiryDate,newOrderAction,newOrderRightType,
			newOrderPrice,newOrderQuantity,newOrderStoploss,instruIds
		).then(result => {
			orderResultJsonArr = result
			errorStatus = orderResultJsonArr["Error"]
			if(errorStatus != null && errorStatus != ""){
				console.log("orderResultJsonArr:" + orderResultJsonArr)
				captionObj.html(errorStatus)
				clearOrder()
				return;
			}
			else{
				captionObj.html(orderResultJsonArr["Success"]["message"])
			}
		
			orderId = orderResultJsonArr["Success"]["order_id"]
			orderStatus = "Ordered"	
		
			hiddenOlDivObj = $(hiddenDivObj).clone()[0];
			hiddenOlDivObj.setAttribute('id','ol-' + orderId)
			//hardcoding fetch orderid from json response to place order
			hiddenOlDivObj.setAttribute('orderId',orderId)
			//orderTime = moment().format("DD-MMM-YYYY HH:mm:ss")
			orderTime = moment().format("HH:mm:ss")
			orderType = "limit"
			if (price == 0)
				orderType = "market"
			newRecord = makeOrderRecord(hiddenOlDivObj,orderId,orderTime,stockName,action,quantity,price,stoploss,orderType,orderStatus);
			refreshOrderListTable(newRecord)
		} )
	}
	

	//myRecords = myRecords.concat(existingRecords);
	
	//obj = new Object();
	//obj.records = myRecords;
	//obj.queryRecordCount = existingRecords.length + 1;
	//obj.totalRecordCount = existingRecords.length + 1;
	//orderListTable.records.updateFromJson(obj)
	//orderListTable.dom.update();
}

function refreshOrderListTable(newRecord){

	var orderListTable = $('#orderList').data('dynatable');
	var existingRecords = orderListTable.records.getFromTable()
	
	var myRecords = null;
	var recordIndex = 0;

	myRecords = [new Object()];
	myRecords[recordIndex] = newRecord
	myRecords = myRecords.concat(existingRecords);
	
	obj = new Object();
	obj.records = myRecords;
	obj.queryRecordCount = existingRecords.length + 1;
	obj.totalRecordCount = existingRecords.length + 1;
	orderListTable.records.updateFromJson(obj)
	orderListTable.dom.update();
}


function cancelOrder(cancelOrderId){
	var captionObj = $(".orderMessages")
	var orderStatus = $("#status-"+cancelOrderId)[0]
	if(orderStatus.innerText.toLowerCase() == "cancelled")	{
		captionObj.html("Order is already cancelled:"+cancelOrderId)
		orderStatus.parentNode.nextSibling.innerHTML=""
		return
	}
		
	sendCancelOrder(cancelOrderId).then(result => {		
		let orderResultJsonArr = result
		errorStatus = orderResultJsonArr["Error"]
		if(errorStatus != null && errorStatus != ""){		
			captionObj.html(errorStatus)
		}else{
			captionObj.html(orderResultJsonArr["Success"]["message"])
			cancelTdObj = orderStatus.parentNode.nextSibling
			modifyTdObj = cancelTdObj.nextSibling
			cancelTdObj.innerHTML=""
			modifyTdObj.innerHTML=""			
		}
	});
}
function populateModifyOrder(modifyButtonObj,action,qty,price,sl){
	trObj = $(modifyButtonObj).closest("tr")[0]
	hiddenDivObj = trObj.firstChild.firstChild
	modifyOrderId = hiddenDivObj.getAttribute('orderid')
	let bgColor = "red"
	if(action.toLowerCase()=="buy"){
		bgColor="#85EA27"
	}
	$(".order-ltp").attr("id",hiddenDivObj.dataset.token + '-price')
	$('#hiddenOrderId').text(modifyOrderId);
	$('#hiddenDataColumnId').text(hiddenDivObj.getAttribute("id"));
	$('#orderStock').text(hiddenDivObj.dataset.code);
	$('#orderAction').text(action);
	$('#orderAction').closest("td").css("background-color",bgColor);
	$('#orderQty')[0].valueAsNumber = qty;
	$('#orderPrice')[0].valueAsNumber = price;
	$('#orderSl')[0].valueAsNumber = sl;
	$('#orderButton')[0].value="Modify"
	$('#orderButton')[0].onclick=modifyOrder
	$('#orderButton').css("background-color",bgColor);
	$('#orderButton').css("color","white");
	$('#order_popup').dialog('open')
	
}
function clearOrder(){
	$("#hiddenOrderId").text("")
	$("#hiddenDataColumnId").text("")
	$('#orderStock').text("")
	$('#orderAction').text("")
	$('#orderQty')[0].valueAsNumber = 1;
	$('#orderPrice')[0].valueAsNumber = 0;
	$('#orderSl')[0].valueAsNumber = 0;
	$('#orderButton')[0].value="Order"
	$("#orderAction").closest("td").css("background-color","")
	$('#orderButton').css("background-color","");
	$('#orderButton').css("color","white");
	try{
		$(".order-ltp").text("")
		$(".order-ltp").attr("id","")
		$('#margin')[0].innerHTML = "0.00"
		$('#charges')[0].innerHTML = "0.00"
		$('#charges_content #total_brokerage')[0].innerHTML = "0.00"
		$('#charges_content #brokerage')[0].innerHTML = "0.00"
		$('#charges_content #stamp_duty')[0].innerHTML = "0.00"
		$('#charges_content #stt')[0].innerHTML = "0.00"
		$('#charges_content #gst')[0].innerHTML = "0.00"
		$('#charges_content #exchange_turnover_charges')[0].innerHTML = "0.00"
		$('#charges_content #sebi_charges')[0].innerHTML = "0.00"
		$('.tooltip').tooltipster('content',$('#charges_content')[0].innerHTML)
	}catch(e){console.log(e)}
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
			try{
		  		hiddenDivObj = col.firstChild
				token = hiddenDivObj.dataset.token
				console.log("unsubscribe token: "+token)
				unsubscribeApiTickData(token,"1second")
				//console.log(response)
				break;
			}catch(e){console.log(e)}			
		}  
	}
	var watchListTable = $('#watchList').data('dynatable');
	obj = new Object();
	obj.records = [];
	obj.queryRecordCount = 0;
	obj.totalRecordCount = 0;
	watchListTable.records.updateFromJson(obj)
	watchListTable.dom.update();
	//$("#watchList tbody").empty();
}


			
function getWatchListStocks(){
	let searchStr = $('#searchStock')[0].value
	let searchStockTypeStr = $('#searchStockType').val()
	localStorage.setItem("searchStr", searchStr);
	//fetchStocks(searchStr).then( fnOJsonArr => {
	let finalSearchStr = searchStockTypeStr + ' ' + searchStr
	fetchDPStocks('False',finalSearchStr).then( fnOJsonArr => {
		//console.log(fnOJsonArr)
		$("#stock-selection").empty()
		fnOJsonArr.forEach(function(eachStock) { 
			let optionObj = $('<option/>')
			for (const [key, value] of Object.entries(eachStock)) {	
				optionObj.attr("data-"+key,value)
				//console.log(key, value);
			}
			optionObj.attr("value",eachStock.token).text(eachStock.code).appendTo('#stock-selection');
		});
	});
}

function makeWatchListRecord(hiddenDivId,hiddenDivObj,token,stockName){
	buyAction = `<img width='40' height='25' src="/static/images/buy1.png" alt="Buy" onClick='buyStock("${stockName}","${hiddenDivId}")'/> `
	sellAction = `<img width='40' height='25' src="/static/images/sell1.png" alt="Sell" onClick='sellStock("${stockName}","${hiddenDivId}")'/> `
	remove = "<img width='20' height='18' src='/static/images/bin.png' alt='Remove' onClick='removeFromWatchList(this)'/>"
	
	var showChart = "&nbsp;<img onClick='loadOptionsData(\""+hiddenDivId+"\")' src='/static/images/chart.png' width='18' height='18' alt='Show Chart' style='display:inline'>"
	var showMarketDepth = `&nbsp;<img  style='display:inline' onClick='showMarketDepth("${hiddenDivId}")' src='/static/images/bidask.png' width='18' height='18' alt='Show Market Depth' />`
	var marketDepthTable = `<div id='marketDepth-${hiddenDivId}'></div>`
	
	wlRecord = new Object();
	wlRecord.hiddenColumn=hiddenDivObj.outerHTML
	wlRecord.stock=stockName + showMarketDepth + showChart + marketDepthTable
	wlRecord.price = "<div id='"+token+"-price'></div>"
	wlRecord.action = buyAction + sellAction
	wlRecord.x = remove
	return wlRecord
}
function watchStock(){
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
	addToWatchList(hiddenDivId,hiddenDivObj,token,stockName)
	
	//add to localstorage
	watchListObj = new Object();
	watchListObj.hiddenDivId = hiddenDivId
	watchListObj.token = token
	watchListObj.stockName = stockName
	watchListObj.hiddenDivObj = hiddenDivObj.outerHTML
	wlKey = "wl-" + token
	localStorage.setItem(wlKey, JSON.stringify(watchListObj));
}
function addToWatchList(hiddenDivId,hiddenDivObj,token,stockName) {
	var watchListTable = $('#watchList').data('dynatable');
	
	wlRecord = makeWatchListRecord(hiddenDivId,hiddenDivObj,token,stockName)
	myRecords = [new Object()];
	myRecords[0] = wlRecord

	/*buyAction = `<img width='40' height='25' src="/static/images/buy1.png" alt="Buy" onClick='buyStock("${stockName}","${hiddenDivId}")'/> `
	sellAction = `<img width='40' height='25' src="/static/images/sell1.png" alt="Sell" onClick='sellStock("${stockName}","${hiddenDivId}")'/> `
	remove = "<img width='20' height='18' src='/static/images/bin.png' alt='Remove' onClick='removeFromWatchList(this)'/>"
	
	var showChart = "&nbsp;<img onClick='loadOptionsData(\""+hiddenDivId+"\")' src='/static/images/chart.png' width='18' height='18' alt='Show Chart' style='display:inline'>"
	
	var showMarketDepth = `&nbsp;<img  style='display:inline' onClick='showMarketDepth("${hiddenDivId}")' src='/static/images/bidask.png' width='18' height='18' alt='Show Market Depth' />`
	
	var marketDepthTable = `<div id='marketDepth-${hiddenDivId}'></div>`
	myRecords = [new Object()];
	myRecords[0].hiddenColumn=hiddenDivObj.outerHTML
	myRecords[0].stock=stockName + showMarketDepth + showChart + marketDepthTable
	myRecords[0].price = "<div id='"+token+"-price'></div>"
	myRecords[0].action = buyAction + sellAction
	myRecords[0].x = remove	
	*/
	
	existingRecords = watchListTable.records.getFromTable()
	myRecords = myRecords.concat(existingRecords);
	obj = new Object();
	obj.records = myRecords;
	obj.queryRecordCount = existingRecords.length + 1;
	obj.totalRecordCount = existingRecords.length + 1;

	watchListTable.records.updateFromJson(obj);
	watchListTable.dom.update();
	
	//const inputToken = token
	//subscribeQuotesFeed(inputToken)
	subscribeApiTickData(token,apiLtpListener)
	
}

function removeFromWatchList(removeButtonObj) {
	trObj = $(removeButtonObj).closest("tr")[0]
	hiddenDivObj = trObj.firstChild.firstChild
	token = hiddenDivObj.getAttribute('data-token')
	ltpElemArr = $('#'+token+'-price');
	if(ltpElemArr.length < 2)
		unsubscribeApiTickData(token, "1second")
	$(removeButtonObj).closest("tr").remove();
	localStorage.removeItem("wl-"+token)
}
function buyStock(stockToBuy,hiddenDivId){
	clearOrder()
	$("#orderStock").text(stockToBuy)
	$("#orderAction").text("Buy")
	//bgColor = "#85EA27"
	bgColor = "#04AA6D"
	$("#orderAction").closest("td").css("background-color",bgColor)
	//$("#orderAction").css("color","green")
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="Buy"
	let token = $('#'+hiddenDivId).get()[0].dataset.token
	//console.log($('#'+token+'-price'))
	let ltp = $('#'+token+'-price')[0].innerText
	if($("input:radio[name='orderType']:checked").first().val()=="market"){
		ltp = "0"
	}
	//console.log($(".order-ltp"))
	$(".order-ltp").attr("id",token + '-price')
	$("#orderPrice")[0].value = ltp
	let lotsize = $('#'+hiddenDivId).get()[0].dataset.lotsize;
	$("#orderQty")[0].valueAsNumber = lotsize
	$("#orderQty")[0].step = lotsize;
	$("#orderQty")[0].min = lotsize;
	$('#orderButton')[0].onclick=function() { addOrder('new') }
	$('#orderButton').css("background-color",bgColor);
	$('#orderButton').css("color","white");
	getBrokerages();
	calculateMargin();
	$('#order_popup').dialog('open')
}

//adjust this function to call squareoff api
function squareoffStock(stockToSell,hiddenDivId,qty){
	clearOrder()
	$("#orderStock")[0].innerText = stockToSell
	$("#orderAction")[0].innerText = "Sell"
	$("#orderQty")[0].valueAsNumber = qty;
	bgColor = "red"
	$("#orderAction").closest("td").css("background-color",bgColor)
	//$($("#orderAction")[0]).css("color","red")
	let token = $('#'+hiddenDivId).get()[0].dataset.token
	let ltp = $('#'+token+'-price')[0].innerText
	if($("input:radio[name='orderType']:checked").first().val()=="market"){
		ltp = "0"
	}
	$(".order-ltp").attr("id",token + '-price')
	$("#orderPrice")[0].value = ltp
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="squareoff"
	$('#orderButton')[0].onclick=function(){addOrder('squareoff')}
	$('#orderButton').css("background-color",bgColor);
	$('#orderButton').css("color","white");
	getBrokerages();
	calculateMargin();
	$('#order_popup').dialog('open')
}

function sellStock(stockToSell,hiddenDivId){
	clearOrder()
	$("#orderStock")[0].innerText = stockToSell
	$("#orderAction")[0].innerText = "Sell"
	bgColor = "red"
	$("#orderAction").closest("td").css("background-color",bgColor)
	//$($("#orderAction")[0]).css("color","red")
	$("#hiddenDataColumnId")[0].innerText = hiddenDivId
	$('#orderButton')[0].value="Sell"
	let token = $('#'+hiddenDivId).get()[0].dataset.token
	let ltp = $('#'+token+'-price')[0].innerText
	if($("input:radio[name='orderType']:checked").first().val()=="market"){
		ltp = "0"
	}
	$(".order-ltp").attr("id",token + '-price')
	$("#orderPrice")[0].value = ltp
	let lotsize = $('#'+hiddenDivId).get()[0].dataset.lotsize;
	$("#orderQty")[0].valueAsNumber = lotsize
	$("#orderQty")[0].step = lotsize;
	$("#orderQty")[0].min = lotsize;
	$('#orderButton')[0].onclick=function() { addOrder('new')}
	$('#orderButton').css("background-color",bgColor);
	$('#orderButton').css("color","white");
	getBrokerages();
	calculateMargin();
	$('#order_popup').dialog('open')
}

/*
function subscribeQuotesFeed(token){
	//console.log("subscribing to quotes feed for token: "+token)
	//response = socket.emit('subscribeQuotes', token, "1second")
	//console.log(response)

	const inputToken = token
	socket.on(inputToken+'-1second', function (ohlcvData){
		ohlcvDataDict = JSON.parse(ohlcvData);
		selectorStr = '[id="'+inputToken+'-price"]'
		ltpElemArr = $(selectorStr);
		for(elementIndex in ltpElemArr){
			ltpElemArr[elementIndex].innerHTML = ohlcvDataDict["close"]
		}
	});
	
	//subscribeApiTickData(token,apiLtpListener)
	
}
*/



function orderNotification(notificationData){
	notificationDataDict = JSON.parse(notificationData);
	//console.log("orderNotification-->" + notificationData)
	//$('#output')[0].innerHTML = "<pre>"+new Date().toLocaleString()+" : " + notificationDataDict + "</pre>"
	orderId = notificationDataDict["orderReference"];
	orderStatus = notificationDataDict["orderStatus"];
	stockCode = notificationDataDict["stockCode"];
	//console.log("order notification: "+orderId+"-->"+orderStatus)
	const options = {
    //body: orderId + " " + orderStatus,
    body: "",
    icon: "/static/images/alert.jpg",
  };
  new Notification(stockCode + " " + orderStatus, options);
	//update status
	$('#status-'+orderId)[0].innerText = orderStatus
	if(orderStatus.toLowerCase() == "executed"){
		try{
			$('#cancelOrdBtn-'+orderId)[0].remove();
			$('#modifyOrdBtn-'+orderId)[0].remove();
		}catch(e){}
		//$('#price-'+orderId)[0].innerText = orderStatus
		refreshOpenPositions();
	}
	refreshMargins();
	//$('#price-'+orderId)[0].innerText = orderStatus
}



function populateRealisedPnl(){
	let fromDateStr = $($("#fromDatepicker")).val()
	let toDateStr = $($("#toDatepicker")).val()
	
	fetchRealisedPnl(fromDateStr,toDateStr).then(result => {
		let pnlResultJsonArr = result
		//console.log(pnlResultJsonArr)
		if(pnlResultJsonArr == null){
			realisedPnl = "0.00";
			realisedPnlWithTaxes = "0.00";
		}
		else{
			realisedPnl = pnlResultJsonArr["realised_pnl"]
			realisedPnlWithTaxes = pnlResultJsonArr["realised_pnl_with_taxes"]
		}
	
		$("#realisedPnl")[0].innerHTML=realisedPnl;
		$("#realisedPnlWithTaxes")[0].innerHTML=realisedPnlWithTaxes;
	});
}

function refreshMargins(){
	fetchMargins().then(result => {
			let marginResultJsonArr=result
			//console.log(marginResultJsonArr)
			if(marginResultJsonArr != null){
				allocatedMargin = marginResultJsonArr["amount_allocated"]
				availableMargin = marginResultJsonArr["cash_limit"]
				mtm = "0.00"
				if ($.isArray(marginResultJsonArr["limit_list"]) &&  marginResultJsonArr["limit_list"].length>0){
					mtm = marginResultJsonArr["limit_list"][0]["amount"]
				}
			}else{
                allocatedMargin = 0
                availableMargin = 0
                mtm=0;
            }
			$("#allocatedMargin")[0].innerHTML=allocatedMargin;
			$("#availableMargin")[0].innerHTML=availableMargin;
			$("#mtm")[0].innerHTML=mtm;
	});
}

function hideMarketDepth(){
	//alert("hiding MD")
	let MDTableDivArr = $("[id^='marketDepth']").get()
	for(elementIndex in MDTableDivArr){
		let MDTableDiv = MDTableDivArr[elementIndex]
		let hiddenDivId = (MDTableDiv.id).split(/-(.*)/s)[1]
		let hiddenDivObj = $("#"+hiddenDivId)[0]
		if(MDTableDiv.innerHTML != ""){
			MDTableDiv.innerHTML = ""
			console.log("unsubscribing market depth for token:"+hiddenDivObj.dataset.token)
			unsubscribeMarketDepth(hiddenDivObj.dataset.token)
		}
	}
}

function showMarketDepth(hiddenDivId){
	MDTableDiv = $("#marketDepth-"+hiddenDivId)[0]
	hiddenDivObj = $("#"+hiddenDivId)[0]
	if(MDTableDiv.innerHTML != ""){
		MDTableDiv.innerHTML = ""
		console.log("unsubscribing market depth for token:"+hiddenDivObj.dataset.token)
		unsubscribeMarketDepth(hiddenDivObj.dataset.token)
		return;
	}
	MDTableStart = `<table class="marketDepth" id='MD-${hiddenDivObj.dataset.token}' width='100%'><thead><tr><th>Bid</th><th>Orders</th><th>Qty</th><th>Ask</th><th>Orders</th><th>Qty</th></tr></thead><tbody>`
	MDTableEnd = "</tbody></table>"
	MDTableDiv.innerHTML=MDTableStart+MDTableEnd
	console.log('calling to subscribe MD:'+hiddenDivObj.dataset.token)
	subscribeMarketDepth(hiddenDivObj.dataset.token)
}

function subscribeMarketDepth(token){
	//alert("subscribing to quotes feed for token: "+token)
	response = socket.emit('subscribeMarketDepth', token)
	console.log('subscribing MD:'+token)
	const inputToken = token
	socket.on(inputToken, function (mdData){
		//console.log(mdData)
		mdDataDict = JSON.parse(mdData);
		mdDataDict = mdDataDict["depth"]
		//console.log(mdDataDict)
		var mdTBody = $("#MD-"+inputToken+" tbody")
		mdTBody.empty();
		row = ""
		for (i=0;i<5;i++){
			//console.log(mdDataDict[i])
			j = i+1;
			row = row+`<tr><td>${mdDataDict[i]["BestBuyRate-"+j]}</td><td>${mdDataDict[i]["BuyNoOfOrders-"+j]}</td><td>${mdDataDict[i]["BestBuyQty-"+j]}</td><td>${mdDataDict[i]["BestSellRate-"+j]}</td><td>${mdDataDict[i]["SellNoOfOrders-"+j]}</td><td>${mdDataDict[i]["BestSellQty-"+j]}</td></tr>`
			
		}
		//console.log(row)
		mdTBody.append(row)	
		
	});
	
}

function unsubscribeMarketDepth(token){
	//alert("subscribing to quotes feed for token: "+token)
	response = socket.emit('unsubscribeMarketDepth', this.token)
}

function handleOrderTypeChange(obj){
	if(obj.value=="market"){
		$("#orderPrice")[0].valueAsNumber=0;
		$("#orderSl")[0].valueAsNumber=0;
		$("#orderPrice").attr("readonly",true)
		$("#orderSl").attr("readonly",true)
	}else if(obj.value=="limit"){
		$("#orderSl")[0].valueAsNumber=0;
		$("#orderPrice").attr("readonly",false)
		$("#orderSl").attr("readonly",true)
	}
	else if(obj.value=="stoploss"){
		$("#orderSl")[0].valueAsNumber=0;
		$("#orderPrice").attr("readonly",false)
		$("#orderSl").attr("readonly",false)
	}
}

function refreshMarginAndCharges(){
	calculateMargin()
	getBrokerages()
}

function getBrokerages(){
	//validate order related data
	let hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		return
	}
	hiddenDivObj = $("#"+hiddenDivId)[0];
	
	let quantity = $('#orderQty')[0].value;
	let action = $('#orderAction')[0].innerText.toLowerCase();
	let price = $('#orderPrice')[0].value;
	let stoploss = $('#orderSl')[0].value;
	let stockCode = hiddenDivObj.dataset.stockcode;
	let exchangeCode = hiddenDivObj.dataset.exchangecode;
	let product = hiddenDivObj.dataset.product;
	let strike = hiddenDivObj.dataset.strike;
	let expiryDate = hiddenDivObj.dataset.expiry;
	let rightType = hiddenDivObj.dataset.right;
	$('#charges')[0].innerHTML = "..."
	fetchBrokerage(stockCode,exchangeCode,product,strike,expiryDate,action,rightType,price,quantity,stoploss)
		.then(result => {
			let brokerageDict=result;
			if(brokerageDict == null){
				$('#charges')[0].innerHTML = "0.00"
				return;
			}
				
			$('#charges')[0].innerHTML = brokerageDict["total_brokerage"]
			$('#charges_content #total_brokerage')[0].innerHTML = brokerageDict["total_brokerage"]
			$('#charges_content #brokerage')[0].innerHTML = brokerageDict["brokerage"]
			$('#charges_content #stamp_duty')[0].innerHTML = brokerageDict["stamp_duty"]
			$('#charges_content #stt')[0].innerHTML = brokerageDict["stt"]
			$('#charges_content #gst')[0].innerHTML = brokerageDict["gst"]
			$('#charges_content #exchange_turnover_charges')[0].innerHTML = brokerageDict["exchange_turnover_charges"]
			$('#charges_content #sebi_charges')[0].innerHTML = brokerageDict["sebi_charges"]
			$('.tooltip').tooltipster('content',$('#charges_content')[0].innerHTML)
		});
}

function calculateMargin(){
		//validate order related data
	let hiddenDivId = $("#hiddenDataColumnId")[0].innerText
	if(hiddenDivId == ""){
		return
	}
	hiddenDivObj = $("#"+hiddenDivId)[0];
	
	let quantity = $('#orderQty')[0].value;
	let action = $('#orderAction')[0].innerText.toLowerCase();
	let price = $('#orderPrice')[0].value;
	let stoploss = $('#orderSl')[0].value;
	let stockCode = hiddenDivObj.dataset.stockcode;
	let exchangeCode = hiddenDivObj.dataset.exchangecode;
	let product = hiddenDivObj.dataset.product;
	let strike = hiddenDivObj.dataset.strike;
	let expiryDate = hiddenDivObj.dataset.expiry;
	let rightType = hiddenDivObj.dataset.right;
	let includeOpenPositions = $('#includeOpenPositions')[0].checked
	$('#margin')[0].innerHTML = "..."
	fetchMarginCalculation(stockCode,exchangeCode,product,strike,expiryDate,action,rightType,price,quantity,includeOpenPositions)
		.then(result => {
			let marginCalculationDict=result;
			if(marginCalculationDict == null){
				$('#margin')[0].innerHTML = "0.00"
				return;
			}
			//marginCalculationDict = marginCalculationDict['Success']	
			$('#margin')[0].innerHTML = marginCalculationDict["span_margin_required"]
		});
}

//unsed
function processChartSessionKey(data){
	sessionKeyData = JSON.parse(data);
	loginForChartData(sessionKeyData["userid"],sessionKeyData["sessionkey"])
}
