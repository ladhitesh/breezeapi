class BrokerApiAdapter():
    def __init__(self) -> None:
        pass

    def initialize(self, str) -> None:
        pass

    def connect(self) -> None:
        pass

    def getLoginUrl(self) -> None:
        pass

    def getSessionTokenName(self) -> None:
        pass
    
    def registerFeedCallback(self,callbackFn) -> None:
        pass

    def isApiConnected(self) -> None:
        pass

    def getCustomerDetails(self):
        pass

    def getStocks(self):
        pass

    def placeOrder(self,params):
        pass

    def modifyOrder(self,params):
        pass

    def cancelOrder(self,orderRef):
        pass

    def squareOffOrder(self,params):
        pass

    def getOrderDetails(self,orderId):
        pass

    def getOrdersList(self,params):
        pass

    def getTradesList(self,params):
        pass

    def getOpenPositionsList(self):
        pass

    def getBrokerages(self):
        pass

    def getPnl(self,params):
        pass

    def getMtm(self):
        pass

    def getMargin(self,params):
        pass

    def marginCalculator(self,params):
        pass

    def getHistoricalData(self,params):
        pass

    def getTokenFromStockName(self,params):
        pass

    def subscribeQuotesFeed(token,interval):
        pass
    
    def unsubscribeQuotesFeed(token,interval):
        pass

    def subscribeMarketDepth(token):
        pass

    def unsubscribeMarketDepth(token):
        pass

    def clearTokenFiles():
        pass