
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
from brokerapi import breezeApiAdapter
from brokerapi import brokerApiConnect
from dataproviderapi import breezeDataProvider
from dataproviderapi import dataproviderConnect
from icecream import ic
import json
import pandas as pd
import configapi
import sys
import traceback

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    from importlib_metadata import metadata


app = Flask(__name__)
socketio = SocketIO(app,logger=False, engineio_logger=False)

cors = CORS(app)
app.secret_key = "thisisasecretkeyfortheflasksession"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['CORS_HEADERS'] = 'Content-Type'

app.breezeapi_version = metadata.version('breeze_connect')

#initialise to the default broker but do not connect yet.
#we will try to connect when app is launched.
brokerapi = brokerApiConnect.BrokerApiConnect(configapi.BROKER_DEFAULT)
#initialise to the default dataprovider
dataprovider = dataproviderConnect.DataProviderConnect(configapi.DATAPROVIDER_DEFAULT)
myapi = brokerapi.brokerApi
if brokerapi.isConnected() and brokerapi.BROKER == configapi.BROKER_IDIRECT:
	#this can never happen as brokerapi.connect is not called during file load
	print("idirect brokerapi is connected. initializing chart to same.")
	dataprovider.initialize(myapi.api,{})
else:
	#if server restarts and we already have a request token, then connect to dataprovider.
	#this is required so that we can load chart when app launches.
	print("brokerapi is not connected or it is not idirect. initializing default data provider")
	try:
		dataprovider.initialize(None,{})
		print("On app start, dataprovider is connected")
	except Exception as e:
		#we do not have a valid request token. Need to go for login flow manually.
		print("On app start, dataprovider not connected exception raised")
		print(e)

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

@app.route('/login', methods=['GET', 'POST'])
@cross_origin()
def login():
	queryParams = request.args.to_dict()
	mode = queryParams.get("mode","full")
	newBroker = queryParams.get("broker",configapi.BROKER_DEFAULT)
	session["mode"] = mode
	
	app.logger.info("login to %s api: %s",mode,newBroker)
	app.logger.info("ChartSessionKey:%s",session.get("chartSessionKey",""))
	#check whether this is chart dataprovider login request or broker login request
	if mode == "chart":
		#skip login if already connected
		if (dataprovider.isDataProviderConnected() or session.get("chartSessionKey","") != ""):
			return redirect(url_for('getDataProviderAccessToken',**request.args))
		#fetch login url for redirect
		newdataprovider = dataproviderConnect.DataProviderConnect(configapi.DATAPROVIDER_IDIRECT)
		print("preparing to redirect to dataprovider login page")
		login_url = newdataprovider.getLoginUrl()
	else:
		#this is a broker login request
		newBrokerApi = brokerApiConnect.BrokerApiConnect(newBroker)
		#skip login if already connected
		if session.get(newBrokerApi.getSessionTokenName(),"") != "":
			print("Not redirecting to login screen as session exist for new broker: " + newBroker + ",token: " + session.get(newBrokerApi.getSessionTokenName()))
			return redirect(url_for('connectApi',**request.args))
		#fetch login url for redirect
		login_url = newBrokerApi.getLoginUrl()
		session["newbroker"] = newBroker
	print(login_url)
	#goto login url for login
	return redirect(login_url)

'''
This method is getting called from broker api login page after successful login.
This is redirect url registered with broker api.
DO NOT CHANGE. BE CAREFUL
'''
@app.route('/authorize', methods=['GET', 'POST'])
def authorize():
	print("inside authorize")
	#queryParams = request.args.to_dict()
	#print(queryParams)
	return redirect(url_for('connectApi',**request.args))
	

