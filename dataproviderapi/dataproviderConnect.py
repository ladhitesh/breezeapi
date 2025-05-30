from dataproviderapi.dataProvider import DataProvider
from dataproviderapi.breezeDataProvider import BreezeDataProvider


import sys
sys.path.append(".")
import configapi

class  DataProviderConnect():

    dataProvider = DataProvider()

    def __init__(self,dataprovider) -> None:
        #python ternary operator
        DATAPROVIDER_ENUM = ({True : configapi.DATAPROVIDER_DEFAULT, False: dataprovider } [dataprovider == None or dataprovider == ""])
        print("Dataproviter: " + dataprovider)
        print(DATAPROVIDER_ENUM)
        print("Setting dataprovider to " + DATAPROVIDER_ENUM)
        if DATAPROVIDER_ENUM == "IDIRECT":
            self.dataProvider = BreezeDataProvider()

    def initialize(self,existingApi,params):
        print("DPConnect existingApi:" + str(existingApi))
        return self.dataProvider.initialize(existingApi,params)
    
    def getLoginUrl(self):
        return self.dataProvider.getLoginUrl()
    
    def isDataProviderConnected(self):
        return self.dataProvider.isDataProviderConnected()
    
    def getDataProviderToken(self,params):
        return self.dataProvider.getDataProviderToken(params)

    
    def getHistoricalData(self,params):
        return self.dataProvider.getHistoricalData(params)
    
    def getDataproviderStocks(self, strict, *searchStr):
        return self.dataProvider.getDataproviderStocks(strict, *searchStr)