
# A very simple Flask Hello World app for you to get started with...

from flask import Flask, request, redirect, session, jsonify, render_template, send_from_directory, url_for, abort
import os
from flask_cors import CORS, cross_origin
from breeze_connect import BreezeConnect
from datetime import datetime, timezone, timedelta
import glob
import urllib
from flask_socketio import SocketIO, emit, SocketIOTestClient
import time
from breezeapi import breezeapi
from icecream import ic
import json
import pandas as pd
import configapi

app = Flask(__name__)
socketio = SocketIO(app,logger=False, engineio_logger=False)

cors = CORS(app)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['CORS_HEADERS'] = 'Content-Type'

app.api_key = configapi.API_KEY
app.secret_key = configapi.SECRET_KEY
app.login_url = configapi.LOGIN_URL + urllib.parse.quote_plus(app.api_key)

myapi = breezeapi.MyBreezeApi(app.api_key)

#@app.after_request
#def after_request(response):
#    header = response.headers
#    header['Access-Control-Allow-Origin'] = '*'
    # Other headers can be added here if needed
#    return response


@app.route('/manifest.json')
@cross_origin()
def serve_manifest():
	return send_from_directory('static', "manifest.json")

@app.route('/static/<path:path>')
@cross_origin()
def serve_static(path):
	return send_from_directory('static', path)
	

@socketio.event
def subscribeQuotes(token,interval):
	print("Subscribe-->"+token+"-"+interval)
	print(subscribeQuotesFeed(token,interval))
	existingSubs = session.get(request.sid,"")
	newSub = token + '-' + interval
	if(existingSubs != ""):
		newSub = ";"+newSub
	session[request.sid] = existingSubs + newSub

@socketio.event
def unsubscribeQuotes(token,interval):
	print("unsubscribe-->"+token+"-"+interval)
	print(unsubscribeQuotesFeed(token,interval))

@socketio.event
def subscribeMarketDepth(token):
	print("Subscribe MD-->"+token)
	print(subscribeMarketDepth(token))
	existingSubs = session.get("md-"+request.sid,"")
	newSub = token
	if(existingSubs != ""):
		newSub = ";"+newSub
	session["md-"+request.sid] = existingSubs + newSub
	
@socketio.event
def unsubscribeMarketDepth(token):
	print("unsubscribe MD-->"+token)
	print(unsubscribeMarketDepth(token))
	
@socketio.event
def spoofTicks(data,count,interval):
	ic(type(data))
	myapi.spoofTicks(data,count,interval)

@socketio.event
def disconnect():
	try:
		clientSid = request.sid
		clientSubs = session.get(request.sid,"")
		app.logger.info('Client disconnected : '+clientSid)
		app.logger.info("unsubscribing from "+clientSubs)
		subsPair = clientSubs.split(";")
		for subs in subsPair:
			if subs != "":
				tokenIntervalPair = subs.split("-")
				token = tokenIntervalPair[0]
				interval = tokenIntervalPair[1]
				unsubscribeQuotes(token,interval)
		clientMDSubs = session.get("md-"+request.sid,"")
		app.logger.info("unsubscribing md from "+clientMDSubs)
		subsMDPair = clientMDSubs.split(";")
		for subs in subsMDPair:
			print(unsubscribeMarketDepth(subs))
		app.logger.info("disconnect successful")
	except:
		app.logger.error("Exception in disconnect caught successfully")
			
@socketio.on_error_default
def default_error_handler(e):
	app.logger.error("socketio default error handler")
	app.logger.error(e)	
	app.logger.error("event:" + request.event["message"]) # "my error event"
	app.logger.error("event args as below:")
	app.logger.error(request.event["args"])    # (data,)
			
def getApiSessionFromFile():
	apiSession = ""
	file_path = './bzapisessions/*'
	files = sorted(glob.iglob(file_path), key=os.path.getctime, reverse=True)
	if len(files) > 0:
		apiSession = os.path.basename(files[0])
	return apiSession


@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
	print("login to idirect breeze api")
	#redirect_uri = url_for('authorize', _external=True)
	print(app.login_url)
	#return oauth.breezeapi.authorize_redirect(redirect_uri)
	return redirect(app.login_url)