@app.route('/connect', methods=['GET', 'POST'])
@cross_origin()
def connectApi():		
	queryParams = request.args.to_dict()
	app.logger.info("Current login flow: %s", session.get("mode",""))
	#check whether this is post login for chart/data provider
	if session.get("mode","") == "chart":
		#reset the login process flag
		session["mode"] = ""
		chartSessionKey = queryParams.get(configapi.IDIRECT_SESSION_TOKEN_NAME,session.get("chartSessionKey"))
		session["chartSessionKey"] = chartSessionKey
		#need to let page refresh and then once socket is connected then send data
		#socketio.emit("processChartSessionKey", json.dumps({"userid":"HITYJ3OJ","sessionkey":apiSession}))
		#time.sleep(10)
		#return redirect("/", code=302)
		#return render_template("loginresponse.html", userId=chartUserId,sessionKey=chartSessionKey)	
		return getDataProviderAccessToken()
	#this is post-login process for broker
	global brokerapi, myapi
	newBrokerApi = brokerapi
	apiSession = queryParams.get(newBrokerApi.getSessionTokenName(),"")
	userId = ""
	sessionKey = ""
	loginMessage = "Not logged in."
	invalidSessionMsg = ""
	try:
		#check whether this is new broker or existing broker.
		if session.get("newbroker","") == "":
			#this is existing broker
			app.logger.info("Not switching to new broker.")
			app.logger.info("This is probably page refresh or request to connect to already connected broker")
			#re-connect using the existing token
			sessionToken = newBrokerApi.connect(queryParams)
			session[newBrokerApi.getSessionTokenName()] = sessionToken
			#set callback for api web socket responses
			newBrokerApi.registerFeedCallback(feedData)
		else:
			app.logger.info("Switching to new broker >%s<",session.get("newbroker",""))
		
		#check whether this is broker only post-login or full (broker + data provider) post-login
		if session.get("mode","") == "broker":
			try:
				#this is broker-only setup
				newBroker = session.get("newbroker","")
				#reset the broker login flag
				session["newbroker"] = ""
				reloadHome = False
				#check whether broker is connected or this is new broker post-login flow
				if not newBrokerApi.isConnected() or (not newBroker == "" and not newBroker == newBrokerApi.BROKER):
					app.logger.info("Trying to switch broker to %s",newBroker)
					brokerapi = brokerApiConnect.BrokerApiConnect(newBroker)					
					myapi = brokerapi.brokerApi
					sessionToken = brokerapi.connect(queryParams)
					session[brokerapi.getSessionTokenName()] = sessionToken
					#set callback for api web socket responses
					brokerapi.registerFeedCallback(feedData)
					#set the new broker name in session
					session["broker"] = newBroker
				else:
					#broker is already connected. This is probably a page refresh
					app.logger.info("Doing nothing with existing broker %s",brokerapi.BROKER)
					sessionToken = session.get(brokerapi.getSessionTokenName(),"")
					reloadHome = True
				#fetch some login info to display on-screen
				loginMessage = getCustomerDetails()
				userId = myapi.user_id
				sessionKey = myapi.session_key
				output = "Using most recent session "
				#dataprovider = dataproviderConnect.DataProviderConnect()
				#dataprovider.initialize(myapi.api,{})
				#check whether we are reloading main page or returning to post-login pop up
				if reloadHome:
					return redirect("/", code=302)
				else: 
					return render_template("loginresponse.html", error="", mode = "broker", broker=newBroker, userId = userId, sessionKey = sessionKey, loginMessage=loginMessage)	
			except Exception as e:
				app.logger.info("Error in broker login flow")
				app.logger.error(e)
				return render_template("loginresponse.html", error=e, mode = "broker", broker=newBroker, userId = userId, sessionKey = sessionKey, loginMessage=loginMessage)	
		
		#post-login setup for full mode
		brokerapi = newBrokerApi
		myapi = brokerapi.brokerApi
		session["broker"] = brokerapi.BROKER
		session["newbroker"] = ""
		#check whether full mode and initializa data provider
		if session.get("mode","") == "full":
			dataprovider.initialize(brokerapi.brokerApi.api,{})
			print("Dataprovider connected on full mode?" + str(dataprovider.isDataProviderConnected()))
		#redirect to homepage
		return redirect("/", code=302)
	except Exception as e:
		app.logger.info("Error in reload page flow")
		app.logger.error(e)
		invalidSessionMsg = ". Session invalid. Create new session from login url."
		brokerapi.clearTokenFiles()
		session.pop(brokerapi.getSessionTokenName(),None)
	
	#if you reached here, you encountered problem in connection. Try again from home page
	loginUrl = "<a href='/login'>Login</a>"
	output = loginUrl +"<br/>Using most recent session:"+invalidSessionMsg
	return render_template("index.html", output=output, broker=brokerapi.BROKER, userId=userId, sessionKey=sessionKey, loginMessage=loginMessage)	

