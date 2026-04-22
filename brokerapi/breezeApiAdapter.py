
# Import Libraries
from breeze_connect import BreezeConnect, config
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

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    from importlib_metadata import metadata


class RightType(Enum):
    call = "CE"
    put = "PE"
    @staticmethod
    def from_str(label):
        label = label.lower()
        if label in ('ce','call'):
            return RightType.call
        elif label in ('pe','put'):
            return RightType.put
        else:
            raise NotImplementedError

class  BreezeApiAdapter(BrokerApiAdapter):

	def __init__(self):
		#global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
		self.api = BreezeConnect(configapi.IDIRECT_API_KEY)
		self.isConnected = False

		if os.path.exists("securityMaster.zip"):
			securityMasterCreateTimestamp = os.path.getctime("securityMaster.zip")
			securityMasterCreateTimeDate = datetime.fromtimestamp(securityMasterCreateTimestamp).date()
			today = datetime.now().date()
			#print(today - securityMasterCreateTimeDate)
			if today > securityMasterCreateTimeDate:
				print("removing stale securityMaster.zip")
				os.remove("securityMaster.zip")
		if not os.path.exists("securityMaster.zip"):
			self.securityMasterResponse = urlopen(config.SECURITY_MASTER_URL)
			securityMasterBytesio = BytesIO(self.securityMasterResponse.read())	
			with open("securityMaster.zip", mode="wb") as file:
				file.write(securityMasterBytesio.getbuffer().tobytes())
				print("wrote new securityMaster.zip")
				file.close()
		else:
			print("using existing securityMaster.zip created on:"+str(securityMasterCreateTimeDate))
		with ZipFile("securityMaster.zip") as securityMasterZipFile:
			self.securityMasterZipFile = securityMasterZipFile
			self.nseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("nse"))
			self.foNseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("nfo"))
			self.bseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("bse"))
		#self.stockScriptdf = pd.read_csv(
		#	config.STOCK_SCRIPT_CSV_URL ,
		#	sep=',',
		#	encoding='utf-8',
		#)
		self.stockScriptdf = pd.read_csv('./instruments/instruments-final.csv' ,sep=',',encoding='utf-8')


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
		file_path = './idirectsessiontokens/*'
		files = sorted(glob.iglob(file_path), key=os.path.getctime, reverse=True)
		if len(files) > 0:
			sessionToken = os.path.basename(files[0])
		return sessionToken
	
	def clearTokenFiles(self):
		try:
			directory_path = './idirectsessiontokens'
			files = os.listdir(directory_path)
			for file in files:
				file_path = os.path.join(directory_path, file)
				if os.path.isfile(file_path) and not file == ".gitignore":
					os.remove(file_path)
			print("All breeze token files deleted successfully as they are invalid.")
		except OSError:
			print("Error occurred while deleting files.")
		return True
	
	def registerFeedCallback(self,callbackFn) -> None:
		self.onMessage = callbackFn
    
	def getLoginUrl(self):
		loginUrl = configapi.IDIRECT_LOGIN_URL + urllib.parse.quote_plus(configapi.IDIRECT_API_KEY)
		return loginUrl
	
	def getSessionTokenName(self):
		return configapi.IDIRECT_SESSION_TOKEN_NAME

	def connect(self,params):
		sessionToken = params.get(configapi.IDIRECT_SESSION_TOKEN_NAME,"no-breezeapi-session")
		if sessionToken == "no-breezeapi-session":
			sessionToken = self.getSessionTokenFromFile()
			if sessionToken == "no-breezeapi-session":
				raise Exception("No valid sessionToken exist")
		else:
			try:
				file_path = './idirectsessiontokens/'+sessionToken
				os.makedirs(os.path.dirname(file_path), exist_ok=True)
				# create file
				with open(file_path, 'x') as fp:
					fp.close()
			except Exception as e:
				print(e)
				print('File already exists')
		self.api.generate_session(api_secret=configapi.IDIRECT_SECRET_KEY,session_token=sessionToken)
		self.api.ws_connect()
		# Assign the callbacks.
		self.api.on_ticks = self.on_ticks
		self.api.subscribe_feeds(get_order_notification=True)
		print("USERID-->" + self.api.user_id)
		self.user_id = self.api.user_id
		self.session_key = self.api.session_key
		self.session_token = sessionToken
		self.isConnected = True
		return sessionToken
	
	def isApiConnected(self):
		return self.isConnected
	
	def getApiVersion(self):
		return "breeze_connect " + metadata.version('breeze_connect')
	
	def getCustomerDetails(self):
		userDetails = self.api.get_customer_details(self.session_token)
		print(userDetails)
		customerDetails = { "Success":{}}
		user = {}
		if (userDetails["Success"] != None):
			user["userid"] = userDetails["Success"]["idirect_userid"]
			user["user_name"] = userDetails["Success"]["idirect_user_name"]
			user["broker"] = "IDIRECT"
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

	def getFnOStocks(self,*searchTuple):
		searchList = list(searchTuple)
		#print(searchList)
		base = r'^{}'
		expr = '(?=.*{})'
		searchRegex = base.format(''.join(expr.format(w) for w in searchList[1:]))
		searchStockType = searchList[0]
		#print(searchRegex)
		#ic(stockScriptdf.columns.values)
		stockScriptdf = self.stockScriptdf
		requiredCol = stockScriptdf[["trading_symbol","ExAllowed","ShortName","CompanyName", "LotSize","idirect_id","zerodha_id","upstox_id","Series","ExpiryDate","StrikePrice","OptionType","InstrumentName"]]
		result = requiredCol.loc[( \
                                            (stockScriptdf["Series"]  == searchStockType) \
                                            & (stockScriptdf["trading_symbol"].str.contains(searchRegex,na=False, case=False)
											   | stockScriptdf["ShortName"].str.contains(searchRegex,na=False, case=False)
                                                | stockScriptdf["CompanyName"].str.contains(searchRegex,na=False, case=False) ) \
                                            ) ].head(10).copy()
		result.rename(columns = {'trading_symbol':'code','ExAllowed':'exchangeCode','ShortName':'stockCode', 'LotSize':'lotSize','Series':'product','ExpiryDate':'expiry','StrikePrice':'strike','OptionType':'right','InstrumentName':'fnoType'}, inplace = True)
		#print(result.to_string())
		result['token'] = result['idirect_id']
		result['fnoType'] = result['fnoType'].str[:3]
		#print(result.head(2).to_string())
		#result = result.apply(self.addFnOStocksAdditionalColumns,axis=1)
		resultJsonStr = result.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		return resultJsonDict
    
	def getBrokerages(self,params):
		stockCode = params.get("stockCode","CNXBAN")
		quantity = params.get("quantity","1")
		priceStr = params.get("price","1")
		action = params.get("action")
		product = params.get("product")
		if params.get("product","").lower() == "option":
			product = "options"
		elif params.get("product","").lower() == "future":
			product = "futures"
		exchangeCode = params.get("exchangeCode","NFO")
		strike = ""
		rightTypeStr = ""
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"

		if exchangeCode == "NFO":
			expiryDateStr = params.get("expiryDate")
			#expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
			expiryDate = datetime.strptime(expiryDateStr, "%Y-%m-%d")
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
		if product.lower() == "option":
			product = "options"
		elif product.lower() == "future":
			product = "futures"
		exchangeCode = params.get("exchangeCode","NFO")
		strike = ""
		rightTypeStr = ""
		orderType = "limit"
		if priceStr == "0":
			orderType = "market"

		if exchangeCode == "NFO":
			expiryDateStr = params.get("expiryDate")
			#expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
			expiryDate = datetime.strptime(expiryDateStr, "%Y-%m-%d")
			if product == "options":
				strike = params.get("strike","NA")
				rightTypeStr = params.get("rightType","NA")
				rightTypeEnum = RightType.from_str(rightTypeStr)
				rightTypeStr = rightTypeEnum.name
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
		if product.lower() == "option":
			product = "options"
		elif product.lower() == "future":
			product = "futures"
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
    
		#orderDetail = getOrderDetails('202310201500017588')

	def addInstrumentIdColumns(self,df_row):
		exchangeCode = df_row['exchange_code']
		stockCode = df_row['stock_code']
		expiryDate = df_row['expiry_date']
		if exchangeCode == "NFO":
			expiryDate = (datetime.strptime(expiryDate,"%d-%b-%Y")).strftime('%Y-%m-%d')
		product = df_row['product_type']
		if product.lower() == 'options':
			product = "OPTION"
		elif product.lower() == 'futures':
			product = "FUTURE"
		strikePrice = df_row['strike_price']
		strikePrice = str(strikePrice).split('.')[0]
		right = df_row['right']
		rightEnum = RightType.from_str(right)
		stockScriptdf = self.stockScriptdf
		requiredCol = stockScriptdf[["ExAllowed","ShortName","trading_symbol","idirect_id","zerodha_id","upstox_id"]]
		result = requiredCol.loc[( \
                                            (stockScriptdf["ExAllowed"] == exchangeCode)
                                            & (stockScriptdf["ShortName"] == stockCode)
											& (stockScriptdf["ExpiryDate"] == expiryDate)
                                            & (stockScriptdf["Series"] == product) 
											& (stockScriptdf["StrikePrice"] == int(strikePrice))
											& (stockScriptdf["OptionType"] == rightEnum.value)
                                            ) ].head(1).copy()
		result.rename(columns = {'trading_symbol':'code'}, inplace = True)
		#print(result.to_string())
		df_row['idirect_id'] = result['idirect_id'].astype(str).item()
		df_row['zerodha_id'] = result['zerodha_id'].astype(str).item()
		df_row['upstox_id'] = result['upstox_id'].astype(str).item()
		df_row['code'] = result['code'].astype(str).item()
		#print(df_row.to_string())
		return df_row
		   
	def getOrdersList(self,params):
		fromDateStrOrig = params.get("orderDate","07-12-2023")
		toDateStrOrig = params.get("orderDate","07-12-2023")
		
		if fromDateStrOrig == "":
			today = datetime.now()
			#show only one day orders
			daysFrom = timedelta(days = 0)
			fromDate = today - daysFrom
			toDate = today
			fromDateStr = fromDate.strftime("%d-%b-%Y")
		else:
			fromDate = datetime.strptime(fromDateStrOrig,"%d-%m-%Y").date()
			toDate = datetime.strptime(toDateStrOrig,"%d-%m-%Y").date()
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
		orderList = self.api.get_order_list(exchange_code="NFO",
														from_date=fromDateStr,
														to_date=toDateStr)
		#print(orderList)
		if orderList is None or orderList.get("Success") is None:
			print(orderList)
			orderList = json.loads('{"Error":"Not connected"}')
		else:
			unfilteredOrderList = orderList.get("Success")
			if(unfilteredOrderList is not None):
				#print(unfilteredOrderList)
				orderListDf = pd.json_normalize(unfilteredOrderList)
				#orderListDf = orderListDf.apply(derivedCol, axis=1)
				#today = datetime.now()    
				#todayStr = today.strftime("%d-%b-%Y")
				orderDateStr = datetime.strptime(fromDateStrOrig,"%d-%m-%Y").date().strftime("%d-%b-%Y")
				#print(todayStr)
				result = orderListDf.loc[( \
												((orderListDf["order_datetime"].str.contains(orderDateStr,na=False, case=False))) \
												) ].copy()
				#print(result.columns.values)
				#print(result[["order_id","order_datetime","stock_code","status","1","2","3"]])
				result = result.apply(self.addInstrumentIdColumns,axis=1)
				result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
				result.sort_values(by='order_datetime_sorting', inplace = True, ascending = False)
				resultJsonStr = result.to_json(orient = "records")
				resultJsonDict = json.loads(resultJsonStr)
				orderList["Success"]=resultJsonDict
		#print(resultJsonDict)
		return orderList
    
    
	def getOpenPositionsList(self):
		portfolioPositionsJson = self.api.get_portfolio_positions()
		openPostionsList = portfolioPositionsJson.get("Success")
		if(openPostionsList is not None):
			positionsListDf = pd.json_normalize(openPostionsList)
			result = positionsListDf.apply(self.addInstrumentIdColumns,axis=1)
			portfolioPositionsJson = result.to_json(orient = "records")
		#ic(portfolioPositions)
		return portfolioPositionsJson
    
    
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
		exchangeCode = params.get("exchangeCode","NFO")
		return self.api.get_margin(exchangeCode)

	def marginCalculator(self,params):
		newPosition = {}
		exchangeCode = params.get("exchangeCode","NFO")
		newPosition["stock_code"] = params.get("stockCode","")
		newPosition["expiry_date"] = params.get("expiryDate","")
		if params.get("product","").lower() == "option":
			newPosition["product"] = "options"
		elif params.get("product","").lower() == "future":
			newPosition["product"] = "futures"
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

