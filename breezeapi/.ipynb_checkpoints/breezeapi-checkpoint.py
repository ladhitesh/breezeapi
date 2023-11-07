

#intialize keys
api_key = "$6Y56)71761r28t23V2751~dQ7j8o518"
api_secret = "939C6l37E=53245%5i930lJa4)B60u60"
api_session = '24489095'

# Select Stock (USE SYMBOL AS SHOWN ON NSE) eg: RELIANCE
#STOCK = 'RELIANCE' 

# Import Libraries
from breeze_connect import BreezeConnect, config
from io import BytesIO
from zipfile import ZipFile
from urllib.request import urlopen
from io import StringIO  
from datetime import datetime, date, timedelta
from icecream import ic
import json


import pandas as pd
import time

# Setup my API keys 
#api = BreezeConnect(api_key=api_key)
#api.generate_session(api_secret=api_secret,session_token=api_session)
'''
api = None
securityMasterResponse = None
securityMasterZipFile = None
nseFile = None
foNseFile = None
bseFile = None

stockScriptdf = None
'''
class  MyBreezeApi():

    def __init__(self):
        #global api, securityMasterResponse, securityMasterZipFile, nseFile, foNseFile, bseFile, stockScriptdf
        self.api = BreezeConnect(api_key=api_key)
        self.securityMasterResponse = urlopen(config.SECURITY_MASTER_URL)
        self.securityMasterZipFile = ZipFile(BytesIO(self.securityMasterResponse.read()))
        self.nseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("nse"))
        self.foNseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("fonse"))
        self.bseFile = self.securityMasterZipFile.open(config.ISEC_NSE_CODE_MAP_FILE.get("bse"))

        self.stockScriptdf = pd.read_csv(
                                config.STOCK_SCRIPT_CSV_URL ,
                                sep=',',
                                encoding='utf-8',
                            )
        
        
    def connect(self,api_session):
        self.api.generate_session(api_secret=api_secret,session_token=api_session)

    def addAdditionalColumns(self,df_row):
        codeArr = df_row["code"].split("-", 2)
        fnoType = codeArr[0]
        stockCode =  codeArr[1]
        #print(codeArr)
        if fnoType == "FUT":
            expiry = codeArr[2]
            strike = "NA"
            right = "NA"
        else:
            codeArrRevSplit = codeArr[2].rsplit("-", 2)
            #print(codeArrRevSplit)
            expiry = codeArrRevSplit[0]  #'26-Oct-2023'
            strike = codeArrRevSplit[1]
            right = codeArrRevSplit[2]
        df_row["fnoType"] = fnoType
        df_row["expiry"] = expiry
        df_row["strike"] = strike
        df_row["right"] = right
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
                                 ) ].copy()
        result.rename(columns = {'TK':'token', 'CD':'code','EC':'exchangeCode','SC':'stockCode'}, inplace = True)
        result = result.apply(self.addAdditionalColumns,axis=1)
        resultJsonStr = result.to_json(orient = "records")
        resultJsonDict = json.loads(resultJsonStr)
        return resultJsonDict
    
    #fnoStocksJson = getFnOStocks("oct","26","cnx", "43800","ce")
    #fnoStocksDf = pd.read_json(StringIO(fnoStocksJson), orient='columns')
    #print(fnoStocksDf.to_string(index=False))
    #print(fnoStocksDf['exchangeCode'].iloc[0])
    #print(fnoStocksDf['stockCode'].iloc[0])
    #print(api.get_names(exchange_code="NSE", stock_code="CNXBAN"))
    #['isec_stock_code']
    #print(brokerages)
    #print(fnoStocks)
    #& (stockScriptdf["SC"]  == "CNXBAN") \
    #& (stockScriptdf["CD"].str.contains(searchStr, regex=False, na=False, case=False)) \
    
    def getBrokerages(self,exchangeCode,stockCode,orderType="market",price="0",action="buy",quantity="1"):
        print("exchangeCode=" + exchangeCode + ", stockcode= " + stockCode)
        stock = self.api.get_names(exchange_code=exchangeCode, stock_code=stockCode)['isec_stock_code']
        brokerages = self.api.preview_order( stock_code = stock,
            exchange_code = exchangeCode,
            product = "margin",
            order_type = orderType,
            price = price,
            action = action,
            quantity = quantity,
            specialflag = "N")
        return brokerages
    
    def placeOrder(self,stockcode,strike,expiry,action,right,order_type,price):
        # Place order
        stockcode = "CNXBAN"
        todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
        expiryStr = expiry.strftime('%Y-%m-%dT06:00:00.000Z')
        buy_order = self.api.place_order(stock_code=stockcode,
                                exchange_code="NFO",
                                product="options",
                                action=action,
                                order_type='limit',
                                stoploss="",
                                quantity="15",
                                price=price,
                                validity="day",
                                validity_date=todayStr,
                                disclosed_quantity="0",
                                expiry_date=expiryStr,
                                right=right,
                                strike_price=strike)
    
        print(buy_order)
        return buy_order
    
    #exchangeCode = fnoStocksDf['exchangeCode'].iloc[0]
    #stockCode = fnoStocksDf['stockCode'].iloc[0]
    #if exchangeCode not in ["NSE","BSE"]:
    #    exchangeCode = "NSE"
    #brokerages = getBrokerages(exchangeCode=exchangeCode,stockCode=stockCode,orderType="market",price="0",action="buy",quantity="15")
    #print(brokerages)
    #expiry = '2023-10-26T06:00:00.000Z'
    #expiry = date(2023,10,26).strftime(r'%d-%b-%Y')
    #placeOrder(stockcode="CNXBAN",strike="43800",expiry=expiry, action="buy",right="call",order_type="limit",price="1")
    
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
    
    def modifyOrder(self,orderId,quantity="",price=""):
        modifyResult = self.api.modify_order(order_id=orderId,
                        exchange_code="NFO",
                        order_type="limit",
                        stoploss="0",
                        quantity=quantity,
                        price=price,
                        validity="day",
                        disclosed_quantity="0")
        print(modifyResult)
        return modifyResult
    
    #modifyOrder("202310201500017588",quantity="30")
    '''
    {'Success': {'message': 'Successfully Modified the order', 'order_id': '202310201500017588'}, 'Status': 200, 'Error': None}
    '''
    #orderDetail = getOrderDetail('202310201500017588')
    
    def cancelOrder(self,orderId):
        cancelResult = self.api.cancel_order(exchange_code="NFO",
                        order_id=orderId)
        print(cancelResult)
        return cancelResult
    
    #cancelOrder('202310201500017588')
    '''
    {'Success': {'order_id': '202310201500017588', 'message': 'Your Order Canceled Successfully'}, 'Status': 200, 'Error': None}
    '''
    
    def getOrderList(self):
        today = datetime.now()    
        daysFrom = timedelta(days = 7)
        fromDate = today - daysFrom
        todayStr = today.strftime('%Y-%m-%dT23:00:00.000Z')
        fromDateStr = fromDate.strftime('%Y-%m-%dT06:00:00.000Z')
        orderList = self.api.get_order_list(exchange_code="NFO",
                            from_date=fromDateStr,
                            to_date=todayStr)
        #ic(orderList)
        return orderList
    
    #getOrderList()
    '''
    {'Success': [{'order_id': '202310201500017588', 'exchange_order_id': '1500000114831618', 'exchange_code': 'NFO', 
    'stock_code': 'CNXBAN', 'product_type': 'Options', 'action': 'Buy', 'order_type': 'Limit', 'stoploss': '0', 
    'quantity': '30', 'price': '2', 'validity': 'Day', 'disclosed_quantity': '0', 'expiry_date': '26-Oct-2023', 
    'right': 'Call', 'strike_price': 43800.0, 'average_price': '0', 'cancelled_quantity': '30', 'pending_quantity': '30', 
    'status': 'Cancelled', 'user_remark': None, 'order_datetime': '20-Oct-2023 13:34:52', 'parent_order_id': '',
    'modification_number': None, 'exchange_acknowledgement_date': None, 'SLTP_price': None, 'exchange_acknowledge_number': None, 
    'initial_limit': None, 'intial_sltp': None, 'LTP': None, 'limit_offset': None, 'mbc_flag': None, 'cutoff_price': None,
    'validity_date': None}], 'Status': 200, 'Error': None}
    '''
    
    def getPortfolioPositions(self):
        portfolioPositions = self.api.get_portfolio_positions()
        #ic(portfolioPositions)
        return portfolioPositions
    
    #getPortfolioPositions()
    # {'Success': None, 'Status': 200, 'Error': 'No Positions available.'}
    
    #stock_token = api.get_stock_token_value(exchange_code="NSE", stock_code="RELIND", product_type="", expiry_date="", strike_price="", right="")
    #print(stock_token)
    #print(getStockNameFromToken(stock_token)
    def getStockNameFromToken(self,token):
        return self.api.get_data_from_stock_token_value(token)
    
    from enum import Enum
    
    class Right(Enum):
        call = "CE"
        put = "PUT"
        @staticmethod
        def from_str(label):
            if label in ('CE', 'ce'):
                return Right.call
            elif label in ('PE', 'pr'):
                return Right.put
            else:
                raise NotImplementedError
    
        
    def orderTesting(self):
        fnoStocksJson = getFnOStocks("oct","26","cnx", "43800","ce")
        fnoStocksDf = pd.read_json(StringIO(fnoStocksJson), orient='columns')
        print(fnoStocksDf)
        exchangeCode = fnoStocksDf['exchangeCode'].iloc[0]
        stockCode = fnoStocksDf['stockCode'].iloc[0]
        code = fnoStocksDf['code'].iloc[0]
        token =  fnoStocksDf['token'].iloc[0]
        if exchangeCode not in ["NSE","BSE"]:
            brExchangeCode = "NSE"
        else:
            brExchangeCode = exchangeCode
        brokerages = getBrokerages(exchangeCode=brExchangeCode,stockCode=stockCode,orderType="market",price="0",action="buy",quantity="15")
        print(brokerages)
        expiry = '2023-10-26T06:00:00.000Z'
        expiry = date(2023,10,26).strftime(r'%d-%b-%Y')
        print(getStockNameFromToken(token))
        print(code)
        codeArr = code.split("-", 2)
        fnoType = codeArr[0]
        stockCode =  codeArr[1]
        print(codeArr)
        codeArrSplit = codeArr[2].rsplit("-", 2)
        print(codeArrSplit)
        expiry = codeArrSplit[0]  #'26-Oct-2023'
        strike = codeArrSplit[1]
        right = codeArrSplit[2]
    
        expiryDate = datetime.strptime(expiry, "%d-%b-%Y")
        right_type = Right.from_str(right)
        print(right_type.name)
        #result = placeOrder(stockcode=stockCode,strike=strike,expiry=expiryDate, action="buy",right=right_type.name,order_type="limit",price="1")
        print(result)
    
    
    #orderTesting()
    
    
    # Callback to receive ticks.
    def on_ticks(self,ticks):
        print("Ticks: {}\n".format(ticks))
        #convert ticks to dataframe
        #identify stock token
        #emit back with stock token so appropriate receiver can receive
    
    
    # Assign the callbacks.
    #api.on_ticks = on_ticks
    
    # Feeds Subscription
    
    #api.ws_connect()
    def subscribeQuotes(self,token, interval):
        #"4.1!2885"
        self.api.subscribe_feeds(stock_token=token,interval=interval)
        return {"Status":"Success"}
    
    def subscribeMarketDepth(self,token, interval):
        #"4.2!2885"
        self.api.unsubscribe_feeds(stock_token=token,interval=interval)
    
    def unSubscribeQuotes(self,token, interval):
        #"4.1!2885"
        self.api.subscribe_feeds(stock_token=token,interval=interval)
        return {"Status":"Success"}
    
    def unSubscribeMarketDepth(self,token, interval):
        #"4.2!2885"
        self.api.unsubscribe_feeds(stock_token=token,interval=interval)
    
    #time.sleep(10)
    #print(api.subscribe_feeds(get_order_notification=True))
    #print("waiting for data")
    #time.sleep(30)
    #print("shutting down")
    #print(api.unsubscribe_feeds(stock_token="4.1!2885",interval="1second"))
    #print(api.unsubscribe_feeds(stock_token="4.2!2885",interval="1second"))
    #print(api.unsubscribe_feeds(get_order_notification=True))
    #api.ws_disconnect()
    
    
        
    #print(config.ISEC_NSE_CODE_MAP_FILE)
    
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
    #myapi.connect(api_session)
    #myapi.getOrderList()

def test():
    result = myapi.getFnOStocks("oct","26","cnx", "43500","ce")
    print(result)
    

#test()

if __name__ == "__main__":
    main() 

