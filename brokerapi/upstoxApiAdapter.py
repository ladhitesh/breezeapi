
# Import Libraries
import upstox_client
import upstox_client.models
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

if sys.version_info >= (3, 8):
    from importlib import metadata
else:
    from importlib_metadata import metadata



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

class  UpstoxApiAdapter(BrokerApiAdapter):

	def __init__(self):
		#global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
		self.loginapi = upstox_client.LoginApi()
		self.isConnected = False
		self.stockScriptdf = pd.read_csv('./instruments/instruments-final.csv' ,sep=',',encoding='utf-8')

	# Callback to receive ticks.
	def on_ticks(self,ticks):
		#print(ticks)
		
		if(self.onMessage!=None):
			token = "none"
			interval = ""
			if ticks.get('feeds') != None and ticks.get('update_type') == None:
				#OHLV data
				
				feed = ticks.get('feeds')
				#print(feed)
				#print(type(feed))
				for instrumentKey in feed.keys():
					#print(instrumentKey)
					token = instrumentKey.split('|')[1]
					#print(token)
					close = ticks.get('feeds').get(instrumentKey).get('ltpc').get('ltp')
					#print("closing price ****************************")
					newTick = {"token":token,"close":close}
					self.onMessage(token+"-1second",newTick)
					#print(close)
				#print(ticks.get('feeds'))
				#get exchange token from upstox instrument key
				#(quotesToken, marketDepthToken) = self.getTokenFromStockName(params)
				#token = quotesToken.split('!')[1]
			elif ticks.get('quotes') == "Market Depth":
				#Market Data
				token = ticks['symbol'].split('!')[1]
			elif ticks.get('quotes') == "Quotes Data":
				token = ticks['symbol'].split('!')[1]
				interval = ticks['interval']
			elif ticks.get('update_type') != None and ticks.get('update_type') == "order":
				#order Notification
				#print(ticks)
				token = "order_notification"
				orderReference = ticks.get("order_id")
				orderStatus = ticks.get("status")
				stockCode = ticks.get("trading_symbol")
				newTick = {"orderReference":orderReference,"orderStatus":orderStatus,"stockCode":stockCode}
				print(newTick)
				self.onMessage(token,newTick)
			eventName = token
			if interval != "":
				eventName = token + "-" + interval
				ticks['token'] = token
			#self.onMessage(eventName,ticks)
			

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
				if os.path.isfile(file_path) and not file == ".gitignore":
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
	
	def getApiVersion(self):
		return "upstox-python-sdk " + metadata.version('upstox-python-sdk')
	
	def getCustomerDetails(self):
		userDetails = self.userapi.get_profile(self.apiversion)
		print(userDetails)
		customerDetails = { "Success":{}}
		user = {}
		status = userDetails.status
		if status == "success":
			userProfile = userDetails.data
			print(userProfile)
			user["userid"] = userProfile.user_id
			user["user_name"] = userProfile.user_name
			user["broker"] = userProfile.broker
		customerDetails["Success"] = user
		print(customerDetails)
		return customerDetails
	
	def getInstrumentDetailsByInstruId(self,upstox_id):
		print("Populating values based on upstox id:%s",upstox_id)
		stockScriptdf = self.stockScriptdf
		requiredCol = stockScriptdf[["ExAllowed","ShortName","trading_symbol","idirect_id","zerodha_id","upstox_id","Series"]]
		result = requiredCol.loc[( \
                                            (stockScriptdf["upstox_id"] == upstox_id)
                                          	) ].head(1).copy()
		result.rename(columns = {'trading_symbol':'code'}, inplace = True)
		print(result.to_string())
		response = {}
		if not result.empty:
			response['token'] = result['idirect_id'].astype(str).item()
			response['idirect_id'] = result['idirect_id'].astype(str).item()
			response['zerodha_id'] = result['zerodha_id'].astype(str).item()
			response['upstox_id'] = result['upstox_id'].astype(str).item()
			response['code'] = result['code'].astype(str).item()
			product = result['Series'].astype(str).item()
			if product.lower() == 'option':
				product = "OPTIONS"
			elif product.lower() == 'future':
				product = "FUTURES"
			response['product_type'] = product
		else:
			print("Cannot find data for upstox id: %s",upstox_id)
		#print(df_row.to_string())
		return response

	def addInstrumentIdColumns(self,df_row):
		print(df_row.index)
		print(df_row.to_dict())
		print('upstox_id' in df_row.index)
		if 'upstox_id' in df_row.index :
			upstox_id = df_row["upstox_id"]
			response = self.getInstrumentDetailsByInstruId(upstox_id)
			df_row['idirect_id'] = response['idirect_id']
			df_row['zerodha_id'] = response['zerodha_id']
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
		upstox_id = params.get("upstox_id","None")
		quantity:int = params.get("quantity",0)
		price:float = (params.get("price",1),1)[params.get("price",1) == ""]
		action = params.get("action").upper()
		try:
			brokerageResponse:upstox_client.GetBrokerageResponse = self.chargeApi.get_brokerage(instrument_token=upstox_id,quantity=quantity,transaction_type=action,price=price,product='D',api_version=self.apiversion)
			print(brokerageResponse)
			brokerageWrapper:upstox_client.BrokerageWrapperData = brokerageResponse.data
			brokerageData:upstox_client.BrokerageData = brokerageWrapper.charges
			brokerage = brokerageData.to_dict()
			returnData = '"total_brokerage":"'+str(brokerage["total"])+'"'
			returnData = returnData +','+'"brokerage":"'+str(brokerage["brokerage"])+'"'
			returnData = returnData +','+'"stamp_duty":"'+str(brokerage["taxes"]["stamp_duty"])+'"'
			returnData = returnData +','+'"stt":"'+str(brokerage["taxes"]["stt"])+'"'
			returnData = returnData +','+'"gst":"'+str(brokerage["taxes"]["gst"])+'"'
			returnData = returnData +','+'"exchange_turnover_charges":"'+str(brokerage["other_taxes"]["transaction"])+'"'
			returnData = returnData +','+'"sebi_charges":"'+str(brokerage["other_taxes"]["sebi_turnover"])+'"'
			response = '{"Success":{'+returnData+'}}'
			response = json.loads(response)
		except Exception as e:
			print(e)
			response = '{"Error":"Check error in server logs"}'
			response = json.loads(response)

		return response
    
	def placeOrder(self,params):
		#stockcode,exchangeCode,product,action,orderType,stoploss,quantity,price,expiryDate,rightStr,strike
		quantity = int(params.get("quantity","1"))
		price = float(params.get("price","1"))
		stoploss = float(params.get("stoploss","0"))
		action = params.get("action").upper()
		instrumentId = params.get("upstox_id","")
		orderType = "LIMIT"
		if price == 0:
			orderType = "MARKET"
		amoOrder = False
		try:
			marketResponse:upstox_client.GetMarketStatusResponse = self.marketHolidaysapi.get_market_status("NFO")
			marketStatus:upstox_client.MarketStatusData = marketResponse.data
			if not marketStatus.status == "NORMAL_OPEN":
				amoOrder = True
		except Exception as e:
			print(e)
			print("Unable to determine market open status to place new order. Placing regular order")
		
		body = upstox_client.PlaceOrderRequest(
		quantity = quantity,
		product = 'D', #I=Intraday D=Delivery
		price = price,
		order_type = orderType, #MARKET, LIMIT, SL,SL-M
		transaction_type = action,
		trigger_price = stoploss,
		instrument_token = instrumentId,
		validity='DAY',
		disclosed_quantity=quantity,
		is_amo=amoOrder,
		tag="hitesh" )
		# Place order
		try:
			order_response:upstox_client.PlaceOrderResponse = self.orderapi.place_order(body,self.apiversion)
			print(order_response)
			orderData : upstox_client.PlaceOrderData = order_response.data
			orderId = orderData.order_id
			order_details:upstox_client.GetOrderDetailsResponse = self.orderapi.get_order_status(order_id=orderId)
			print(order_details)
			orderDetailsData:upstox_client.OrderBookData = order_details.data
		except Exception as ex:
			print("Error occurred while placing order")
			print(ex)
			response = '{"Error":"Error occured while placing order. Check logs."}'
			print(response)
			result = json.loads(response)
			return result
		order_status = "Success"
		order_status_message = ""
		if orderDetailsData.status_message == None :
			order_status_message = '{ "message":"' + orderDetailsData.status +'","order_id":"' + orderDetailsData.order_id + '"}'
		else:
			order_status = "Error"
			order_status_message = '"' + orderDetailsData.status_message + '"'
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
			body:upstox_client.ModifyOrderRequest = upstox_client.ModifyOrderRequest(
				price=price,quantity=quantity,validity=validity,order_id=orderIdStr,
				trigger_price=stopLoss,order_type=orderType)
			modifyResponse:upstox_client.ModifyOrderResponse = self.orderapi.modify_order(body,self.apiversion)
			print(modifyResponse)
			modifyResult:upstox_client.ModifyOrderData = modifyResponse.data
			response = '{"Success":{"message":"Order ' + modifyResult.order_id + ' modified successfully","order_id":"' + modifyResult.order_id + '"}}'
		except Exception as e:
			print(e)
			response = '{"Error":"'+str(e)+'"}'
		
		print(response)
		result = json.loads(response)
		return result

		'''
    {'Success': {'message': 'Successfully Modified the order', 'order_id': '202310201500017588'}, 'Status': 200, 'Error': None}
    '''

    
	def cancelOrder(self,orderRef):
		try : 
			cancelResponse:upstox_client.CancelOrderResponse = self.orderapi.cancel_order(order_id=orderRef,api_version=self.apiversion)
			cancelResult:upstox_client.CancelOrderData = cancelResponse.data
			print(cancelResult)
			response = '{"Success":{"message":"Order '+ cancelResult.order_id+' cancelled successfully"}}'
		
		except Exception as e:
			print(e)
			response = '{"Error":"' + str(e) + '"}'

		print(response)
		result = json.loads(response)
		return result

		'''
    {'Success': {'order_id': '202310201500017588', 'message': 'Your Order Canceled Successfully'}, 'Status': 200, 'Error': None}
    '''
    
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
		orderList:upstox_client.GetOrderBookResponse = self.orderapi.get_order_book(self.apiversion)
		print(orderList)
		resultJsonDict = {}
		if orderList is None or orderList.status == "error":
			print(orderList)
			resultJsonDict = json.loads('{"Error":"Not connected"}')
		else:
			unfilteredOrderList = orderList.data
			#print(type(unfilteredOrderList))
			#print(unfilteredOrderList)
			if(unfilteredOrderList): #list not empty
				orderListDf = pd.DataFrame([o.to_dict() for o in unfilteredOrderList])
				#print(orderListDf)
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
				result.rename(columns = {'exchange':'exchange_code', 'order_timestamp':'order_datetime','transaction_type':'action','instrument_token':'upstox_id', 'trigger_price':'stoploss'}, inplace = True)
				result = result.apply(self.addInstrumentIdColumns,axis=1)
				result = result.apply(self.fixOrderStatus,axis=1)
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
		portfolioPositionsResponse:upstox_client.GetPositionResponse = self.portfolioapi.get_positions(api_version=self.apiversion)
		print(portfolioPositionsResponse)
		positionDataList = portfolioPositionsResponse.data
		#spoofData start
		#positionData:upstox_client.PositionData = upstox_client.PositionData(buy_price=250,average_price=250,quantity=15,trading_symbol="BANKNIFTY",instrument_token="NSE_FO|45066")
		#positionDataList.append(positionData)
		#spoof data end
		positionList = []
		for positionData in positionDataList:
			#print(positionData.to_dict())
			position = positionData.to_dict()
			newPosition = {}
			if position["buy_price"] > 0 :
				newPosition["action"] = "BUY"
				newPosition["average_price"] = position["buy_price"]
				newPosition["quantity"] = position["quantity"]
			newPosition["code"] = position["trading_symbol"]
			upstox_id = position["instrument_token"]
			newPosition["upstox_id"] = upstox_id
			instruDetails = self.getInstrumentDetailsByInstruId(upstox_id)
			newPosition = newPosition | instruDetails #merge 2 dicts
			positionList.append(newPosition)
		print(positionList)
		response = '{"Success":' + json.dumps(positionList) + '}'
		print(response)
		response = json.loads(response)
		print(response)
		return response
    
    
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
		tradesListJsonDict:upstox_client.GetTradeWiseProfitAndLossDataResponse = self.pnlApi.get_trade_wise_profit_and_loss_data(api_version=self.apiversion,segment=segment,financial_year=financial_year,from_date=from_date,to_date=to_date,page_number=1,page_size=5000)
		#print(tradesListJsonDict)
		if tradesListJsonDict == None or not tradesListJsonDict.status == "success" :
			print(tradesListJsonDict)
			tradesListJsonDict = json.loads('{"Error":"Not connected"}')
			return tradesListJsonDict
		#print("trade list")
		#print(len(list(tradesListJsonDict.data)))
		if len(list(tradesListJsonDict.data)) == 0 :
			print("No Trades taken between "+fromDateStr+"-"+toDateStr)
			print(tradesListJsonDict)
			realisedPnlDf = pd.DataFrame({"realised_pnl": 0, 'realised_pnl_with_taxes': 0}, index=[0])
			resultJsonStr = realisedPnlDf.to_json(orient = "records")
			resultJsonDict = json.loads(resultJsonStr)
			responseJsonDict = {}
			responseJsonDict["Success"]=resultJsonDict[0]
			return responseJsonDict
		tradesList = tradesListJsonDict.data
		tradesListDf = pd.DataFrame([o.to_dict() for o in tradesList])
		#print(tradesListDf)
		realised_pnl = (tradesListDf['sell_amount']-tradesListDf['buy_amount']).sum()
		#print(realised_pnl)
		chargesResponse:upstox_client.GetProfitAndLossChargesResponse = self.pnlApi.get_profit_and_loss_charges(api_version=self.apiversion,segment=segment,financial_year=financial_year,from_date=from_date,to_date=to_date)
		chargesData:upstox_client.ProfitAndLossChargesWrapperData = chargesResponse.data
		chargesBreakDown:upstox_client.ProfitAndLossChargesData = chargesData.charges_breakdown
		totalCharges = (chargesBreakDown.to_dict())["total"]
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
		return responseJsonDict
	
	def getFunds(self):
		#not used
		response = ""
		return response
	
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
		upstox_id = "NSE_FO|"+token
		return self.marketdataStreamer.subscribe(instrumentKeys=[upstox_id],mode="ltpc")
    
	def subscribeMarketDepth(self,token):
		#"4.2!2885"
		marketDepthToken = "4.2!"+token
		return self.subscribeFeed(marketDepthToken,"")
    
	def unsubscribeQuotes(self,token, interval):
		#"4.1!2885"
		upstox_id = "NSE_FO|"+token
		return self.marketdataStreamer.unsubscribe(instrumentKeys=[upstox_id],mode="ltpc")
    
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
		userFundMarginResponse:upstox_client.GetUserFundMarginResponse = self.userapi.get_user_fund_margin(self.apiversion,segment="SEC")
		print(userFundMarginResponse)
		userFundMarginData:upstox_client.UserFundMarginData = userFundMarginResponse.data['equity']
		allocatedFunds = userFundMarginData.available_margin
		availableMargin = userFundMarginData.used_margin
		mtm = userFundMarginData.payin_amount
		response = '{ "Success" : { "amount_allocated" : "'+str(allocatedFunds)+'", "cash_limit" : "'+str(availableMargin)+'"} }'
		print(response)
		result = json.loads(response)
		return result


	def marginCalculator(self,params):
		newPosition = {}
		exchangeCode = params.get("exchangeCode","NFO")
		action = params.get("action","BUY").upper()
		price:float = params.get("price",0)
		quantity = int(params.get("quantity",0))
		upstox_id = params.get("upstox_id","")
		newPosition:upstox_client.Instrument = upstox_client.Instrument(instrument_key=upstox_id,quantity=quantity,transaction_type=action,price=price,product='D')
		includeOpenPostions = params.get("includeOpenPositions","false")
		if includeOpenPostions.lower() == "true":
			includeOpenPostions = True
		includePendingOrders = False
		#open positions
		openPositionsList = []
		if includeOpenPostions == "true":
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
		try:
			body:upstox_client.MarginRequest = upstox_client.MarginRequest(instruments=listOfPositions)
			marginResponse:upstox_client.PostMarginResponse = self.chargeApi.post_margin(body)
			marginData:upstox_client.MarginData = marginResponse.data
			margin = marginData.to_dict()
			print(margin)
			span_margin_required = str(round(margin["final_margin"],2))
			response = '{"Success":{"span_margin_required":"' + span_margin_required + '"}}'
			response = json.loads(response)
		except Exception as e:
			print(e)
			response = '{"Error":"'+str(e)+'"}'
			response = json.loads(response)
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
	myapi = UpstoxApiAdapter()
	test()


if __name__ == "__main__":
    main() 