@app.route('/authorize', methods=['GET', 'POST'])
def authorize():
	print("inside authorize")
	'''
	token = oauth.breezeapi.authorize_access_token()
	print("obtained access token:"+str(token))
	print("getting repos")
	resp = oauth.breezeapi.get('/breezeapi/api/v1/customerdetails')
	resp.raise_for_status()
	profile = resp.json()
	# do something with the token and profile
	print("token :"+str(token))
	print("profile :"+str(profile))
	'''
	queryParams = request.args.to_dict()
	apiSession = queryParams.get('apisession','')
	return redirect('/connect?apisession=' + apiSession)
	

@app.route('/connect', methods=['GET', 'POST'])
@cross_origin()
def connectApi():		
	queryParams = request.args.to_dict()
	apiSession = queryParams.get('apisession','no-breezeapi-session')
	userId = ""
	sessionKey = ""
	loginMessage = "Not logged in."
	invalidSessionMsg = ""
	if apiSession == "no-breezeapi-session":
		apiSession = getApiSessionFromFile()
	else:
		try:
			file_path = './bzapisessions/'+apiSession
			# create file
			with open(file_path, 'x') as fp:
				fp.close()
		except Exception as e:
			app.logger.info(e)
			app.logger.info('File already exists')
	
	if apiSession != "no-breezeapi-session":
		try:
			myapi.onMessage = feedData
			myapi.connect(apiSession,app.secret_key)
			session["apisession"] = apiSession
			return redirect("/", code=302)
			loginMessage = getCustomerDetails(apiSession)
			userId = myapi.user_id
			sessionKey = myapi.session_key
		except Exception as e:
			app.logger.error(e)
			invalidSessionMsg = ". Session invalid. Create new session from login url."
	
	loginUrl = "<a href='/login'>Login</a>"
	output = loginUrl +"<br/>Most recent session:"+apiSession+invalidSessionMsg
	return render_template("index.html", output=output, apiSession=apiSession, userId=userId, sessionKey=sessionKey, loginMessage=loginMessage)	


@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def oneClick():
	if not myapi.isConnected:
		return redirect("/connect", code=302)
	apiSession = session.get("apisession","")
	if apiSession == "" or apiSession == "no-breezeapi-session":
		print("api connected but session destroyed/tab closed.")
		print("getting apisession from file")
		apiSession = getApiSessionFromFile()
		return redirect("/connect", code=302)
	loginMessage = getCustomerDetails(apiSession)
	userId = myapi.user_id
	sessionKey = myapi.session_key
	output = "Most recent session:"+apiSession
	return render_template("index.html", output=output, apiSession=apiSession, userId=userId, sessionKey=sessionKey, loginMessage=loginMessage)	

@app.route('/getFnOStocks', methods=['GET'])
@cross_origin()
def getFnOStocks():
	queryParams = request.args.to_dict()
	searchStr = queryParams.get('searchStr','OPT CNXBAN 43800')
	seachStrList = searchStr.split(' ')
	fnoStocksDict = myapi.getFnOStocks(*seachStrList)
	return (json.dumps(fnoStocksDict),200, {'Content-Type': 'application/json'})


@app.route('/getExistingSessions', methods=['GET', 'POST'])
@cross_origin()
def getExistingSessions():
    existingSession = os.listdir('./bzapisessions')
    outputResponse = "{\"msg\" : \"Existing api sessions=" + str(existingSession) + "\"}"
    return (outputResponse,200, {'Content-Type': 'application/json'})

@app.route('/getCurrentSession', methods=['GET'])
@cross_origin()
def getCurrentSession():
    return session["apisession"]

@app.route('/clearSessionFiles', methods=['GET', 'POST'])
@cross_origin()
def clearSessionFiles():
    queryParams = request.args.to_dict()
    apiSession = queryParams.get('sessionfile','none')
    if apiSession != "none":
        if os.path.exists("./breezeapi/bzapisessions/" + apiSession):
            os.remove("./breezeapi/bzapisessions/" + apiSession)
    return redirect("/getExistingSessions", code=302)

def getCustomerDetails(apiSession):
    customerDetailsJsonDict = myapi.getCustomerDetails(apiSession)
    print(customerDetailsJsonDict)
    userId = customerDetailsJsonDict["Success"]["idirect_userid"]
    userName = customerDetailsJsonDict["Success"]["idirect_user_name"]
    lastLogin = customerDetailsJsonDict["Success"]["idirect_lastlogin_time"]
    customerDetails = userId + "-" + userName + "-last login: " + lastLogin
    return customerDetails