#this is homepage and get called on app launch or page refresh
@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def homePage():
	#try connecting to the broker when app launched/page refreshes
	session["mode"] = "broker"
	#get last connected broker from session to reconnect
	if not "broker" in session:
		#last connected broker not in session(probably session destroyed), use brokerapi to get that
		session["broker"] = brokerapi.BROKER
	broker = session.get("broker")
	
	if broker == configapi.BROKER_IDIRECT:
		# as of now, data provider(charts) is also idirect. 
		# hence we have full mode as we cannot login twice. same login is shared by broker and data provider
		session["mode"] = "full"
	
	if not brokerapi.isConnected():
		#this happens for first app launch
		app.logger.info("%s broker is not connected. Redirecting to /connect",broker)
		return redirect("/connect", code=302)
	
	#this happens if we accidently closed app and relaunch it and the server is still running
	apiSession = session.get( brokerapi.getSessionTokenName(),"")
	#broker is already connected. reset the login flag
	session["mode"] = ""
	if apiSession == "" or apiSession == "no-breezeapi-session":
		print("api connected but session destroyed/tab closed.")
		print("getting apisession from file")
		return redirect("/connect", code=302)
	loginMessage = getCustomerDetails()
	userId = myapi.user_id
	sessionKey = myapi.session_key
	output = "Using most recent session"
	return render_template("index.html", output=output, broker=brokerapi.BROKER, userId=userId, sessionKey=sessionKey, loginMessage=loginMessage)	

@app.route('/getAccessToken', methods=['GET', 'POST'])
@cross_origin()
def getDataProviderAccessToken():

	try:
		if not dataprovider.isDataProviderConnected():
			dataprovider.initialize(None,{configapi.IDIRECT_SESSION_TOKEN_NAME:session.get("chartSessionKey","")})
		(userId,sessionKey) = dataprovider.getDataProviderToken({})
		session["chartSessionKey"] = sessionKey
		print("response received:" + userId+" : " + sessionKey)
	except Exception as e:
		app.logger.error(e)
		#traceback.print_stack()
		session["chartSessionKey"] = ""
		return redirect(url_for('login',**request.args))
	#return (json.dumps(response),200, {'Content-Type': 'application/json'})	
	return render_template("loginresponse.html", mode = "chart", broker="idirect", userId = userId, sessionKey = sessionKey)	

@app.route('/getFnOStocks', methods=['GET'])
@cross_origin()
def getFnOStocks():
	queryParams = request.args.to_dict()
	searchStr = queryParams.get('searchStr','OPT CNXBAN 43800')
	seachStrList = searchStr.split(' ')
	fnoStocksDict = brokerapi.getStocks(*seachStrList)
	return (json.dumps(fnoStocksDict),200, {'Content-Type': 'application/json'})

@app.route('/getDPStocks', methods=['GET'])
@cross_origin()
def getDPStocks():
	queryParams = request.args.to_dict()
	searchStr = queryParams.get('searchStr','FUT CNXBAN')
	strict = queryParams.get('strict','False')
	seachStrList = searchStr.split(' ')
	dpStocksDict = dataprovider.getDataproviderStocks(strict,*seachStrList)
	return (json.dumps(dpStocksDict),200, {'Content-Type': 'application/json'})


