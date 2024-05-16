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
    
    def isConnected(self):
        return self.brokerApi.isApiConnected()

    def getCustomerDetails(self):
        return self.brokerApi.getCustomerDetails()

    def getStocks(self, *searchList):
        return self.brokerApi.getFnOStocks(*searchList)

    def placeOrder(self):
        self.brokerApi.placeOrder()

    def modifyOrder(self):
        self.brokerApi.modifyOrder()

    def cancelOrder(self):
        self.brokerApi.cancelOrder()

    def squareOffOrder(self):
        self.brokerApi.squareoffOrder()

    def getOrderList(self):
        self.brokerApi.getOrderList()

    def getTradeList(self):
        self.brokerApi.getTradeList()

    def getOpenPositionList(self):
        self.brokerApi.getOpenPositionList()

    def getBrokerages(self):
        self.brokerApi.getBrokerages()

    def getPnl(self):
        self.brokerApi.getPnl()

    def getMtm(self):
        self.brokerApi.getMtm()


