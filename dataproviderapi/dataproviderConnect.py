from dataproviderapi.dataProvider import DataProvider
from dataproviderapi.breezeDataProvider import BreezeDataProvider


import sys
sys.path.append(".")
import configapi

class  DataProviderConnect():

    dataProvider = DataProvider()

    def __init__(self) -> None:
        pass

    def initialize(self,existingApi,params):
        DATAPROVIDER_ENUM = configapi.DATAPROVIDER
        print("Initializing dataprovider to " + DATAPROVIDER_ENUM)
        if DATAPROVIDER_ENUM == "IDIRECT":
            self.dataProvider = BreezeDataProvider()
        print("DPConnect existingApi:" + str(existingApi))
        return self.dataProvider.initialize(existingApi,params)
    
    def isDataProviderConnected(self):
        return self.dataProvider.isDataProviderConnected()
    
    def getDataProviderToken(self,params):
        return self.dataProvider.getDataProviderToken(params)

    
    def getHistoricalData(self,params):
        return self.dataProvider.getHistoricalData(params)
    
    def getDataproviderStocks(self, *searchStr):
        return self.dataProvider.getDataproviderStocks(*searchStr)