@app.route('/getExistingSessions', methods=['GET', 'POST'])
@cross_origin()
def getExistingSessions():
    existingSession = os.listdir('./idirectsessiontokens')
    outputResponse = "{\"msg\" : \"Existing api sessions=" + str(existingSession) + "\"}"
    return (outputResponse,200, {'Content-Type': 'application/json'})

@app.route('/getCurrentSession', methods=['GET'])
@cross_origin()
def getCurrentSession():
    return session[brokerapi.getSessionTokenName()]

@app.route('/clearSessionFiles', methods=['GET', 'POST'])
@cross_origin()
def clearSessionFiles():
    queryParams = request.args.to_dict()
    apiSession = queryParams.get('sessionfile','none')
    if apiSession != "none":
        if os.path.exists("./breezeapi/bzapisessions/" + apiSession):
            os.remove("./breezeapi/bzapisessions/" + apiSession)
    return redirect("/getExistingSessions", code=302)

def getCustomerDetails():
	print("fetching customer details")
	customerDetailsJsonDict = brokerapi.getCustomerDetails()
	print("printing customer details")
	print(customerDetailsJsonDict)
	if (customerDetailsJsonDict["Success"] != None):
		userId = customerDetailsJsonDict["Success"]["idirect_userid"]
		userName = customerDetailsJsonDict["Success"]["idirect_user_name"]
		lastLogin = customerDetailsJsonDict["Success"]["idirect_lastlogin_time"]
	else:
		userId = customerDetailsJsonDict["Error"]
		userName = ""
		lastLogin = ""
	version = brokerapi.getApiVersion()
	customerDetails = userId + "-" + userName + "-last login: " + lastLogin + " (" + version + ")"
	print(customerDetails)
	return customerDetails

@app.route('/getStockToken', methods=['GET', 'POST'])
@cross_origin()
def getStockToken():
	queryParams = request.args.to_dict()
	(quotesToken,marketDepthToken) = brokerapi.getTokenFromStockName(queryParams)
	print(quotesToken+"<-->"+marketDepthToken)
	return ("{\"quotesToken\":\""+quotesToken+"\"}",200, {'Content-Type': 'application/json'})

@app.route('/getOrderDetails', methods=['GET', 'POST'])
@cross_origin()
def getOrderDetails():
	queryParams = request.args.to_dict()
	orderId = queryParams.get("orderId")
	orderDetails =  brokerapi.getOrderDetails(orderId)
	return (orderDetails,200, {'Content-Type': 'application/json'})

@app.route('/getOrderList', methods=['GET', 'POST'])
@cross_origin()
def getOrderList():
	#from_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T05:30:00.000Z'
	#to_date = datetime.strpdate(str(datetime.today()),"%Y-%m-%d").isoformat()[:10] + 'T20:30:00.000Z'
	queryParams = request.args.to_dict()
	orderList =  brokerapi.getOrdersList(queryParams)
	return (orderList,200, {'Content-Type': 'application/json'})

@app.route('/getOpenPositions', methods=['GET', 'POST'])
@cross_origin()
def getOpenPositions():
	openPositions = brokerapi.getOpenPositionsList()
	if openPositions is None:
		print(openPositions)
		openPositions = json.loads('{"Error":"Not connected"}')
	return (openPositions,200, {'Content-Type': 'application/json'})

