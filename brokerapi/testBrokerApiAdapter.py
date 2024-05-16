from brokerapi.brokerApiAdapter import BrokerApiAdapter
class TestBrokerApiAdapter(BrokerApiAdapter):
    def __init__(self):
        print("created test broker api adapter")

    def initialize(self, str) -> None:
        print("initialize test broker api")

    def connect(self):
        print("connected to test broker api")

    def getCustomerDetails(self):
        print("fetched customer details from test broker api")

    def getStocks(self):
        print("fetched stocks from test broker api")

    def placeOrder(self):
        print("placed order using test broker api")

    def modifyOrder(self):
        print("modified order using test broker api")

    def cancelOrder(self):
        print("cancelled order using test broker api")

    def squareoffOrder(self):
        print("squared off order using test broker api")

    def getOrderList(self):
        print("order list using test broker api")

    def getTradeList(self):
        print("trade list using test broker api")

    def getOpenPositionList(self):
        print("open position list using test broker api")

    def getBrokerages(self):
        print("brokerages using test broker api")

    def getPnl(self):
        print("pnl using test broker api")

    def getMtm(self):
        print("mtm using test broker api")