from breeze_connect import BreezeConnect, config
from datetime import datetime, date, timedelta, timezone
import json
import pandas as pd
import urllib
import os
import glob
import sys
sys.path.append(".")
import configapi
from dataproviderapi.dataProvider import DataProvider

class BreezeDataProvider(DataProvider):
    def __init__(self):
        self.dp = BreezeConnect(configapi.IDIRECT_API_KEY)
        #self.stockScriptdf = pd.read_csv(config.STOCK_SCRIPT_CSV_URL ,sep=',',encoding='utf-8')
        self.stockScriptdf = pd.read_csv('./instruments/instruments-final.csv' ,sep=',',encoding='utf-8')
        self.isConnected = False

    def initialize(self,existingApi,params):
        if existingApi != None:
            self.dp = existingApi
            #self.user_id = self.dp.user_id
            #self.session_key = self.dp.session_key
            #self.session_token = self.dp.session_key
            self.isConnected = True
            return self.dp
        print("Initializing Dataprovider using params")
        sessionToken = params.get(configapi.IDIRECT_SESSION_TOKEN_NAME,"no-breezeapi-session")
        if sessionToken == "no-breezeapi-session":
            sessionToken = self.getSessionTokenFromFile()
            if sessionToken == "no-breezeapi-session":
                raise Exception("No valid sessionToken exist")
        else:
            try:
                file_path = './dataprovidersessiontokens/'+sessionToken
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                # create file
                with open(file_path, 'x') as fp:
                    fp.close()
            except Exception as e:
                print(e)
                print('File already exists')
        self.dp.generate_session(api_secret=configapi.IDIRECT_SECRET_KEY,session_token=sessionToken)
        print("USERID-->" + self.dp.user_id)
        self.user_id = self.dp.user_id
        self.session_key = self.dp.session_key
        self.session_token = sessionToken
        self.isConnected = True
        return self.dp.session_key

    def getSessionTokenFromFile(self):
        sessionToken = "no-breezeapi-session"
        file_path = './dataprovidersessiontokens/*'
        files = sorted(glob.iglob(file_path), key=os.path.getctime, reverse=True)
        if len(files) > 0:
            sessionToken = os.path.basename(files[0])
        return sessionToken

    def getLoginUrl(self):
        loginUrl = configapi.IDIRECT_LOGIN_URL + urllib.parse.quote_plus(configapi.IDIRECT_API_KEY)
        return loginUrl
    
    def isDataProviderConnected(self):
        return self.isConnected
    
    def getDataProviderToken(self,params):
        userId = self.dp.user_id
        sessionKey = self.dp.session_key
        print(userId + " : " + sessionKey)
        return (userId, sessionKey)

    def getHistoricalData(self, params ):
        interval = params.get("interval","15minute")
        fromDateStr = params.get("fromDate","2023-11-01T00:00:00.000Z")
        toDateStr = params.get("toDate","2023-11-01T00:00:00.000Z")
        stockCode = params.get("stockCode","CNXBAN")
        exchangeCode = params.get("exchangeCode","NSE")
        product = params.get("product","")
        product = ({True:"futures",False:product.lower()}[product.lower()=="future" or product.lower()=="fut"])
        product = ({True:"options",False:product.lower()}[product.lower()=="option" or product.lower()=="opt"])
        expiry = params.get("expiry","")
        rightStr = params.get("right","")
        strikePrice = params.get("strike","")
        print("Dataprovider:Historical data")
        print("Dataprovider connected?" + str(self.isConnected))
        hDataJsonDict = self.dp.get_historical_data_v2(interval, fromDateStr, toDateStr, stockCode, exchangeCode, product, expiry, rightStr, strikePrice)
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
        #df_row["fnoType"] = fnoType
        #df_row["expiry"] = expiry
        #df_row["strike"] = strike
        #df_row["right"] = right
        #df_row["product"] = product
        return df_row
    
    def getDataproviderStocks(self,strict='False',*searchTuple):
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
        if strict.lower() == 'true':
            result = requiredCol.loc[( \
                                            (stockScriptdf["Series"]  == searchStockType) \
                                            & ( stockScriptdf["ShortName"].str.contains(searchRegex,na=False, case=False) ) \
                                                ) ].head(10).copy()
        else:
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