from brokerapi.brokerApiAdapter import BrokerApiAdapter
from brokerapi.breezeApiAdapter import BreezeApiAdapter
from brokerapi.upstoxApiAdapter import UpstoxApiAdapter
from brokerapi.testBrokerApiAdapter import TestBrokerApiAdapter

import sys
sys.path.append(".")
import configapi

class  BrokerApiConnect():

    

    def __init__(self, broker) -> None:
        #python ternary operator
        self.BROKER = ({True : configapi.BROKER_DEFAULT, False: broker } [broker == None or broker == ""])
        print("Initializing broker to " + self.BROKER)
        if self.BROKER == configapi.BROKER_IDIRECT:
            self.brokerApi = BreezeApiAdapter()
        if self.BROKER == configapi.BROKER_UPSTOX:
            self.brokerApi = UpstoxApiAdapter()
        if self.BROKER == configapi.BROKER_TEST:
            self.brokerApi = TestBrokerApiAdapter()

    def connect(self,params):
        return self.brokerApi.connect(params)
    
    def registerFeedCallback(self,callbackFn) -> None:
        self.brokerApi.registerFeedCallback(callbackFn)
    
    def isConnected(self):
        return self.brokerApi.isApiConnected()
    
    def getLoginUrl(self):
        return self.brokerApi.getLoginUrl()
    
    def getSessionTokenName(self):
        return self.brokerApi.getSessionTokenName()
    
    def getSessionTokenNameByBroker(self, broker):
        sessionTokenName = configapi.IDIRECT_SESSION_TOKEN_NAME
        if broker == configapi.BROKER_IDIRECT:
            sessionTokenName = configapi.IDIRECT_SESSION_TOKEN_NAME
        elif broker == configapi.BROKER_KITE:
            sessionTokenName = configapi.KITE_SESSION_TOKEN_NAME
        return sessionTokenName

    def getCustomerDetails(self):
        return self.brokerApi.getCustomerDetails()

    def getStocks(self, *searchList):
        return self.brokerApi.getFnOStocks(*searchList)

    def placeOrder(self,params):
        return self.brokerApi.placeOrder(params)

    def modifyOrder(self,params):
        return self.brokerApi.modifyOrder(params)

    def cancelOrder(self,orderRef):
        return self.brokerApi.cancelOrder(orderRef)

    def squareOffOrder(self,params):
        return self.brokerApi.squareOffOrder(params)

    def getOrderDetails(self,orderId):
        return self.brokerApi.getOrderDetails(orderId)
    
    def getOrdersList(self,params):
        return self.brokerApi.getOrdersList(params)

    def getTradesList(self,params):
        return self.brokerApi.getTradesList(params)

    def getOpenPositionsList(self):
        return self.brokerApi.getOpenPositionsList()

    def getBrokerages(self,params):
        return self.brokerApi.getBrokerages(params)

    def getPnl(self,params):
        return self.brokerApi.getPnl(params)

    def getMtm(self):
        self.brokerApi.getMtm()

    def getMargin(self,params):
        return self.brokerApi.getMargin(params)
    
    def marginCalculator(self,params):
        return self.brokerApi.marginCalculator(params)
    
    def getHistoricalData(self,params):
        return self.brokerApi.getHistoricalData(params)
    
    def getTokenFromStockName(self,params):
        return self.brokerApi.getTokenFromStockName(params)
    
    def subscribeQuotesFeed(self,token,interval):
        return self.brokerApi.subscribeQuotes(token,interval)
    
    def unsubscribeQuotesFeed(self,token,interval):
        return self.brokerApi.unsubscribeQuotes(token,interval)

    def subscribeMarketDepth(self,token):
        return self.brokerApi.subscribeMarketDepth(token)

    def unsubscribeMarketDepth(self,token):
        return self.brokerApi.unsubscribeMarketDepth(token)
    
    def clearTokenFiles(self):
        return self.brokerApi.clearTokenFiles()


