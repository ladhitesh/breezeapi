
# Import Libraries
import upstox_client
from upstox_client.rest import ApiException
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from io import StringIO  
from datetime import datetime, date, timedelta, timezone
from icecream import ic
import json
import os
import pandas as pd
import time
import urllib
import glob
from enum import Enum
import sys
sys.path.append(".")
import configapi
from brokerapi.brokerApiAdapter import BrokerApiAdapter




class RightType(Enum):
    call = "CE"
    put = "PUT"
    @staticmethod
    def from_str(label):
        label = label.lower()
        if label in ('ce','call'):
            return RightType.call
        elif label in ('pe','put'):
            return RightType.put
        else:
            raise NotImplementedError

class  UpstoxApiAdapter(BrokerApiAdapter):

	def __init__(self):
		#global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
		self.loginapi = upstox_client.LoginApi()
		self.isConnected = False

	# Callback to receive ticks.
	def on_ticks(self,ticks):
		if(self.onMessage!=None):
			token = "none"
			interval = ""
			if ticks.get('quotes') == None and ticks.get('sourceNumber') == None:
				#OHLV data
				interval = ticks['interval']
				exchangeCode = ticks['exchange_code']
				stockCode = ticks['stock_code']
				expiryDate = ""
				product = "equity"
				rightType = ""
				strikePrice = ""
				if ticks.get('exchange_code') == "NFO":
					expiryDate = ticks['expiry_date']
					product = "futures"
					if ticks.get('right_type') != None:
						product = "options"
						strikePrice = str(ticks['strike_price']).split('.')[0]
						rightType = RightType.from_str(ticks['right_type']).name
						#print(ticks)
						#print(exchangeCode, stockCode, product,expiryDate,strikePrice,rightType)
						params={}
						params['exchangeCode'] = exchangeCode
						params['stockCode'] = stockCode
						params['productType'] = product
						params['expiryDate'] = expiryDate
						params['strike'] = strikePrice
						params['rightType'] = rightType
						
						(quotesToken, marketDepthToken) = self.getTokenFromStockName(params)
						token = quotesToken.split('!')[1]
					else:
						#print(ticks)
						#print(exchangeCode, stockCode, product,expiryDate,strikePrice,rightType)
						params={}
						params['exchangeCode'] = exchangeCode
						params['stockCode'] = stockCode
						params['productType'] = product
						params['expiryDate'] = expiryDate
						(quotesToken, marketDepthToken) = self.getTokenFromStockName(params)
						token = quotesToken.split('!')[1]
						#print(token,stockCode)
				elif ticks.get('exchange_code') == "NSE":
					#print(exchangeCode, stockCode, "","","","")
					params={}
					params['exchangeCode'] = exchangeCode
					params['stockCode'] = stockCode
					(quotesToken, marketDepthToken) = self.getTokenFromStockName(params)
					token = quotesToken.split('!')[1]
			elif ticks.get('quotes') == "Market Depth":
				#Market Data
				token = ticks['symbol'].split('!')[1]
			elif ticks.get('quotes') == "Quotes Data":
				token = ticks['symbol'].split('!')[1]
				interval = ticks['interval']
			elif ticks.get('sourceNumber') != None:
				#order Notification
				token = "order_notification"
			eventName = token
			if interval != "":
				eventName = token + "-" + interval
				ticks['token'] = token
			self.onMessage(eventName,ticks)

	def getSessionTokenFromFile(self):
		sessionToken = ""
		file_path = './upstoxsessiontokens/access_token'
		with open(file_path, 'r') as file:
			sessionToken = file.read()
		print("session token from file" + sessionToken)
		return sessionToken
	
	def clearTokenFiles(self):
		try:
			directory_path = './upstoxsessiontokens'
			files = os.listdir(directory_path)
			for file in files:
				file_path = os.path.join(directory_path, file)
				if os.path.isfile(file_path):
					os.remove(file_path)
			print("All upstox token files deleted successfully as they are invalid.")
		except OSError:
			print("Error occurred while deleting files.")
		return True
	
	def registerFeedCallback(self,callbackFn) -> None:
		self.onMessage = callbackFn
    
	def getLoginUrl(self):
		loginUrl = configapi.UPSTOX_LOGIN_URL + urllib.parse.quote_plus(configapi.UPSTOX_API_KEY)
		return loginUrl
	
	def getSessionTokenName(self):
		return configapi.UPSTOX_SESSION_TOKEN_NAME

	def connect(self,params):
		sessionToken = params.get(configapi.UPSTOX_SESSION_TOKEN_NAME,"no-upstox-session")
		if self.isConnected == True:
			print("API already connected.No doing anything in connect call.")
			return self.session_token
		reConnect = False
		if sessionToken == "no-upstox-session":
			sessionToken = self.getSessionTokenFromFile()
			self.session_token = sessionToken
			self.session_key = sessionToken
			if sessionToken == "no-upstox-session":
				raise Exception("No valid upstox sessionToken exist")
			else:
				reConnect = True
		else:
			try:
				file_path = './upstoxsessiontokens/'+sessionToken
				#os.makedirs(os.path.dirname(file_path), exist_ok=True)
				# create file
				#with open(file_path, 'x') as fp:
				#	fp.close()
			except Exception as e:
				print(e)
				print('File already exists')

		if not reConnect :
			try:
				token = self.loginapi.token("2", code=sessionToken, client_id=configapi.UPSTOX_API_KEY, client_secret=configapi.UPSTOX_SECRET_KEY, redirect_uri=configapi.UPSTOX_REDIRECT_URL, grant_type="authorization_code")
				self.session_key = token.access_token
				self.session_token = token.access_token
				try:
					file_path = './upstoxsessiontokens/access_token'
					os.makedirs(os.path.dirname(file_path), exist_ok=True)
					# create file
					with open(file_path, 'w') as fp:
						fp.write(token.access_token)
						fp.close()
				except Exception as e:
					print(e)
					print('File already exists')
			except Exception as e:	
				print("Error getting token using code from file")
				print(e)

		#fetch customer details using token from file
		configuration = upstox_client.Configuration()
		configuration.access_token = self.session_token
		self.apiversion = "2.0"
		self.userapi = upstox_client.UserApi(upstox_client.ApiClient(configuration))
		try:
			userDetails = self.userapi.get_profile(self.apiversion)
			self.orderapi = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
			self.portfolioapi = upstox_client.PortfolioApi(upstox_client.ApiClient(configuration))
		except Exception as e:
			print("Error while fetching customer details in UPSTOX login flow")
			print(e)
			raise e
		if userDetails.status == "success":
			userProfile = userDetails.data
			print(userProfile)
			self.user_id = userProfile.user_id
			self.user_name = userProfile.user_name
		print("USERID-->" + self.user_id)
		print("USERNAME-->" + self.user_name)

		
		self.isConnected = True
		return self.session_token
	
	def isApiConnected(self):
		return self.isConnected
	
	def getCustomerDetails(self):
		userDetails = self.userapi.get_profile(self.apiversion)
		print(userDetails)
		customerDetails = { "Success":{}}
		user = {}
		status = userDetails.status
		if status == "success":
			userProfile = userDetails.data
			print(userProfile)
			user["idirect_userid"] = userProfile.user_id
			user["idirect_user_name"] = userProfile.user_name
			user["idirect_lastlogin_time"] = userProfile.broker
		customerDetails["Success"] = user
		print(customerDetails)
		return customerDetails

	def addFnOStocksAdditionalColumns(self,df_row):
		codeArr = df_row["code"].split("-", 2)
		fnoType = codeArr[0]
		stockCode =  codeArr[1]
		#print(codeArr)
		if fnoType == "FUT":
			expiry = codeArr[2]
			strike = ""
			right = ""
			product = "futures"
		else:
			codeArrRevSplit = codeArr[2].rsplit("-", 2)
			#print(codeArrRevSplit)
			expiry = codeArrRevSplit[0]  #'26-Oct-2023'
			strike = codeArrRevSplit[1]
			right = codeArrRevSplit[2]
			product="options"
		#print(df_row)
		df_row["fnoType"] = fnoType
		df_row["expiry"] = expiry
		df_row["strike"] = strike
		df_row["right"] = right
		df_row["product"] = product
		return df_row

	def getFnOStocks(self,*searchList):
		base = r'^{}'
		expr = '(?=.*{})'
		searchRegex = base.format(''.join(expr.format(w) for w in searchList))
		#ic(searchRegex)
		#ic(stockScriptdf.columns.values)
		stockScriptdf = self.stockScriptdf
		requiredCol = stockScriptdf[["TK","CD","EC","SC","SN", "LS"]]
		result = requiredCol.loc[( \
										  (stockScriptdf["SG"]  == "DERIVATIVE") \
										  & (stockScriptdf["CD"].str.contains(searchRegex,na=False, case=False)
											   | stockScriptdf["SN"].str.contains(searchRegex,na=False, case=False) ) \
										 ) ].head(10).copy()
		result.rename(columns = {'TK':'token', 'CD':'code','EC':'exchangeCode','SC':'stockCode', 'LS':'lotSize'}, inplace = True)
		result = result.apply(self.addFnOStocksAdditionalColumns,axis=1)
		resultJsonStr = result.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		return resultJsonDict
    
	def getBrokerages(self,params):
		stockCode = params.get("stockCode","CNXBAN")
		quantity = params.get("quantity","1")
		priceStr = params.get("price","1")
		action = params.get("action")
		product = params.get("product")
		exchangeCode = params.get("exchangeCode","NFO")
		strike = ""
		rightTypeStr = ""
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"

		if exchangeCode == "NFO":
			expiryDateStr = params.get("expiryDate")
			expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
			if product == "options":
				strike = params.get("strike","NA")
				rightTypeStr = params.get("rightType","NA")
				rightTypeEnum = RightType.from_str(rightTypeStr)
				rightTypeStr = rightTypeEnum.name
		
		expiry = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
		brokerages = self.api.preview_order( stock_code = stockCode,
														exchange_code = exchangeCode,
														product = product,
														order_type = orderType,
														price = priceStr,
														action = action,
														quantity = quantity,
														expiry_date=expiry,
														right=rightTypeStr,
														strike_price=strike,
														specialflag = "N")
		return brokerages
    
	def placeOrder(self,params):
		#stockcode,exchangeCode,product,action,orderType,stoploss,quantity,price,expiryDate,rightStr,strike
		stockCode = params.get("stockCode","CNXBAN")
		quantity = params.get("quantity","1")
		priceStr = params.get("price","1")
		stoploss = params.get("stoploss","")
		action = params.get("action")
		product = params.get("product")
		exchangeCode = params.get("exchangeCode","NFO")
		strike = ""
		rightTypeStr = ""
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"

		if exchangeCode == "NFO":
			expiryDateStr = params.get("expiryDate")
			expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
			if product == "options":
				strike = params.get("strike","NA")
				rightTypeStr = params.get("rightType","NA")
				rightTypeEnum = RightType.from_str(rightTypeStr)
				rightTypeStr = rightTypeEnum.name

		body = self.orderapi.PlaceOrderRequest()
		# Place order
		todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
		expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
		buy_order = self.api.place_order(stock_code=stockCode,
													exchange_code=exchangeCode,
													product=product,
													action=action,
													order_type=orderType,
													stoploss=stoploss,
													quantity=quantity,
													price=priceStr,
													validity="day",
													validity_date=todayStr,
													disclosed_quantity="0",
													expiry_date=expiryStr,
													right=rightTypeStr,
													strike_price=strike)

		print(buy_order)
		return buy_order
	
	def squareOffOrder(self,params):
		
		stockCode = params.get("stockCode","CNXBAN")
		quantity = params.get("quantity","1")
		priceStr = params.get("price","1")
		stoploss = params.get("stoploss","")
		action = params.get("action")
		product = params.get("product")
		exchangeCode = params.get("exchangeCode","NFO")
		strike = ""
		rightTypeStr = ""
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"

		if exchangeCode == "NFO":
			expiryDateStr = params.get("expiryDate")
			expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
			if product == "options":
				strike = params.get("strike","NA")
				rightTypeStr = params.get("rightType","NA")
				rightTypeEnum = RightType.from_str(rightTypeStr)
				rightTypeStr = rightTypeEnum.name
		# Place order
		todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
		expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
		buy_order = self.api.square_off(stock_code=stockCode,
													exchange_code=exchangeCode,
													product=product,
													action=action,
													order_type=orderType,
													stoploss=stoploss,
													quantity=quantity,
													price=priceStr,
													validity="day",
													validity_date=todayStr,
													disclosed_quantity="0",
													expiry_date=expiryStr,
													right=rightTypeStr,
													strike_price=strike)

		print(buy_order)
		return buy_order

    
	def modifyOrder(self,params):
		#orderId,exchangeCode,orderType,stopLoss,quantity,price
		orderIdStr = params.get("orderId","")
		exchangeCode = params.get("exchangeCode","NFO")
		priceStr = params.get("price","")
		quantityStr = params.get("quantity","")
		stopLossStr = params.get("stoploss","0")
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"
		modifyResult = self.api.modify_order(order_id=orderIdStr,
														 exchange_code=exchangeCode,
														 order_type=orderType,
														 stoploss=stopLossStr,
														 quantity=quantityStr,
														 price=priceStr,
														 validity="day",
														 disclosed_quantity="0")
		print(modifyResult)
		return modifyResult

		'''
    {'Success': {'message': 'Successfully Modified the order', 'order_id': '202310201500017588'}, 'Status': 200, 'Error': None}
    '''

    
	def cancelOrder(self,orderRef):
		cancelResult = self.api.cancel_order(exchange_code="NFO",
														 order_id=orderRef)
		print(cancelResult)
		return cancelResult

		'''
    {'Success': {'order_id': '202310201500017588', 'message': 'Your Order Canceled Successfully'}, 'Status': 200, 'Error': None}
    '''
    
	def getOrderDetails(self,orderId):
		orderDetail = self.api.get_order_detail(exchange_code="NFO",order_id=orderId)
		print(orderDetail)
		return orderDetail
	
	def getOrdersList(self,params):
		fromDateStr = params.get("orderDate","22-09-2024")
		toDateStr = params.get("orderDate","22-09-2024")
		
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

		#if today is holiday and you put an order, it gets scheduled for next working day
		#this future day hack is to fetch that order so it can be viewed, modified, or cancelled on holidays
		moveBackDays = 0
		moveAheadDays = 0
		if(fromDate.weekday() == 6):
			moveBackDays = 1
		if(toDate.weekday() == 5):
			moveAheadDays = 2
		else:
			if(toDate.weekday() == 6):
				moveAheadDays = 1
		if(not moveBackDays == 0) or not (moveAheadDays == 0):
			fromDate = fromDate - timedelta(days = moveBackDays)
			toDate = toDate + timedelta(days = moveAheadDays)
		toDateStr = toDate.strftime('%Y-%m-%dT23:00:00.000Z')
		fromDateStr = fromDate.strftime('%Y-%m-%dT01:00:00.000Z')
		print("fetching orders from: "+fromDateStr+" to "+toDateStr)		
		orderList = self.orderapi.get_order_book(self.apiversion)
		print(orderList)
		print(orderList.data[0])
		print(orderList.data[0].to_dict()["order_id"])
		if orderList is None or  orderList.status == "error":
			print(orderList)
			orderList = json.loads('{"Error":"Not connected"}')
		else:
			unfilteredOrderList = orderList.data
			#print(type(unfilteredOrderList))
			#print(unfilteredOrderList)
			if(unfilteredOrderList is not None):
				orderListDf = pd.DataFrame([o.to_dict() for o in unfilteredOrderList])
				print(orderListDf)
				#orderListDf = orderListDf.apply(derivedCol, axis=1)
				today = datetime.now()    
				todayStr = today.strftime("%Y-%m-%d")
				orderDateStr = todayStr
				#orderDateStr = "2024-09-22"
				#print(todayStr)
				result = orderListDf.loc[( \
												((orderListDf["order_timestamp"].str.contains(orderDateStr,na=False, case=False))) \
												) ].copy()
				#print(result.columns.values)
				#print(result[["order_id","order_datetime","stock_code","status","1","2","3"]])
				result["order_timestamp_sorting"] = pd.to_datetime(result['order_timestamp'])
				result.sort_values(by='order_timestamp_sorting', inplace = True, ascending = False)
				resultJsonStr = result.to_json(orient = "records")
				resultJsonDict = json.loads(resultJsonStr)
				print(resultJsonDict)
				mappedResult = mapOrderlistResult(resultJsonDict)
				#orderList["Success"]=resultJsonDict
		#print(resultJsonDict)
		returnValue = {}
		returnValue["Success"] = resultJsonDict
		return returnValue
    
	def mapOrderlistResult(orderList):
		mappedOrderList = []
		return mappedOrderList

	def mapOrderResult(order):
		mappedOrder = {}
		return mappedOrder
    
	def getOpenPositionsList(self):
		portfolioPositions = self.api.get_portfolio_positions()
		#ic(portfolioPositions)
		return portfolioPositions
    
    
	def getTradesList(self,params):
		fromDateStr = params.get("fromDate",datetime.now().strftime("%d-%b-%Y"))
		toDateStr = params.get("toDate",datetime.now().strftime("%d-%b-%Y"))
		fromDate = datetime.strptime(fromDateStr, "%d-%b-%Y")
		toDate = datetime.strptime(toDateStr, "%d-%b-%Y")
		exchangeCode = "NFO" #get only fno pnl
		productCode=""
		action=""
		stockCode=""
		fromStr = fromDate.strftime('%Y-%m-%dT06:00:00.000Z')
		toStr = toDate.strftime('%Y-%m-%dT18:00:00.000Z')

		tradesList = self.api.get_trade_list(from_date=fromStr,
														 to_date=toStr,
														 exchange_code=exchangeCode,
														 product_type=productCode,
														 action=action,
														 stock_code=stockCode)
		return tradesList
	
	def pnlMultiplier(self,row):
		pnlMultilpier = 1
		if row["action"] == "Buy":
			pnlMultilpier = -1
		row["sum_total_cost"] = pnlMultilpier * row["sum_total_cost"]
		row["total_cost_with_taxes"] = pnlMultilpier * row["total_cost_with_taxes"]
		return row

	def costCalculator(self,row):
		row["total_cost_with_taxes"] = row["sum_total_cost"]
		if row["action"] == "Buy":
			row["total_cost_with_taxes"] = row["total_cost_with_taxes"] + row["sum_total_taxes"]
		else:
			row["total_cost_with_taxes"] = row["total_cost_with_taxes"] - row["sum_total_taxes"]
		return row
	
	def getPnl(self,params):
		fromDateStr = params.get("fromDate",datetime.now().strftime("%d-%b-%Y"))
		toDateStr = params.get("toDate",datetime.now().strftime("%d-%b-%Y"))
		fromDate = datetime.strptime(fromDateStr, "%d-%b-%Y")
		toDate = datetime.strptime(toDateStr, "%d-%b-%Y")
		exchangeCode = "NFO" #get only fno pnl
		tradesListJsonDict = self.getTradesList(params)
		if tradesListJsonDict is None:
			print(tradesListJsonDict)
			tradesListJsonDict = json.loads('{"Error":"Not connected"}')
			return tradesListJsonDict
		
		if not tradesListJsonDict["Success"]:
			print("No Trades taken between "+fromDateStr+"-"+toDateStr)
			print(tradesListJsonDict)
			return tradesListJsonDict
		tradesListDf = pd.json_normalize(tradesListJsonDict["Success"])
		tradesListDf["quantity"] = tradesListDf["quantity"].astype(float)
		tradesListDf["average_cost"] = tradesListDf["average_cost"].astype(float)
		tradesListDf["total_taxes"] = tradesListDf["total_taxes"].astype(float)
		tradesListDf["total_cost"] = tradesListDf["quantity"] * tradesListDf["average_cost"]
		#print(tradesListDf)
		groupbyTradesListDf = tradesListDf.groupby(["stock_code", "action"], as_index=False)\
		.agg(quantity=("quantity","sum"),sum_total_cost=("total_cost","sum"),sum_total_taxes=("total_taxes","sum"))
		groupbyTradesListDf = groupbyTradesListDf.apply(self.costCalculator,axis=1)
		groupbyTradesListDf = groupbyTradesListDf.apply(self.pnlMultiplier,axis=1)
		#print(groupbyTradesListDf)
		#remove open postion total cost from all trades cost
		openPositionsDict = self.getOpenPositionsList()
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
		return tradesListJsonDict
	
	def getFunds(self):
		return self.api.get_funds()
	
	def getStockNameFromToken(self,token):
		return self.api.get_data_from_stock_token_value(token)

	def getTokenFromStockName(self,params):
		stockCode = params.get("stockCode","CNXBAN")
		exchangeCode = params.get("exchangeCode","NFO")
		productType = params.get("productType","")
		strike = params.get("strike","")
		expiryDateStr = params.get("expiryDate","")
		rightTypeStr = params.get("rightType","")
		#expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
		#rightType = breezeapi.RightType.from_str(rightTypeStr)
		return self.api.get_stock_token_value(exchangeCode, stockCode, productType, expiryDateStr, strike, rightTypeStr, True, True)
    
	def spoofTicks(self,ticks,count,interval):
		for i in range(count):
			time.sleep(interval)
			self.on_ticks(ticks)

    
		# Feeds Subscription

	def subscribeQuotes(self,token, interval):
		#"4.1!2885"
		quotesToken = "4.1!"+token
		return self.subscribeFeed(quotesToken,interval)
    
	def subscribeMarketDepth(self,token):
		#"4.2!2885"
		marketDepthToken = "4.2!"+token
		return self.subscribeFeed(marketDepthToken,"")
    
	def unsubscribeQuotes(self,token, interval):
		#"4.1!2885"
		quotesToken = "4.1!"+token
		return self.unsubscribeFeed(quotesToken,interval)
    
	def unsubscribeMarketDepth(self,token):
		#"4.2!2885"
		marketDepthToken = "4.2!"+token
		return self.unsubscribeFeed(marketDepthToken,"")

	def subscribeFeed(self,codedToken, interval):
		return self.api.subscribe_feeds(stock_token=codedToken,interval=interval)   

	def unsubscribeFeed(self,codedToken, interval):
		return self.api.unsubscribe_feeds(stock_token=codedToken,interval=interval) 

	def disconnectFeed(self):
		self.api.unsubscribe_feeds(get_order_notification=True)
		self.api.ws_disconnect()

	def getHistoricalData(self, params ):
		pass

	def getHistoricalData1(self, params ):
		interval = params.get("interval","15minute")
		fromDateStr = params.get("fromDate","2023-11-01T00:00:00.000Z")
		toDateStr = params.get("toDate","2023-11-01T00:00:00.000Z")
		stockCode = params.get("stockCode","CNXBAN")
		exchangeCode = params.get("exchangeCode","NSE")
		product = params.get("product","")
		expiry = params.get("expiry","")
		rightStr = params.get("right","")
		strikePrice = params.get("strike","")
		hDataJsonDict = self.api.get_historical_data_v2(interval, fromDateStr, toDateStr, stockCode, exchangeCode, product, expiry, rightStr, strikePrice)
		#print(hDataJsonDict)
		if hDataJsonDict is None:
			print(hDataJsonDict)
			hDataJsonDict = json.loads('{"Error":"Not connected"}')
			return hDataJsonDict

		if not hDataJsonDict.get("Success") or hDataJsonDict.get("Error"):
			print("Invalid Historical data")
			print(hDataJsonDict)
			return hDataJsonDict

		hDataDf = pd.json_normalize(hDataJsonDict["Success"])
		#'2023-11-01 12:30:00'
		hDataDf["time"] = hDataDf['datetime'].apply(lambda x: datetime.strptime(x,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
		hDataDf["value"] = hDataDf["volume"]
		resultJsonStr = hDataDf.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		hDataJsonDict["Success"]=resultJsonDict
		return hDataJsonDict

	def getMargin(self,params):
		fundsAndMargin = self.userapi.get_user_fund_margin("2")
		print(fundsAndMargin)
		return fundsAndMargin

	def marginCalculator(self,params):
		newPosition = {}
		exchangeCode = params.get("exchangeCode","NFO")
		newPosition["stock_code"] = params.get("stockCode","")
		newPosition["expiry_date"] = params.get("expiryDate","")
		newPosition["product"] = params.get("product","")
		newPosition["action"] = params.get("action","")
		newPosition["price"] = params.get("price","")
		newPosition["quantity"] = params.get("quantity","")
		newPosition["strike_price"] = params.get("strike","")
		rightTypeStr = params.get("rightType","")
		if not rightTypeStr == "":
			rightTypeEnum = RightType.from_str(rightTypeStr)
			rightTypeStr = rightTypeEnum.name
		newPosition["right"] = rightTypeStr
		includeOpenPostions = params.get("includeOpenPositions","")
		if includeOpenPostions.lower() == "true":
			includeOpenPostions = True
		includePendingOrders = False
		#open positions
		openPositionsList = []
		if includeOpenPostions:
			openPositionsDictList = self.getOpenPositionsList()
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
			orderList =  self.getOrdersList(fromDate,toDate)
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
		return self.api.margin_calculator(listOfPositions,"NFO")

	def getNseStocks(self,stockName):
		nseSecuritiesDf = pd.read_csv(self.nseFile, sep=',', engine='python')
		#print(dataframe.keys())
		filteredData = (nseSecuritiesDf[' "CompanyName"'].str.contains(stockName, na=False, case=False)) & (nseSecuritiesDf['Token'] != '0')
		requiredColumns = nseSecuritiesDf[[' "ExchangeCode"',' "CompanyName"',' "ShortName"','Token']]
		result = requiredColumns.loc[filteredData].copy()
		result.rename(columns = {' "ExchangeCode"':'ExchangeCode', ' "CompanyName"':'CompanyName',
										 ' "ShortName"':'ShortName'}, inplace = True)
		#print(result)
		#print(result.to_json(orient = "records"))
		return (result.to_json(orient = "records"))  


def test():
	result = myapi.getFnOStocks("oct","26","cnx", "43500","ce")
	print(result)

def main():
	print("Hello World!")
	global myapi
	myapi = BreezeApiAdapter()
	test()


if __name__ == "__main__":
    main() 

