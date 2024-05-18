import unittest
import brokerApiConnect

class testBrokerApiConnect(unittest.TestCase):

    brokerapi = brokerApiConnect.BrokerApiConnect()
    brokerapi.initialize("test")

    def test_initialize(self):
        #self.brokerapi.initialize("test")
        self.assertTrue(True)

    def test_connect(self):
        self.brokerapi.connect()
        self.assertTrue(True)

    def test_getCustomerDetails(self):
        self.brokerapi.getCustomerDetails()
        self.assertTrue(True)

    def test_getStocks(self):
        self.brokerapi.getStocks()
        self.assertTrue(True)

    def test_placeOrder(self):
        self.brokerapi.placeOrder()
        self.assertTrue(True)

    def test_modifyOrder(self):
        self.brokerapi.modifyOrder()
        self.assertTrue(True)

    def test_cancelOrder(self):
        self.brokerapi.cancelOrder()
        self.assertTrue(True)

    def test_squareOffOrder(self):
        self.brokerapi.squareOffOrder()
        self.assertTrue(True)

    def test_getOrdersList(self):
        self.brokerapi.getOrdersList()
        self.assertTrue(True)

    def test_getTradesList(self):
        self.brokerapi.getTradesList()
        self.assertTrue(True)

    def test_getOpenPositionsList(self):
        self.brokerapi.getOpenPositionsList()
        self.assertTrue(True)

    def test_getBrokerages(self):
        self.brokerapi.getBrokerages()
        self.assertTrue(True)

    def test_getPnl(self):
        self.brokerapi.getPnl()
        self.assertTrue(True)

    def test_getMtm(self):
        self.brokerapi.getMtm()
        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()