@app.route('/getStockToken', methods=['GET', 'POST'])
@cross_origin()
def getStockToken():
	queryParams = request.args.to_dict()
	stockCode = queryParams.get("stockCode","CNXBAN")
	exchangeCode = queryParams.get("exchangeCode","NFO")
	productType = queryParams.get("productType","Options")
	strike = queryParams.get("strike")
	expiryDateStr = queryParams.get("expiryDate")
	rightTypeStr = queryParams.get("rightType")
	#expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
	#rightType = breezeapi.RightType.from_str(rightTypeStr)
	(quotesToken,marketDepthToken) = myapi.getTokenFromStockName(exchangeCode, stockCode, productType, expiryDateStr, strike, rightTypeStr)
	print(quotesToken+"<-->"+marketDepthToken)
	return ("{\"quotesToken\":\""+quotesToken+"\"}",200, {'Content-Type': 'application/json'})

@app.route('/getOrderList', methods=['GET', 'POST'])
@cross_origin()
def getOrderList():
	#from_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T05:30:00.000Z'
	#to_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T20:30:00.000Z'
	
	queryParams = request.args.to_dict()
	fromDateStr = queryParams.get("orderDate","07-12-2023")
	toDateStr = queryParams.get("orderDate","07-12-2023")
	
	if fromDateStr == "":
		today = datetime.now()
		#show only one day orders
		daysFrom = timedelta(days = 0)
		fromDate = today - daysFrom
		toDate = today
		fromDateStr = fromDate.strftime("%d-%b-%Y")
	else:
		fromDate = datetime.strptime(fromDateStr,"%d-%m-%Y").date()
		toDate = datetime.strptime(toDateStr,"%d-%m-%Y").date()
		fromDateStr = fromDate.strftime("%d-%b-%Y")
		
	orderList =  myapi.getOrderList(fromDate,toDate)
	if orderList is None or orderList.get("Success") is None:
		print(orderList)
		orderList = json.loads('{"Error":"Not connected"}')
		return (orderList,200, {'Content-Type': 'application/json'})
	unfilteredOrderList = orderList.get("Success")
	if(unfilteredOrderList is not None):
		orderListDf = pd.json_normalize(unfilteredOrderList)
		#orderListDf = orderListDf.apply(derivedCol, axis=1)
		#today = datetime.now()    
		#todayStr = today.strftime("%d-%b-%Y")
		orderDateStr = fromDateStr
		#print(todayStr)
		result = orderListDf.loc[( \
										  ((orderListDf["order_datetime"].str.contains(orderDateStr,na=False, case=False))) \
										 ) ].copy()
		#print(result.columns.values)
		#print(result[["order_id","order_datetime","stock_code","status","1","2","3"]])
		result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
		result.sort_values(by='order_datetime_sorting', inplace = True, ascending = False)
		resultJsonStr = result.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		orderList["Success"]=resultJsonDict
	#print(resultJsonDict)
	return (orderList,200, {'Content-Type': 'application/json'})

@app.route('/getOpenPositions', methods=['GET', 'POST'])
@cross_origin()
def getOpenPositions():
	openPositions = myapi.getPortfolioPositions()
	if openPositions is None:
		print(openPositions)
		openPositions = json.loads('{"Error":"Not connected"}')
	return (openPositions,200, {'Content-Type': 'application/json'})

