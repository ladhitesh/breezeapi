class DataProvider():

    def __init__(self) -> None:
        pass
    
    def initialize(self,existingApi,params):
        pass

    def getLoginUrl(self):
        pass
    
    def isDataProviderConnected(self):
        pass

    def getDataProviderToken(self,params):
        pass

    def getHistoricalData(self, params):
        pass

    def getDataproviderStocks(self, strict, searchStr):
        pass

    def subscribeQuotesFeed(self, token, interval):
        pass
    
    def unsubscribeQuotesFeed(self, token, interval):
        pass

    def subscribeMarketDepth(self,token):
        pass

    def unsubscribeMarketDepth(self, token):
        pass

    def registerFeedCallback(self, callBack):
        pass