@app.route('/placeOrder', methods=['GET', 'POST'])
@cross_origin()
def placeOrder():
	queryParams = request.args.to_dict()
	result = brokerapi.placeOrder(queryParams)
	if result is None:
		print(result)
		result = json.loads('{"Error":"Not connected"}')
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/squareoff', methods=['GET', 'POST'])
@cross_origin()
def squareoff():
	queryParams = request.args.to_dict()
	result = brokerapi.squareOff(queryParams)
	if result is None:
		print(result)
		result = json.loads('{"Error":"Not connected"}')
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/modifyOrder', methods=['GET', 'POST'])
@cross_origin()
def modifyOrder():
	queryParams = request.args.to_dict()
	result = brokerapi.modifyOrder(queryParams)
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/cancelOrder', methods=['GET', 'POST'])
@cross_origin()
def cancelOrder():
	queryParams = request.args.to_dict()
	orderRef = queryParams.get("orderId")
	result = brokerapi.cancelOrder(orderRef)
	return (result,200, {'Content-Type': 'application/json'})

@app.route('/getRealisedPnL', methods=['GET', 'POST'])
@cross_origin()
def getRealisedPnL():
	queryParams = request.args.to_dict()
	tradesListJsonDict = brokerapi.getPnl(queryParams)
	return (tradesListJsonDict,200, {'Content-Type': 'application/json'})
	
@app.route('/getHistoricalData', methods=['GET', 'POST'])
@cross_origin()
def getHistoricalData():
	queryParams = request.args.to_dict()
	print("Historical data get:is dataprovider connected?" + str(dataprovider.isDataProviderConnected()))
	hDataJsonDict = dataprovider.getHistoricalData(queryParams)
	#print(hDataJsonDict)
	return (hDataJsonDict,200, {'Content-Type': 'application/json'})

@app.route('/getFunds', methods=['GET', 'POST'])
@cross_origin()
def getFunds():
	fundsJsonDict = brokerapi.getFunds()
	if fundsJsonDict is None:
		fundsJsonDict = json.loads('{"Error":"Not connected"}')
	print(fundsJsonDict)
	return (fundsJsonDict,200, {'Content-Type': 'application/json'})
	

@app.route('/getMargin', methods=['GET', 'POST'])
@cross_origin()
def getMargin():
	queryParams = request.args.to_dict()
	marginJsonDict = brokerapi.getMargin(queryParams)
	if marginJsonDict is None:
		marginJsonDict = json.loads('{"Error":"Not connected"}')
	#print(marginJsonDict)
	return (marginJsonDict,200, {'Content-Type': 'application/json'})

@app.route('/marginCalculator', methods=['GET', 'POST'])
@cross_origin()
def marginCalculator():
	queryParams = request.args.to_dict()
	marginDict = brokerapi.marginCalculator(queryParams)
	return (marginDict,200, {'Content-Type': 'application/json'})

@app.route('/getBrokerages', methods=['GET', 'POST'])
@cross_origin()
def getBrokerages():
	queryParams = request.args.to_dict()
	brokerageDict = brokerapi.getBrokerages(queryParams)
	#print(brokerageDict)
	return (brokerageDict,200, {'Content-Type': 'application/json'})

def subscribeQuotesFeed(token,interval):
	subscriptionStatus = brokerapi.subscribeQuotesFeed(token,interval)
	return (subscriptionStatus,200, {'Content-Type': 'application/json'})

def unsubscribeQuotesFeed(token,interval):
	unsubscriptionStatus = brokerapi.unsubscribeQuotesFeed(token,interval)
	return (unsubscriptionStatus,200, {'Content-Type': 'application/json'})

def subscribeMarketDepth(token):
	subscriptionStatus = brokerapi.subscribeMarketDepth(token)
	return (subscriptionStatus,200, {'Content-Type': 'application/json'})

def unsubscribeMarketDepth(token):
	unsubscriptionStatus = brokerapi.unsubscribeMarketDepth(token)
	return (unsubscriptionStatus,200, {'Content-Type': 'application/json'})

def feedData(eventName,data):
	#print(data)
	#print("emited data for eventName:" + eventName)
	socketio.emit(eventName, json.dumps(data))



if __name__ == '__main__':
	#context = ('local.crt', 'local.key')#certificate and key files
	#app.run(debug=True, ssl_context=context)
	app.run(debug=True)
	socketio.run(app, debug = True)


	