@app.route('/placeOrder', methods=['GET', 'POST'])
@cross_origin()
def placeOrder():
	queryParams = request.args.to_dict()
	stockCode = queryParams.get("stockCode","CNXBAN")
	quantity = queryParams.get("quantity","1")
	priceStr = queryParams.get("price","1")
	stoploss = queryParams.get("stoploss","")
	action = queryParams.get("action")
	product = queryParams.get("product")
	exchangeCode = queryParams.get("exchangeCode","NFO")
	strike = ""
	rightTypeStr = ""
	orderType = "limit"
	if priceStr == "0":
		orderType = "market"

	if exchangeCode == "NFO":
		expiryDateStr = queryParams.get("expiryDate")
		expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
		if product == "options":
			strike = queryParams.get("strike","NA")
			rightTypeStr = queryParams.get("rightType","NA")
			rightTypeEnum = breezeapi.RightType.from_str(rightTypeStr)
			rightTypeStr = rightTypeEnum.name
	result = myapi.placeOrder(stockCode,exchangeCode,product,action,orderType,stoploss,quantity,priceStr, expiryDate,rightTypeStr,strike)
	if result is None:
		print(result)
		result = json.loads('{"Error":"Not connected"}')
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/squareoff', methods=['GET', 'POST'])
@cross_origin()
def squareoff():
	queryParams = request.args.to_dict()
	stockCode = queryParams.get("stockCode","CNXBAN")
	quantity = queryParams.get("quantity","1")
	priceStr = queryParams.get("price","1")
	stoploss = queryParams.get("stoploss","")
	action = queryParams.get("action")
	product = queryParams.get("product")
	exchangeCode = queryParams.get("exchangeCode","NFO")
	strike = ""
	rightTypeStr = ""
	orderType = "limit"
	if priceStr == "0":
		orderType = "market"

	if exchangeCode == "NFO":
		expiryDateStr = queryParams.get("expiryDate")
		expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
		if product == "options":
			strike = queryParams.get("strike","NA")
			rightTypeStr = queryParams.get("rightType","NA")
			rightTypeEnum = breezeapi.RightType.from_str(rightTypeStr)
			rightTypeStr = rightTypeEnum.name
	result = myapi.squareOff(stockCode,exchangeCode,product,action,orderType,stoploss,quantity,priceStr, expiryDate,rightTypeStr,strike)
	if result is None:
		print(result)
		result = json.loads('{"Error":"Not connected"}')
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/modifyOrder', methods=['GET', 'POST'])
@cross_origin()
def modifyOrder():
	queryParams = request.args.to_dict()
	orderIdStr = queryParams.get("orderId","")
	exchangeCode = queryParams.get("exchangeCode","NFO")
	priceStr = queryParams.get("price","")
	quantityStr = queryParams.get("quantity","")
	stopLossStr = queryParams.get("stoploss","0")
	orderType = "limit"
	if priceStr == "0":
		orderType = "market"
	result = myapi.modifyOrder(orderIdStr,exchangeCode,orderType,stopLossStr,quantityStr,priceStr)
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/cancelOrder', methods=['GET', 'POST'])
@cross_origin()
def cancelOrder():
	queryParams = request.args.to_dict()
	orderId = queryParams.get("orderId")
	result = myapi.cancelOrder(orderId)
	return (result,200, {'Content-Type': 'application/json'})

def pnlMultiplier(row):
    pnlMultilpier = 1
    if row["action"] == "Buy":
        pnlMultilpier = -1
    row["sum_total_cost"] = pnlMultilpier * row["sum_total_cost"]
    row["total_cost_with_taxes"] = pnlMultilpier * row["total_cost_with_taxes"]
    return row

def costCalculator(row):
    row["total_cost_with_taxes"] = row["sum_total_cost"]
    if row["action"] == "Buy":
        row["total_cost_with_taxes"] = row["total_cost_with_taxes"] + row["sum_total_taxes"]
    else:
        row["total_cost_with_taxes"] = row["total_cost_with_taxes"] - row["sum_total_taxes"]
    return row


