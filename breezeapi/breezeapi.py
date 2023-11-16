
# Import Libraries
from breeze_connect import BreezeConnect, config
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from io import StringIO  
from datetime import datetime, date, timedelta
from icecream import ic
import json
import os
import pandas as pd
import time
from enum import Enum

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

class  MyBreezeApi():

	def __init__(self,api_key):
		#global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
		self.api = BreezeConnect(api_key=api_key)
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
			self.foNseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("fonse"))
			self.bseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("bse"))
			self.stockScriptdf = pd.read_csv(
				config.STOCK_SCRIPT_CSV_URL ,
				sep=',',
				encoding='utf-8',
			)


	# Callback to receive ticks.
	def on_ticks(self,ticks):
		if(self.onMessage!=None):
			self.onMessage(ticks)

    
	def connect(self,api_session,api_secret):
		self.api.generate_session(api_secret=api_secret,session_token=api_session)
		self.api.ws_connect()
		# Assign the callbacks.
		self.api.on_ticks = self.on_ticks
		self.api.subscribe_feeds(get_order_notification=True)
		self.isConnected = True
		
	def getCustomerDetails(self, apiSession):
		customerDetails = self.api.get_customer_details(apiSession)
		return customerDetails

	def addFnOStocksAdditionalColumns(self,df_row):
		codeArr = df_row["code"].split("-", 2)
		fnoType = codeArr[0]
		stockCode =  codeArr[1]
		#print(codeArr)
		if fnoType == "FUT":
			expiry = codeArr[2]
			strike = "NA"
			right = "NA"
			product = "futures"
		else:
			codeArrRevSplit = codeArr[2].rsplit("-", 2)
			#print(codeArrRevSplit)
			expiry = codeArrRevSplit[0]  #'26-Oct-2023'
			strike = codeArrRevSplit[1]
			right = codeArrRevSplit[2]
			product="options"
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
		requiredCol = stockScriptdf[["TK","CD","EC","SC","SN"]]
		result = requiredCol.loc[( \
										  (stockScriptdf["SG"]  == "DERIVATIVE") \
										  & (stockScriptdf["CD"].str.contains(searchRegex,na=False, case=False)) \
										 ) ].head(10).copy()
		result.rename(columns = {'TK':'token', 'CD':'code','EC':'exchangeCode','SC':'stockCode'}, inplace = True)
		result = result.apply(self.addFnOStocksAdditionalColumns,axis=1)
		resultJsonStr = result.to_json(orient = "records")
		resultJsonDict = json.loads(resultJsonStr)
		return resultJsonDict
    
	def getBrokerages(self,exchangeCode,stockCode,product,orderType,price,action,quantity):
		#print("exchangeCode=" + exchangeCode + ", stockcode= " + stockCode)
		#stock = self.api.get_names(exchange_code=exchangeCode, stock_code=stockCode)['isec_stock_code']
		brokerages = self.api.preview_order( stock_code = stockCode,
														exchange_code = exchangeCode,
														product = product,
														order_type = orderType,
														price = price,
														action = action,
														quantity = quantity,
														specialflag = "N")
		return brokerages
    
	def placeOrder(self,stockcode,exchangeCode,product,action,orderType,stoploss,quantity,price,expiryDate,rightStr,strike):
		# Place order
		todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
		expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
		buy_order = self.api.place_order(stock_code=stockcode,
													exchange_code=exchangeCode,
													product=product,
													action=action,
													order_type=orderType,
													stoploss=stoploss,
													quantity=quantity,
													price=price,
													validity="day",
													validity_date=todayStr,
													disclosed_quantity="0",
													expiry_date=expiryStr,
													right=rightStr,
													strike_price=strike)

		print(buy_order)
		return buy_order
    
	def getOrderDetail(self,orderId):
		orderDetail = self.api.get_order_detail(exchange_code="NFO",order_id=orderId)
		print(orderDetail)
		return orderDetail
    
		#orderDetail = getOrderDetail('202310201500017588')
		'''
    {'Success': [{'order_id': '202310201500017588', 'exchange_order_id': '1500000114831618', 
    'exchange_code': 'NFO', 'stock_code': 'CNXBAN', 'product_type': 'Options', 'action': 'Buy', 
    'order_type': 'Limit', 'stoploss': '0', 'quantity': '15', 'price': '1', 'validity': 'Day', 
    'disclosed_quantity': '0', 'expiry_date': '26-Oct-2023', 'right': 'Call', 'strike_price': 43800.0, 
    'average_price': '0', 'cancelled_quantity': '0', 'pending_quantity': '15', 'status': 'Ordered', 
    'user_remark': None, 'order_datetime': '20-Oct-2023 13:16:24', 'parent_order_id': '', 
    'modification_number': None, 'exchange_acknowledgement_date': None, 'SLTP_price': None,
    'exchange_acknowledge_number': None, 'initial_limit': None, 'intial_sltp': None, 'LTP': None, 
    'limit_offset': None, 'mbc_flag': None, 'cutoff_price': None, 'validity_date': None}], 'Status': 200, 'Error': None}
    '''
    
	def modifyOrder(self,orderId,exchangeCode,orderType,stopLoss,quantity,price):
		modifyResult = self.api.modify_order(order_id=orderId,
														 exchange_code=exchangeCode,
														 order_type=orderType,
														 stoploss=stopLoss,
														 quantity=quantity,
														 price=price,
														 validity="day",
														 disclosed_quantity="0")
		print(modifyResult)
		return modifyResult

		'''
    {'Success': {'message': 'Successfully Modified the order', 'order_id': '202310201500017588'}, 'Status': 200, 'Error': None}
    '''

    
	def cancelOrder(self,orderId):
		cancelResult = self.api.cancel_order(exchange_code="NFO",
														 order_id=orderId)
		print(cancelResult)
		return cancelResult

		'''
    {'Success': {'order_id': '202310201500017588', 'message': 'Your Order Canceled Successfully'}, 'Status': 200, 'Error': None}
    '''
    
	def getOrderList(self):
		today = datetime.now()    
		daysFrom = timedelta(days = 0)
		fromDate = today - daysFrom
		todayStr = today.strftime('%Y-%m-%dT23:00:00.000Z')
		fromDateStr = fromDate.strftime('%Y-%m-%dT01:00:00.000Z')
		print("fetching orders from: "+fromDateStr+" to "+todayStr)		
		orderList = self.api.get_order_list(exchange_code="NFO",
														from_date=fromDateStr,
														to_date=todayStr)
		#print(orderList)
		return orderList
    
    
	def getPortfolioPositions(self):
		portfolioPositions = self.api.get_portfolio_positions()
		#ic(portfolioPositions)
		return portfolioPositions
    
    
	def getTradesList(self,fromDate,toDate,exchangeCode,productCode="",action="",stockCode=""):
		fromStr = fromDate.strftime('%Y-%m-%dT06:00:00.000Z')
		toStr = toDate.strftime('%Y-%m-%dT18:00:00.000Z')
		exchangeCode = "NFO"

		tradesList = self.api.get_trade_list(from_date=fromStr,
														 to_date=toStr,
														 exchange_code=exchangeCode,
														 product_type=productCode,
														 action=action,
														 stock_code=stockCode)
		return tradesList
	
	def getFunds(self):
		return self.api.get_funds()
	
	def getStockNameFromToken(self,token):
		return self.api.get_data_from_stock_token_value(token)

	def getTokenFromStockName(self,exchange_code, stock_code, product_type, expiry_date, strike_price, right):
		return self.api.get_stock_token_value(exchange_code, stock_code, product_type, expiry_date, strike_price, right, True, True)
    
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

	def getHistoricalData(self, interval, fromDate, toDate, stockCode, exchangeCode, product="", expiry="", right="", strikePrice=""):
		return self.api.get_historical_data_v2(interval, fromDate, toDate, stockCode, exchangeCode, product, expiry, right, strikePrice)

	def getNseStocks(self,stockName):
		nseSecuritiesDf = pd.read_csv(self.nseFile, sep=',', engine='python')
		#print(dataframe.keys())
		filteredData = (dataframe[' "CompanyName"'].str.contains(stockName, na=False, case=False)) & (dataframe['Token'] != '0')
		requiredColumns = dataframe[[' "ExchangeCode"',' "CompanyName"',' "ShortName"','Token']]
		result = requiredColumns.loc[filteredData].copy()
		result.rename(columns = {' "ExchangeCode"':'ExchangeCode', ' "CompanyName"':'CompanyName',
										 ' "ShortName"':'ShortName'}, inplace = True)
		#print(result)
		#print(result.to_json(orient = "records"))
		return (result.to_json(orient = "records"))  


	def main():
		print("Hello World!")
		global myapi
		myapi = MyBreezeApi()
		test()


	def test():
		result = myapi.getFnOStocks("oct","26","cnx", "43500","ce")
		print(result)
		

if __name__ == "__main__":
    main() 

