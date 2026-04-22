
# Import Libraries
from http.client import responses
import logging
from kiteconnect import KiteConnect
from kiteconnect import KiteTicker
from kiteconnect.exceptions import KiteException
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

#logging.basicConfig(level=logging.DEBUG)

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

class OrderStatus(Enum):
	requested = "requested"
	pending = "pending"
	ordered = "ordered"
	executed = "executed"
	rejected = "rejected"
	cancelled = "cancelled"
	failed = "failed"

	#https://upstox.com/developer/api-documentation/appendix/order-status
	@staticmethod
	def from_str(label):
		label = label.lower()
		if label in ('validation pending','modify pending','trigger pending','modify validation pending','cancel pending','open pending'):
			return OrderStatus.pending
		elif label in ('put order req received','modify after market order req received','after market order req received'):
			return OrderStatus.requested
		elif label in ('cancelled after market order','cancelled'):
			return OrderStatus.cancelled
		elif label in ('open','modified','not cancelled','not modified'):
			return OrderStatus.ordered
		elif label in ('complete'):
			return OrderStatus.executed
		elif label in ('rejected'):
			return OrderStatus.rejected
		else:
			raise NotImplementedError
		
class  KiteApiAdapter(BrokerApiAdapter):

	def __init__(self):
		#global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
		self.api:KiteConnect = KiteConnect(configapi.KITE_API_KEY,debug=False)
		self.isConnected = False
		self.stockScriptdf = pd.read_csv('./instruments/instruments-final.csv' ,sep=',',encoding='utf-8')
		connectBroker:bool = True
		if connectBroker:
			try:
				sessionToken = ""
				file_path = './kitesessiontokens/access_token'
				files = sorted(glob.iglob(file_path), key=os.path.getctime, reverse=True)
				with open(file_path, 'r') as file:
					sessionToken = file.read()
				print("session token from file: " + sessionToken)
				self.api.set_access_token(sessionToken)
				print("calling user profile api to check if access token is still valid")
				userProfile = self.api.profile()
				self.session_token = sessionToken
				self.session_key = sessionToken
				self.user_id = userProfile.get("user_id")
				self.user_name = userProfile.get("user_name")
				print("USERID-->" + self.user_id)
				print("USERNAME-->" + self.user_name)
				self.isConnected = True
			except Exception as e:
				print("Error occured while using existing session token from file to initialize kite api")
				print(e)

	# Callback to receive ticks. Use on_order_update(ws, data) for order notification
	def on_ticks(self,ticks):
		if(self.onMessage!=None):
			token = "none"
			interval = ""
			mode = ticks[0].get('mode') #full,ltp,quote
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

	def on_order_update(self, data):
		print("Order update : {}".format(data))

	def getSessionTokenFromFile(self):
		sessionToken = ""
		file_path = './kitesessiontokens/access_token'
		files = sorted(glob.iglob(file_path), key=os.path.getctime, reverse=True)
		with open(file_path, 'r') as file:
			sessionToken = file.read()
		print("session token from file: " + sessionToken)
		return sessionToken
	
	def clearTokenFiles(self):
		try:
			directory_path = './kitesessiontokens'
			files = os.listdir(directory_path)
			for file in files:
				file_path = os.path.join(directory_path, file)
				if os.path.isfile(file_path) and not file == ".gitignore":
					os.remove(file_path)
			print("All kite(zerodha) token files deleted successfully as they are invalid.")
		except OSError:
			print("Error occurred while deleting files.")
		return True

	def registerFeedCallback(self,callbackFn) -> None:
		self.onMessage = callbackFn

	def getLoginUrl(self):
		loginUrl = self.api.login_url()
		return loginUrl
	
	def getSessionTokenName(self):
		return configapi.KITE_SESSION_TOKEN_NAME
    
	def connect(self,params):
		if self.isConnected == True:
			print("API already connected. Not doing anything in connect call.")
			return self.session_token
		reConnect = False
		sessionToken = params.get(configapi.KITE_SESSION_TOKEN_NAME.split(".")[1],"no-kite-session")
		if sessionToken == "no-kite-session":
			sessionToken = self.getSessionTokenFromFile()
			token = self.api.generate_session(request_token=sessionToken,api_secret=configapi.KITE_SECRET_KEY)
			self.session_key = token.get('access_token')
			self.session_token = token.get('access_token')
			if sessionToken == "no-kite-session":
				raise Exception("No valid kite sessionToken exist")
			else:
				reConnect = True
		else:
			try:
				file_path = './kitesessiontokens/'+sessionToken
				#os.makedirs(os.path.dirname(file_path), exist_ok=True)
				# create file
				#with open(file_path, 'x') as fp:
				#	fp.close()
			except Exception as e:
				print(e)
				print('File already exists')

		if not reConnect :
			try:
				#token = self.loginapi.token("2", code=sessionToken, client_id=configapi.UPSTOX_API_KEY, client_secret=configapi.UPSTOX_SECRET_KEY, redirect_uri=configapi.UPSTOX_REDIRECT_URL, grant_type="authorization_code")
				self.api : KiteConnect = KiteConnect(api_key=configapi.KITE_API_KEY,debug=False)
				token = self.api.generate_session(request_token=sessionToken,api_secret=configapi.KITE_SECRET_KEY)
				print("token obtained after generate session api call")
				print(token)
				self.session_key = token.get('access_token')
				self.session_token = token.get('access_token')
				try:
					file_path = './kitesessiontokens/access_token'
					os.makedirs(os.path.dirname(file_path), exist_ok=True)
					# create file
					with open(file_path, 'w') as fp:
						fp.write(token.get('access_token'))
						fp.close()
				except Exception as e:
					print(e)
					print('File already exists')
			except Exception as e:	
				print("Error getting token using code from file")
				print(e)

		#fetch customer details using token from file
		userProfile = {}
		try:
			userProfile:dict = self.api.profile()
			#print(userProfile)
			'''
			#zerodha websocket now available in personal(free) version api
			try:
				self.kws = KiteTicker(configapi.KITE_API_KEY, self.session_token)
				self.kws.on_ticks = self.on_ticks
				self.kws.on_order_update = self.on_order_update
				self.kws.connect()
			except Exception as e:
					print('Error while connecting to zerodha websocket')
					print(e)
			'''
			'''
			self.orderapi:upstox_client.OrderApi = upstox_client.OrderApi(upstox_client.ApiClient(configuration))
			self.portfolioapi:upstox_client.PortfolioApi = upstox_client.PortfolioApi(upstox_client.ApiClient(configuration))
			self.marketHolidaysapi:upstox_client.MarketHolidaysAndTimingsApi = upstox_client.MarketHolidaysAndTimingsApi(upstox_client.ApiClient(configuration))
			self.chargeApi:upstox_client.ChargeApi = upstox_client.ChargeApi(upstox_client.ApiClient(configuration))
			self.pnlApi:upstox_client.TradeProfitAndLossApi = upstox_client.TradeProfitAndLossApi(upstox_client.ApiClient(configuration))
			self.portfolioStreamer = upstox_client.PortfolioDataStreamer(upstox_client.ApiClient(configuration),order_update=True,position_update=True,holding_update=False)
			self.portfolioStreamer.on("message", self.on_ticks)
			self.portfolioStreamer.connect()
			self.marketdataStreamer = upstox_client.MarketDataStreamerV3(upstox_client.ApiClient(configuration))
			self.marketdataStreamer.on("message", self.on_ticks)
			self.marketdataStreamer.connect()
			time.sleep(5)
			self.marketdataStreamer.subscribe(["NSE_INDEX|Nifty Bank"], "ltpc")
			'''
		except Exception as e:
			print("Error while fetching customer details in KITE login flow")
			print(e)
			raise e
		#print("checking status of userdetails")
		#print(userProfile)
		if userProfile:
			#print("User profile not empty")
			#print(userProfile.get("user_id"))
			self.user_id = userProfile.get("user_id")
			self.user_name = userProfile.get("user_name")
		print("USERID-->" + self.user_id)
		print("USERNAME-->" + self.user_name)

		
		self.isConnected = True
		return self.session_token
	
	def isApiConnected(self):
		return self.isConnected
	
	def getApiVersion(self):
		return "kiteconnect " + metadata.version('kiteconnect')
		
	def getCustomerDetails(self):
		userProfile = self.api.profile()
		#print(userProfile)
		customerDetails = { "Success":{}}
		user = {}
		if userProfile:
			user["userid"] = userProfile.get("user_id")
			user["user_name"] = userProfile.get("user_name")
			user["broker"] = userProfile.get("broker")
		customerDetails["Success"] = user
		print(customerDetails)
		return customerDetails

	'''
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
	'''
	
	def getInstrumentDetailsByInstruId(self,zerodha_id):
		print(f"Populating values based on zerodha id: {zerodha_id}")
		stockScriptdf = self.stockScriptdf
		#stockScriptdf["zerodha_id"] = stockScriptdf["zerodha_id"].astype(str)
		requiredCol = stockScriptdf[["ExAllowed","ShortName","tradingsymbol","trading_symbol","idirect_id","zerodha_id","upstox_id","Series"]]
		result = requiredCol.loc[( \
                                            (stockScriptdf["zerodha_id"].astype(str) == zerodha_id)
                                          	) ].head(1).copy()
		result.rename(columns = {'trading_symbol':'code','tradingsymbol':'zerodha_tradingsymbol'}, inplace = True)
		print(result.to_string())
		response = {}
		if not result.empty:
			response['token'] = result['idirect_id'].astype(str).item()
			response['idirect_id'] = result['idirect_id'].astype(str).item()
			response['zerodha_id'] = result['zerodha_id'].astype(str).item()
			response['upstox_id'] = result['upstox_id'].astype(str).item()
			response['code'] = result['code'].astype(str).item()
			response['zerodha_tradingsymbol'] = result['zerodha_tradingsymbol'].astype(str).item()
			product = result['Series'].astype(str).item()
			if product.lower() == 'option':
				product = "OPTIONS"
			elif product.lower() == 'future':
				product = "FUTURES"
			response['product_type'] = product
		else:
			print(f"Cannot find data for zerodha id: {zerodha_id}")
		#print(df_row.to_string())
		return response
	
	def addInstrumentIdColumns(self,df_row):
		print(df_row.index)
		print(df_row.to_dict())
		print('zerodha_id' in df_row.index)
		if 'zerodha_id' in df_row.index :
			zerodha_id = str(df_row["zerodha_id"])
			response = self.getInstrumentDetailsByInstruId(zerodha_id)
			df_row['idirect_id'] = response['idirect_id']
			df_row['upstox_id'] = response['upstox_id']
			df_row['code'] = response['code']
			df_row['product_type'] = response['product_type']
			return df_row
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
		result = result.apply(self.addInstrumentIdColumns,axis=1)
		resultJsonStr = result.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		return resultJsonDict
    
	def getBrokerages(self,params):
		quantity = params.get("quantity","1")
		priceStr = params.get("price","0")
		action = params.get("action")
		exchangeCode = params.get("exchangeCode","NFO")
		orderType = "LIMIT"
		if priceStr == "0" or priceStr == "":
			orderType = "MARKET"
			priceStr = "0.0"

		zerodha_id = params.get("zerodha_id","")
		instruDetails = self.getInstrumentDetailsByInstruId(zerodha_id)
		order = {}
		order["exchange"] =  "NFO"
		order["tradingsymbol"] =  instruDetails.get('zerodha_tradingsymbol')
		order["transaction_type"] = str(action).upper()
		order["variety"] = "regular"
		order["product"] = "NRML"
		order["order_type"] = orderType
		order["quantity"] = int(quantity)
		order["price"] = float(priceStr)
		#order["trigger_price"] =  0
		#order["mode"] =  "compact"

		try:
			#print(order)
			brokerageResponse = self.api.order_margins([order])
			#print(brokerageResponse)
			brokerage = brokerageResponse[0]["charges"]
			print(brokerage)
			returnData = '"total_brokerage":"'+str("{:.2f}".format(brokerage["total"]))+'"'
			returnData = returnData +','+'"brokerage":"'+str("{:.2f}".format(brokerage["brokerage"]))+'"'
			returnData = returnData +','+'"stamp_duty":"'+str("{:.2f}".format(brokerage["stamp_duty"]))+'"'
			returnData = returnData +','+'"stt":"'+str("{:.2f}".format(brokerage["transaction_tax"]))+'"'
			returnData = returnData +','+'"gst":"'+str("{:.2f}".format(brokerage["gst"]["total"]))+'"'
			returnData = returnData +','+'"exchange_turnover_charges":"'+str("{:.2f}".format(brokerage["exchange_turnover_charge"]))+'"'
			returnData = returnData +','+'"sebi_charges":"'+str("{:.2f}".format(brokerage["sebi_turnover_charge"]))+'"'
			response = '{"Success":{'+returnData+'}}'
			#print(response)
			response = json.loads(response)
		except Exception as e:
			print(e)
			response = '{"Error":"Check error in server logs"}'
			#print(response)
			response = json.loads(response)
		print(response)
		return response
	
	def placeOrder(self,params):
		#stockcode,exchangeCode,product,action,orderType,stoploss,quantity,price,expiryDate,rightStr,strike
		quantity = int(params.get("quantity","1"))
		price = float(params.get("price","1"))
		stoploss = float(params.get("stoploss","0"))
		action = params.get("action").upper()
		instrumentId = params.get("zerodha_id","")
		if instrumentId:
			responseDict = self.getInstrumentDetailsByInstruId(instrumentId)
			zerodha_tradingsymbol = responseDict.get("zerodha_tradingsymbol","")
			print("zerodha_tradingsymbol: " + zerodha_tradingsymbol)
		exchangeCode = "NFO"
		orderType = "LIMIT"
		if price == 0:
			orderType = "MARKET"
		amoOrder = False
		'''
		try:
			marketResponse:upstox_client.GetMarketStatusResponse = self.marketHolidaysapi.get_market_status("NFO")
			marketStatus:upstox_client.MarketStatusData = marketResponse.data
			if not marketStatus.status == "NORMAL_OPEN":
				amoOrder = True
		except Exception as e:
			print(e)
			print("Unable to determine market open status to place new order. Placing regular order")
		'''
		product = 'NRML' #MIS=Intraday CNC=Delivery of Equities, NRML=overnight of FNO 
		validity='DAY'
		mytag="hiteshapi"
		# Place order
		newOrderId:str = None
		try:
			order_response = self.api.place_order(variety='regular',exchange=exchangeCode,tradingsymbol=zerodha_tradingsymbol,
										 transaction_type=action,quantity=quantity,product=product,
										 order_type=orderType,price=price,validity=validity,trigger_price=stoploss,tag=mytag)
			print(order_response)
			newOrderId = order_response
		except KiteException as ex:
			print("Error occurred while placing order")
			print(ex)
			response = '{"Error":"Check logs for error: '+ str(ex) +'"}'
			print(response)
			result = json.loads(response)
			return result
		order_status = "Success"
		order_status_message = ""
		if newOrderId :
			order_status_message = '{ "message":"order placed successfully.check status.","order_id":"' + newOrderId + '"}'
		else:
			order_status = "Error"
			order_status_message = '"Error placing order"'
		response = '{"'+ order_status +'":' + order_status_message + '}'
		print(response)
		result = json.loads(response)
		return result
	

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
		quantity = int(params.get("quantity","0"))
		stopLoss = float(params.get("stoploss","0"))
		orderType = "LIMIT"
		validity ="DAY" #DAY,IOC
		if priceStr == "0":
			orderType = "MARKET" #MARKET,LIMIT,SL,SL-M
		if stopLoss > 0 :
			orderType = "SL" #MARKET,LIMIT,SL,SL-M
		price = float(priceStr)

		try:
			modifyResponse = self.api.modify_order(variety='regular',order_id=orderIdStr,quantity=quantity,price=price,order_type=orderType,trigger_price=stopLoss,validity=validity)
			print(modifyResponse)
			modifiedOrderId = modifyResponse
			response = '{"Success":{"message":"Order ' + orderIdStr + ' modified successfully","order_id":"' + modifiedOrderId + '"}}'
		except Exception as e:
			print(e)
			response = '{"Error":"'+str(e)+'"}'
		
		print(response)
		result = json.loads(response)
		return result
    
	def cancelOrder(self,orderRef):
		try : 
			cancelResponse = self.api.cancel_order(variety='regular',order_id=orderRef)
			print(cancelResponse)
			response = '{"Success":{"message":"Order '+ cancelResponse +' cancelled successfully"}}'
		
		except Exception as e:
			print(e)
			response = '{"Error":"' + str(e) + '"}'

		print(response)
		result = json.loads(response)
		return result
    
	def getOrderDetails(self,orderId):
		orderDetail = self.api.get_order_detail(exchange_code="NFO",order_id=orderId)
		print(orderDetail)
		return orderDetail
	
	def fixOrderStatus(self,df_row):
		status = df_row['status']
		statusMessage = df_row['status_message']
		if statusMessage == None:
			statusMessage = ""
		newStatus = OrderStatus.from_str(status).name
		df_row['status'] = newStatus
		df_row['status_message'] = str(status) + " " + statusMessage
		print(df_row)
		return df_row

	def updatePrice(self, df_row):
		price = df_row['price']
		if price == 0:
			print(f"updating price: {price} with average_price: {df_row['average_price']}")
			df_row["price"] = df_row["average_price"]
		return df_row
	
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
		orderList:dict = self.api.orders()
		print(orderList)
		resultJsonDict = {}
		if orderList is None or not orderList:
			print(orderList)
			resultJsonDict = json.loads('{"Error":"Not connected"}')
		else:
			unfilteredOrderList = orderList
			#print(type(unfilteredOrderList))
			#print(unfilteredOrderList)
			if(unfilteredOrderList): #list not empty
				orderListDf = pd.DataFrame(unfilteredOrderList)
				print(orderListDf)
				orderListDf["order_timestamp"] = orderListDf["order_timestamp"].astype(str)
				#orderListDf = orderListDf.apply(derivedCol, axis=1)
				today = datetime.now()    
				todayStr = today.strftime("%Y-%m-%d")
				orderDateStr = todayStr
				#orderDateStr = "2024-09-22"
				#print(todayStr)
				result = orderListDf.loc[( \
												(orderListDf["order_timestamp"].str.contains(orderDateStr,na=False, case=False)) \
												& (orderListDf["exchange"].str.contains("NFO",na=False, case=False) 
			   										| orderListDf["exchange"].str.contains("BFO",na=False, case=False) )
												) ].copy()
				#print(result.columns.values)
				#print(result[["order_id","order_datetime","stock_code","status","1","2","3"]])
				result.rename(columns = {'exchange':'exchange_code', 'order_timestamp':'order_datetime','transaction_type':'action','instrument_token':'zerodha_id', 'trigger_price':'stoploss'}, inplace = True)
				result = result.apply(self.addInstrumentIdColumns,axis=1)
				result = result.apply(self.fixOrderStatus,axis=1)
				result = result.apply(self.updatePrice,axis=1)
				result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
				result.sort_values(by='order_datetime_sorting', inplace = True, ascending = False)
				resultJsonStr = result.to_json(orient = "records")
				resultJsonDict = json.loads(resultJsonStr)
				
				#print(resultJsonDict)
		#print(resultJsonDict)
		returnValue = {}
		returnValue["Success"] = resultJsonDict
		return returnValue
    
    
	def getOpenPositionsList(self):
		portfolioPositions = self.api.positions()
		print(portfolioPositions)
		positionList = []
		if portfolioPositions:
			positionDataList = portfolioPositions["net"]
			for positionData in positionDataList:
				#print(positionData.to_dict())
				position = positionData
				if position["buy_quantity"] == position["sell_quantity"]:
					continue
				newPosition = {}
				if position["buy_price"] > 0 :
					newPosition["action"] = "BUY"
					newPosition["average_price"] = position["buy_price"]
					newPosition["quantity"] = position["quantity"]
				newPosition["code"] = position["tradingsymbol"]
				zerodha_id = str(position["instrument_token"])
				newPosition["zerodha_id"] = zerodha_id
				instruDetails = self.getInstrumentDetailsByInstruId(zerodha_id)
				newPosition = newPosition | instruDetails #merge 2 dicts
				positionList.append(newPosition)
			print(positionList)
		response = '{"Success":' + json.dumps(positionList) + '}'
		print(response)
		response = json.loads(response)
		print(response)
		return response

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
		if toDate.month < 4 :
			financial_year = str((toDate.year%100)-1) + str(toDate.year%100)
		else :
			financial_year = str((toDate.year%100)) + str((toDate.year%100)+1)
		from_date = fromDate.strftime("%d-%m-%Y")
		to_date = toDate.strftime("%d-%m-%Y")
		segment = "FO" #get only fno pnl
		#financial_year = str(fromDate.year%100) + str(toDate.year%100) #last 2 digits of from and to date
		positionsList = self.api.positions()
		print(positionsList)
		
		if not positionsList:
			print(positionsList)
			positionsList = json.loads('{"Error":"Not connected"}')
			return positionsList
		#print("trade list")
		#print(len(list(tradesListJsonDict.data)))
		if len(list(positionsList['day'])) == 0 :
			print("No Trades taken between "+fromDateStr+"-"+toDateStr)
			print(positionsList)
			realisedPnlDf = pd.DataFrame({"realised_pnl": 0, 'realised_pnl_with_taxes': 0}, index=[0])
			resultJsonStr = realisedPnlDf.to_json(orient = "records")
			resultJsonDict = json.loads(resultJsonStr)
			responseJsonDict = {}
			responseJsonDict["Success"]=resultJsonDict[0]
			return responseJsonDict
		
		tradesList = positionsList['day']
		tradesListDf = pd.DataFrame(tradesList)
		#print(tradesListDf)
		realised_pnl = tradesListDf['pnl'].sum()
		#print(realised_pnl)
		
		#chargesResponse:upstox_client.GetProfitAndLossChargesResponse = self.pnlApi.get_profit_and_loss_charges(api_version=self.apiversion,segment=segment,financial_year=financial_year,from_date=from_date,to_date=to_date)
		#chargesData:upstox_client.ProfitAndLossChargesWrapperData = chargesResponse.data
		#chargesBreakDown:upstox_client.ProfitAndLossChargesData = chargesData.charges_breakdown
		totalCharges = 0
		realised_pnl_with_taxes = realised_pnl - totalCharges
		#remove open positions
		realised_pnl = round((realised_pnl),2)
		realised_pnl_with_taxes = round((realised_pnl_with_taxes),2)
		realisedPnlDf = pd.DataFrame({"realised_pnl": realised_pnl, 'realised_pnl_with_taxes': realised_pnl_with_taxes}, index=[0])
		#realisedPnlDf = pd.DataFrame({"realised_pnl": realised_pnl, 'realised_pnl_with_taxes': 0}, index=[0])
		print(realisedPnlDf)
		resultJsonStr = realisedPnlDf.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		
		responseJsonDict = {}
		responseJsonDict["Success"]=resultJsonDict[0]
		#responseJsonDict["Success"]={}
		return responseJsonDict
	
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
		margin = self.api.margins(segment="equity")
		print(margin)
		response = '{ "Error" : "Some error occured"}'
		if margin:
			allocatedFunds = margin["available"]["opening_balance"]
			availableMargin = margin["available"]["live_balance"]
			mtm = margin["utilised"]["m2m_realised"]
			mtmStr = '"limit_list":[{"amount":' + str(mtm) + '}] '
			response = '{ "Success" : { "amount_allocated" : "'+str(allocatedFunds)+'", "cash_limit" : "'+str(availableMargin)+'", ' + mtmStr + '} }'
		print(response)
		result = json.loads(response)
		return result

	def marginCalculator(self,params):
		quantity = int(params.get("quantity","1"))
		priceStr = params.get("price","0")
		action = str(params.get("action")).upper()
		exchangeCode = params.get("exchangeCode","NFO")
		orderType = "LIMIT"
		if priceStr == "0" or priceStr == "":
			orderType = "MARKET"
			price = 0.0
		else:
			price = float(priceStr)

		zerodha_id = params.get("zerodha_id","")
		instruDetails = self.getInstrumentDetailsByInstruId(zerodha_id)
		zerodha_tradingsymbol = instruDetails.get('zerodha_tradingsymbol')
		newPosition = {}
		newPosition["exchange"] =  "NFO"
		newPosition["product"] = "NRML"
		newPosition["variety"] = "regular"
		newPosition["tradingsymbol"] =  zerodha_tradingsymbol
		newPosition["transaction_type"] = action
		newPosition["price"] = price
		newPosition["quantity"] = quantity
		newPosition["order_type"] = orderType

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
		includePendingOrders = False
		pendingOrdersList = []
		if includePendingOrders:
			today = datetime.now()
			#show only one day orders
			daysFrom = timedelta(days = 0)
			fromDate = today - daysFrom
			toDate = today + timedelta(days=0)
			orderList =  self.getOrdersList({})
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
		try:
			#print(listOfPositions)
			marginResponse = self.api.order_margins(listOfPositions)
			#print(marginResponse)
			span_margin_required = 0.0
			for margin in marginResponse:
				if margin["tradingsymbol"] == zerodha_tradingsymbol:
					span_margin_required = float(margin["total"])
			#print(span_margin_required)
			response = '{"Success":{"span_margin_required":"' + str("{:.2f}".format(span_margin_required)) + '"}}'
			#print(response)
			response = json.loads(response)
		except Exception as e:
			print(e)
			response = '{"Error":"Check error in server logs"}'
			#print(response)
			response = json.loads(response)
		print(response)
		return response

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
	myapi = KiteApiAdapter()
	test()


if __name__ == "__main__":
    main() 