@app.route('/getRealisedPnL', methods=['GET', 'POST'])
@cross_origin()
def getRealisedPnL():
	queryParams = request.args.to_dict()
	fromDateStr = queryParams.get("fromDate",datetime.now().strftime("%d-%b-%Y"))
	toDateStr = queryParams.get("toDate",datetime.now().strftime("%d-%b-%Y"))
	fromDate = datetime.strptime(fromDateStr, "%d-%b-%Y")
	toDate = datetime.strptime(toDateStr, "%d-%b-%Y")
	exchangeCode = "NFO" #get only fno pnl
	tradesListJsonDict = myapi.getTradesList(fromDate,toDate,exchangeCode)
	if tradesListJsonDict is None:
		print(tradesListJsonDict)
		tradesListJsonDict = json.loads('{"Error":"Not connected"}')
		return (tradesListJsonDict,200, {'Content-Type': 'application/json'})
	
	if not tradesListJsonDict["Success"]:
		print("No Trades taken between "+fromDateStr+"-"+toDateStr)
		print(tradesListJsonDict)
		return (tradesListJsonDict,200, {'Content-Type': 'application/json'})
	tradesListDf = pd.json_normalize(tradesListJsonDict["Success"])
	tradesListDf["quantity"] = tradesListDf["quantity"].astype(float)
	tradesListDf["average_cost"] = tradesListDf["average_cost"].astype(float)
	tradesListDf["total_taxes"] = tradesListDf["total_taxes"].astype(float)
	tradesListDf["total_cost"] = tradesListDf["quantity"] * tradesListDf["average_cost"]
	#print(tradesListDf)
	groupbyTradesListDf = tradesListDf.groupby(["stock_code", "action"], as_index=False)\
    .agg(quantity=("quantity","sum"),sum_total_cost=("total_cost","sum"),sum_total_taxes=("total_taxes","sum"))
	groupbyTradesListDf = groupbyTradesListDf.apply(costCalculator,axis=1)
	groupbyTradesListDf = groupbyTradesListDf.apply(pnlMultiplier,axis=1)
	#print(groupbyTradesListDf)
	#remove open postion total cost from all trades cost
	openPositionsDict = myapi.getPortfolioPositions()
	totalOpAmount = 0
	if not openPositionsDict is None and not openPositionsDict["Success"] is None:
		todayStr = datetime.now().strftime("%d-%b-%Y")
		today = datetime.strptime(todayStr, "%d-%b-%Y")
		if toDate == today:
			openPositionsDf = pd.json_normalize(openPositionsDict["Success"])
			#print(openPositionsDf)
			openPositionsDf["quantity"] = openPositionsDf["quantity"].astype(float)
			openPositionsDf["average_price"] = openPositionsDf["average_price"].astype(float)
			openPositionsDf["total_op_amt"] = openPositionsDf["quantity"] * openPositionsDf["average_price"] * -1 #assuming buy
			totalOpAmount = openPositionsDf['total_op_amt'].sum()
			print("Total open position:" + str(totalOpAmount))
	realised_pnl = groupbyTradesListDf['sum_total_cost'].sum()
	realised_pnl_with_taxes = groupbyTradesListDf['total_cost_with_taxes'].sum()
	#remove open positions
	realised_pnl = round((realised_pnl - totalOpAmount),2)
	realised_pnl_with_taxes = round((realised_pnl_with_taxes - totalOpAmount),2)
	realisedPnlDf = pd.DataFrame({"realised_pnl": realised_pnl, 'realised_pnl_with_taxes': realised_pnl_with_taxes}, index=[0])
	#print(realisedPnlDf)
	resultJsonStr = realisedPnlDf.to_json(orient = "records")
	resultJsonDict = json.loads(resultJsonStr)
	tradesListJsonDict["Success"]=resultJsonDict[0]
	return (tradesListJsonDict,200, {'Content-Type': 'application/json'})


def subscribeQuotesFeed(token,interval):
	subscriptionStatus = myapi.subscribeQuotes(token,interval)
	return (subscriptionStatus,200, {'Content-Type': 'application/json'})

def unsubscribeQuotesFeed(token,interval):
	unsubscriptionStatus = myapi.unsubscribeQuotes(token,interval)
	return (unsubscriptionStatus,200, {'Content-Type': 'application/json'})

def subscribeMarketDepth(token):
	subscriptionStatus = myapi.subscribeMarketDepth(token)
	return (subscriptionStatus,200, {'Content-Type': 'application/json'})

def unsubscribeMarketDepth(token):
	unsubscriptionStatus = myapi.unsubscribeMarketDepth(token)
	return (unsubscriptionStatus,200, {'Content-Type': 'application/json'})
	
