from brokerapi.brokerApiAdapter import BrokerApiAdapter
from brokerapi.breezeApiAdapter import BreezeApiAdapter
from brokerapi.testBrokerApiAdapter import TestBrokerApiAdapter

import sys
sys.path.append(".")
import configapi

class  BrokerApiConnect():

    brokerApi = BrokerApiAdapter()

    def __init__(self) -> None:
        pass

    def initialize(self):
        BROKER_API_ENUM = configapi.BROKER
        print("Initializing api to " + BROKER_API_ENUM)
        if BROKER_API_ENUM == "ICICIDIRECT":
            self.brokerApi = BreezeApiAdapter()
        if BROKER_API_ENUM == "test":
            self.brokerApi = TestBrokerApiAdapter()
        return self.brokerApi

    def connect(self,params):
        return self.brokerApi.connect(params)
    
    def registerFeedCallback(self,callbackFn) -> None:
        self.brokerApi.registerFeedCallback(callbackFn)
    
    def isConnected(self):
        return self.brokerApi.isApiConnected()

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


