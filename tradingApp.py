
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
from icecream import ic
import json
import pandas as pd
import configapi
import sys

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    from importlib_metadata import metadata


app = Flask(__name__)
socketio = SocketIO(app,logger=False, engineio_logger=False)

cors = CORS(app)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['CORS_HEADERS'] = 'Content-Type'

app.api_key = configapi.API_KEY
app.secret_key = configapi.SECRET_KEY
app.login_url = configapi.LOGIN_URL + urllib.parse.quote_plus(app.api_key)

app.breezeapi_version = metadata.version('breeze_connect')

#myapi = breezeApiAdapter.BreezeApiAdapter()
brokerapi = brokerApiConnect.BrokerApiConnect()
myapi = brokerapi.initialize()

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
	print("login to idirect breeze api")
	#redirect_uri = url_for('authorize', _external=True)
	print(app.login_url)
	#return oauth.breezeapi.authorize_redirect(redirect_uri)
	return redirect(app.login_url)

'''
This method is getting called from broker api login page after successful login.
This is redirect url registered with broker api.
DO NOT CHANGE. BE CAREFUL
'''
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
	#queryParams = request.args.to_dict()
	#apiSession = queryParams.get(configapi.SESSION_TOKEN_NAME,'')
	#return redirect('/connect?apisession=' + apiSession)
	return redirect(url_for('connectApi',**request.args))
	

@app.route('/connect', methods=['GET', 'POST'])
@cross_origin()
def connectApi():		
	queryParams = request.args.to_dict()
	apiSession = queryParams.get(configapi.SESSION_TOKEN_NAME,'no-breezeapi-session')
	userId = ""
	sessionKey = ""
	loginMessage = "Not logged in."
	invalidSessionMsg = ""
	try:
		#myapi.onMessage = feedData
		brokerapi.registerFeedCallback(feedData)
		sessionToken = brokerapi.connect(queryParams)
		session[configapi.SESSION_TOKEN_NAME] = sessionToken
		return redirect("/", code=302)
	except Exception as e:
		app.logger.error(e)
		invalidSessionMsg = ". Session invalid. Create new session from login url."
	
	loginUrl = "<a href='/login'>Login</a>"
	output = loginUrl +"<br/>Most recent session:"+apiSession+invalidSessionMsg
	return render_template("index.html", output=output, apiSession=apiSession, userId=userId, sessionKey=sessionKey, loginMessage=loginMessage)	


@app.route('/', methods=['GET', 'POST'])
@cross_origin()
def oneClick():
	if not brokerapi.isConnected():
		return redirect("/connect", code=302)
	apiSession = session.get(configapi.SESSION_TOKEN_NAME,"")
	if apiSession == "" or apiSession == "no-breezeapi-session":
		print("api connected but session destroyed/tab closed.")
		print("getting apisession from file")
		return redirect("/connect", code=302)
	loginMessage = getCustomerDetails()
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
	fnoStocksDict = brokerapi.getStocks(*seachStrList)
	return (json.dumps(fnoStocksDict),200, {'Content-Type': 'application/json'})


@app.route('/getExistingSessions', methods=['GET', 'POST'])
@cross_origin()
def getExistingSessions():
    existingSession = os.listdir('./idirectsessiontokens')
    outputResponse = "{\"msg\" : \"Existing api sessions=" + str(existingSession) + "\"}"
    return (outputResponse,200, {'Content-Type': 'application/json'})

@app.route('/getCurrentSession', methods=['GET'])
@cross_origin()
def getCurrentSession():
    return session[configapi.SESSION_TOKEN_NAME]

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
	version = app.breezeapi_version
	customerDetails = userId + "-" + userName + "-last login: " + lastLogin + " (breeze_connect:" + version + ")"
	return customerDetails

@app.route('/getStockToken', methods=['GET', 'POST'])
@cross_origin()
def getStockToken():
	queryParams = request.args.to_dict()
	(quotesToken,marketDepthToken) = brokerapi.getTokenFromStockName(queryParams)
	print(quotesToken+"<-->"+marketDepthToken)
	return ("{\"quotesToken\":\""+quotesToken+"\"}",200, {'Content-Type': 'application/json'})

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
    hDataJsonDict = brokerapi.getHistoricalData(queryParams)
    #print(hDataJsonDict)
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
	#print("emited data for eventName:" + eventName
	socketio.emit(eventName, json.dumps(data))



if __name__ == '__main__':
	#context = ('local.crt', 'local.key')#certificate and key files
	#app.run(debug=True, ssl_context=context)
	app.run(debug=True)
	socketio.run(app, debug = True)


	