@app.route('/getHistoricalData', methods=['GET', 'POST'])
@cross_origin()
def getHistoricalData():
    queryParams = request.args.to_dict()
    interval = queryParams.get("interval","15minute")
    fromDateStr = queryParams.get("fromDate","2023-11-01T00:00:00.000Z")
    toDateStr = queryParams.get("toDate","2023-11-01T00:00:00.000Z")
    stockCode = queryParams.get("stockCode","CNXBAN")
    exchangeCode = queryParams.get("exchangeCode","NSE")
    product = queryParams.get("product","")
    expiry = queryParams.get("expiry","")
    rightStr = queryParams.get("right","")
    strikePrice = queryParams.get("strike","")
    hDataJsonDict = myapi.getHistoricalData(interval, fromDateStr, toDateStr, stockCode, exchangeCode,product,expiry,rightStr,strikePrice)
    #print(hDataJsonDict)
    if hDataJsonDict is None:
        print(hDataJsonDict)
        hDataJsonDict = json.loads('{"Error":"Not connected"}')
        return (hDataJsonDict,200, {'Content-Type': 'application/json'})

    if not hDataJsonDict.get("Success") or hDataJsonDict.get("Error"):
        print("Invalid Historical data")
        print(hDataJsonDict)
        return (hDataJsonDict,200, {'Content-Type': 'application/json'})

    hDataDf = pd.json_normalize(hDataJsonDict["Success"])
    #'2023-11-01 12:30:00'
    hDataDf["time"] = hDataDf['datetime'].apply(lambda x: datetime.strptime(x,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
    hDataDf["value"] = hDataDf["volume"]
    resultJsonStr = hDataDf.to_json(orient = "records")
    resultJsonDict = json.loads(resultJsonStr)
    hDataJsonDict["Success"]=resultJsonDict
    return (hDataJsonDict,200, {'Content-Type': 'application/json'})

@app.route('/getFunds', methods=['GET', 'POST'])
@cross_origin()
def getFunds():
	fundsJsonDict = myapi.getFunds()
	if fundsJsonDict is None:
		fundsJsonDict = json.loads('{"Error":"Not connected"}')
	print(fundsJsonDict)
	return (fundsJsonDict,200, {'Content-Type': 'application/json'})
	

@app.route('/getMargin', methods=['GET', 'POST'])
@cross_origin()
def getMargin():
	queryParams = request.args.to_dict()
	exchangeCode = queryParams.get("exchangeCode","NFO")
	marginJsonDict = myapi.getMargin(exchangeCode)
	if marginJsonDict is None:
		marginJsonDict = json.loads('{"Error":"Not connected"}')
	#print(marginJsonDict)
	return (marginJsonDict,200, {'Content-Type': 'application/json'})

@app.route('/marginCalculator', methods=['GET', 'POST'])
@cross_origin()
def marginCalculator():
	queryParams = request.args.to_dict()
	newPosition = {}
	exchangeCode = queryParams.get("exchangeCode","NFO")
	newPosition["stock_code"] = queryParams.get("stockCode","")
	newPosition["expiry_date"] = queryParams.get("expiryDate","")
	newPosition["product"] = queryParams.get("product","")
	newPosition["action"] = queryParams.get("action","")
	newPosition["price"] = queryParams.get("price","")
	newPosition["quantity"] = queryParams.get("quantity","")
	newPosition["strike_price"] = queryParams.get("strike","")
	rightTypeStr = queryParams.get("rightType","")
	if not rightTypeStr == "":
		rightTypeEnum = breezeapi.RightType.from_str(rightTypeStr)
		rightTypeStr = rightTypeEnum.name
	newPosition["right"] = rightTypeStr
	includeOpenPostions = queryParams.get("includeOpenPositions","")
	if includeOpenPostions.lower() == "true":
		includeOpenPostions = True
	includePendingOrders = False
	#open positions
	openPositionsList = []
	if includeOpenPostions:
		openPositionsDictList = myapi.getPortfolioPositions()
		#print("open position as below")
		#print(openPositionsDictList)
		if not openPositionsDictList is None and not openPositionsDictList["Success"] is None:
			#print(openPositionsDictList)
			openPositionsDictList = openPositionsDictList["Success"]
			filteredKeys = ["stock_code","expiry_date","action","price","quantity","strike_price","right"]
			openPositionsList = []
			for openPosition in openPositionsDictList:
				print(openPosition)
				if openPosition['action'] == 'NA':
					continue
				openPositionsFilteredDict = {key: openPosition[key] for key in filteredKeys}
				openPositionsFilteredDict["product"] = openPosition["product_type"]
				openPositionsFilteredDict["price"] = openPosition["average_price"]
				openPositionsList.append(openPositionsFilteredDict)
	#print(openPositionsList)

	#pending orders
	pendingOrdersList = []
	if includePendingOrders:
		today = datetime.now()
		#show only one day orders
		daysFrom = timedelta(days = 0)
		fromDate = today - daysFrom
		toDate = today + timedelta(days=0)
		orderList =  myapi.getOrderList(fromDate,toDate)
		if(orderList is not None and orderList["Success"] is not None ):
			unfilteredOrderList = orderList["Success"]
			orderListDf = pd.json_normalize(unfilteredOrderList)
			#pd.set_option('display.max_columns', 500)
			#print(orderListDf)
			pendingOrdersDf = orderListDf.loc[( \
				((orderListDf["status"].str.contains("Requested",na=False, case=False))) \
				| ((orderListDf["status"].str.contains("Queued",na=False, case=False))) \
				| ((orderListDf["status"].str.contains("Ordered",na=False, case=False))) \
			) ].copy()
			#print("Pending orders")
			#print(pendingOrdersDf)
			pendingOrdersDf["product"] = pendingOrdersDf["product_type"]
			pendingOrdersDf = pendingOrdersDf[["stock_code","product","expiry_date","action","price","quantity","strike_price","right"]]
			pendingOrdersList = pendingOrdersDf.to_dict(orient='records')

	listOfPositions = []
	listOfPositions = openPositionsList
	listOfPositions = listOfPositions + pendingOrdersList
	listOfPositions.append(newPosition)
	#print("list of positions")
	#print(listOfPositions)
	marginDict = myapi.marginCalculator(listOfPositions,"NFO")
	#print(marginDict)
	return (marginDict,200, {'Content-Type': 'application/json'})

@app.route('/getBrokerages', methods=['GET', 'POST'])
@cross_origin()
def getBrokerages():
	queryParams = request.args.to_dict()
	stockCode = queryParams.get("stockCode","CNXBAN")
	quantity = queryParams.get("quantity","1")
	priceStr = queryParams.get("price","1")
	action = queryParams.get("action")
	product = queryParams.get("product")
	exchangeCode = queryParams.get("exchangeCode","NFO")
	strike = ""
	rightTypeStr = ""
	orderType = "limit"
	if priceStr == "0":
		orderType = "market"

	if exchangeCode == "NFO":
		expiryDateStr = queryParams.get("expiryDate")
		expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
		if product == "options":
			strike = queryParams.get("strike","NA")
			rightTypeStr = queryParams.get("rightType","NA")
			rightTypeEnum = breezeapi.RightType.from_str(rightTypeStr)
			rightTypeStr = rightTypeEnum.name
	brokerageDict = myapi.getBrokerages(exchangeCode,stockCode,product,orderType,priceStr,action,quantity,expiryDate,rightTypeStr,strike)
	#print(brokerageDict)
	return (brokerageDict,200, {'Content-Type': 'application/json'})

def feedData(data):
	#print(data)
	token = "none"
	interval = ""
	if data.get('quotes') == None and data.get('sourceNumber') == None:
		#OHLV data
		interval = data['interval']
		exchangeCode = data['exchange_code']
		stockCode = data['stock_code']
		expiryDate = ""
		product = "equity"
		rightType = ""
		strikePrice = ""
		if data.get('exchange_code') == "NFO":
			expiryDate = data['expiry_date']
			product = "futures"
			if data.get('right_type') != None:
				product = "options"
				strikePrice = str(data['strike_price']).split('.')[0]
				rightType = breezeapi.RightType.from_str(data['right_type']).name
				#print(exchangeCode, stockCode, product,expiryDate,strikePrice,rightType)
				(quotesToken, marketDepthToken) = myapi.getTokenFromStockName(exchangeCode, stockCode, product,expiryDate,strikePrice,rightType)
				token = quotesToken.split('!')[1]
			else:
				(quotesToken, marketDepthToken) = myapi.getTokenFromStockName(exchangeCode, stockCode, product,expiryDate,"","")
				token = quotesToken.split('!')[1]
				#print(token,stockCode)
		elif data.get('exchange_code') == "NSE":
			#print(exchangeCode, stockCode, "","","","")
			(quotesToken, marketDepthToken) = myapi.getTokenFromStockName(exchangeCode, stockCode, "","","","")
			token = quotesToken.split('!')[1]
	elif data.get('quotes') == "Market Depth":
		#Market Data
		token = data['symbol'].split('!')[1]
	elif data.get('quotes') == "Quotes Data":
		token = data['symbol'].split('!')[1]
		interval = data['interval']
	elif data.get('sourceNumber') != None:
		#order Notification
		token = "order_notification"
	eventName = token
	if interval != "":
		eventName = token + "-" + interval
		data['token'] = token
	#print("emited data for eventName:" + eventName
	socketio.emit(eventName, json.dumps(data))



if __name__ == '__main__':
	#context = ('local.crt', 'local.key')#certificate and key files
	#app.run(debug=True, ssl_context=context)
	app.run(debug=True)
	socketio.run(app, debug = True)


	