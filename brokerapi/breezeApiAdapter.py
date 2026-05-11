import logging
import json
from typing import Dict, Optional
from datetime import datetime, timedelta, timezone
import pandas as pd
from breeze_connect import BreezeConnect

from app.config import Config
from brokerapi.base_adapters import BaseApiAdapter
from brokerapi.base_transformers import RightType
from app.models.orders import OrderRequest, OrderResponse, OrderStatus, OrderAction

logger = logging.getLogger(__name__)

class BreezeApiAdapter(BaseApiAdapter):
    """
    Refactored ICICI Breeze Adapter.
    Inherits session management and websocket parsing from BaseApiAdapter.
    """

    def __init__(self, session_manager, instrument_mapper):
        super().__init__(
            broker_name="IDIRECT", 
            session_manager=session_manager, 
            instrument_mapper=instrument_mapper
        )
        # Initialize the SDK object
        from breeze_connect import BreezeConnect # Ensure this is imported at the top
        from app.config import Config
        self.api = BreezeConnect(api_key=Config.IDIRECT_API_KEY)
        self.stockScriptdf = self._instrument_mapper.df
        
        # Check if we have a token saved
        token = self.getSessionToken()
        if token:
            try:
                # Try to resume the session
                self.api.generate_session(api_secret=Config.IDIRECT_SECRET_KEY, session_token=token)
                import logging
                logging.getLogger(__name__).info("BreezeApiAdapter auto-resumed existing session.")
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to auto-resume session: {e}. Clearing stale token.")
                # The token is bad/expired. Delete the file so we don't try it again!

    # -------------------------------------------------------------------------
    # Core Connection & Websocket Overrides
    # -------------------------------------------------------------------------
    
    def connect(self, query_params: Dict[str, str]) -> str:
        api_session = query_params.get(Config.IDIRECT_SESSION_TOKEN_NAME)
        if not api_session:
            # Fallback to existing valid session if available
            api_session = self.getSessionToken()
            if not api_session:
                raise ValueError("No valid session token provided or found.")
            
        def auth_fn():
            self.api.generate_session(api_secret=Config.IDIRECT_SECRET_KEY, session_token=api_session)
            return api_session

        token = self._session_manager.connect_and_save(self.BROKER, auth_fn)
        self.api.ws_connect()
        self.api.on_ticks = self._parse_and_emit_tick
        self.api.subscribe_feeds(get_order_notification=True)
        return token

    def getLoginUrl(self):
        import urllib.parse
        return Config.IDIRECT_LOGIN_URL + urllib.parse.quote_plus(Config.IDIRECT_API_KEY)
        
    def getCustomerDetails(self):
        try:
            userDetails = self.api.get_customer_details(self.getSessionToken())
            customerDetails = {"Success": {}}
            if userDetails and userDetails.get("Success"):
                customerDetails["Success"]["userid"] = userDetails["Success"]["idirect_userid"]
                customerDetails["Success"]["user_name"] = userDetails["Success"]["idirect_user_name"]
                customerDetails["Success"]["broker"] = self.BROKER
            return customerDetails
        except Exception as e:
            logger.error(f"Error fetching customer details: {e}")
            return {"Error": str(e)}

    def _extract_token(self, ticks: Dict, tick_type: str) -> str:
        if tick_type in ["MARKET_DEPTH", "QUOTES", "OHLV"]:
            return str(ticks.get('stock_code', ''))
        return "order_notification" if tick_type == "ORDER_NOTIFICATION" else "UNKNOWN"

    def _extract_interval(self, ticks: Dict, tick_type: str) -> Optional[str]:
        if tick_type == "OHLV":
            return str(ticks.get('interval', ''))
        return None

    # -------------------------------------------------------------------------
    # Orders Management
    # -------------------------------------------------------------------------

    def placeOrder(self, params: Dict) -> Dict:
        # Standardizing dictionary inputs for backward compatibility with tradingApp.py
        stockCode = params.get("stockCode", "CNXBAN")
        quantity = params.get("quantity", "1")
        priceStr = params.get("price", "1")
        stoploss = params.get("stoploss", "")
        action = params.get("action")
        product = params.get("product", "options").lower()
        if product == "option": product = "options"
        if product == "future": product = "futures"
        
        exchangeCode = params.get("exchangeCode", "NFO")
        orderType = "limit" if priceStr != "0" else "market"
        
        strike, rightTypeStr, expiryStr = "", "", ""
        if exchangeCode == "NFO":
            expiryDateStr = params.get("expiryDate")
            expiryDate = datetime.strptime(expiryDateStr, "%Y-%m-%d")
            expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
            if product == "options":
                strike = params.get("strike", "NA")
                rightTypeStr = RightType.from_str(params.get("rightType", "NA")).name

        todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
        
        return self.api.place_order(
            stock_code=stockCode, exchange_code=exchangeCode, product=product,
            action=action, order_type=orderType, stoploss=stoploss,
            quantity=quantity, price=priceStr, validity="day",
            validity_date=todayStr, disclosed_quantity="0",
            expiry_date=expiryStr, right=rightTypeStr, strike_price=strike
        )

    def squareOffOrder(self, params: Dict) -> Dict:
        # Logic identical to placeOrder but calls api.square_off
        stockCode = params.get("stockCode", "CNXBAN")
        quantity = params.get("quantity", "1")
        priceStr = params.get("price", "1")
        stoploss = params.get("stoploss", "")
        action = params.get("action")
        product = params.get("product", "options").lower()
        if product == "option": product = "options"
        if product == "future": product = "futures"
        
        exchangeCode = params.get("exchangeCode", "NFO")
        orderType = "limit" if priceStr != "0" else "market"
        
        strike, rightTypeStr, expiryStr = "", "", ""
        if exchangeCode == "NFO":
            expiryDateStr = params.get("expiryDate")
            expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y") # Retained original parsing
            expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
            if product == "options":
                strike = params.get("strike", "NA")
                rightTypeStr = RightType.from_str(params.get("rightType", "NA")).name

        todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
        
        return self.api.square_off(
            stock_code=stockCode, exchange_code=exchangeCode, product=product,
            action=action, order_type=orderType, stoploss=stoploss,
            quantity=quantity, price=priceStr, validity="day",
            validity_date=todayStr, disclosed_quantity="0",
            expiry_date=expiryStr, right=rightTypeStr, strike_price=strike
        )

    def modifyOrder(self, params: Dict) -> Dict:
        orderIdStr = params.get("orderId", "")
        exchangeCode = params.get("exchangeCode", "NFO")
        priceStr = params.get("price", "")
        quantityStr = params.get("quantity", "")
        stopLossStr = params.get("stoploss", "0")
        orderType = "limit" if priceStr != "0" else "market"
        
        return self.api.modify_order(
            order_id=orderIdStr, exchange_code=exchangeCode, order_type=orderType,
            stoploss=stopLossStr, quantity=quantityStr, price=priceStr,
            validity="day", disclosed_quantity="0"
        )

    def cancelOrder(self, orderRef: str) -> Dict:
        return self.api.cancel_order(exchange_code="NFO", order_id=orderRef)

    def getOrderDetails(self, orderId: str) -> Dict:
        return self.api.get_order_detail(exchange_code="NFO", order_id=orderId)

    def getOrdersList(self, params: Dict) -> Dict:
        fromDateStrOrig = params.get("orderDate", "")
        today = datetime.now()
        
        if not fromDateStrOrig:
            fromDate = today
            toDate = today
        else:
            fromDate = datetime.strptime(fromDateStrOrig, "%d-%m-%Y").date()
            toDate = datetime.strptime(params.get("orderDate", ""), "%d-%m-%Y").date()

        # Retained user's specific weekend holiday hacking logic
        moveBackDays, moveAheadDays = 0, 0
        if fromDate.weekday() == 6: moveBackDays = 1
        if toDate.weekday() == 5: moveAheadDays = 2
        elif toDate.weekday() == 6: moveAheadDays = 1
        
        if moveBackDays != 0 or moveAheadDays != 0:
            fromDate = fromDate - timedelta(days=moveBackDays)
            toDate = toDate + timedelta(days=moveAheadDays)
            
        toDateStr = toDate.strftime('%Y-%m-%dT23:00:00.000Z')
        fromDateStr = fromDate.strftime('%Y-%m-%dT01:00:00.000Z')
        
        orderList = self.api.get_order_list(exchange_code="NFO", from_date=fromDateStr, to_date=toDateStr)
        
        if not orderList or orderList.get("Success") is None:
            return {"Error": "Not connected or no orders"}
            
        unfilteredOrderList = orderList.get("Success")
        if unfilteredOrderList:
            orderListDf = pd.json_normalize(unfilteredOrderList)
            orderDateStr = fromDate.strftime("%d-%b-%Y")
            result = orderListDf.loc[orderListDf["order_datetime"].str.contains(orderDateStr, na=False, case=False)].copy()
            if not result.empty:
                result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
                result.sort_values(by='order_datetime_sorting', inplace=True, ascending=False)
                orderList["Success"] = json.loads(result.to_json(orient="records"))
                
        return orderList

    # -------------------------------------------------------------------------
    # Portfolio, PnL & Margin
    # -------------------------------------------------------------------------

    def getOpenPositionsList(self) -> Dict:
        portfolioPositionsJson = self.api.get_portfolio_positions()
        # Retaining original logic; ID mappings can be added back if needed in frontend
        return portfolioPositionsJson

    def getTradesList(self, params: Dict) -> Dict:
        fromDateStr = params.get("fromDate", datetime.now().strftime("%d-%b-%Y"))
        toDateStr = params.get("toDate", datetime.now().strftime("%d-%b-%Y"))
        fromStr = datetime.strptime(fromDateStr, "%d-%b-%Y").strftime('%Y-%m-%dT06:00:00.000Z')
        toStr = datetime.strptime(toDateStr, "%d-%b-%Y").strftime('%Y-%m-%dT18:00:00.000Z')

        return self.api.get_trade_list(
            from_date=fromStr, to_date=toStr, exchange_code="NFO",
            product_type="", action="", stock_code=""
        )

    def getPnl(self, params: Dict) -> Dict:
        # Retained user's specific Pandas calculation logic for taxes and multiplier
        tradesListJsonDict = self.getTradesList(params)
        if not tradesListJsonDict or not tradesListJsonDict.get("Success"):
            return tradesListJsonDict or {"Error": "Not connected"}
            
        tradesListDf = pd.json_normalize(tradesListJsonDict["Success"])
        tradesListDf["quantity"] = tradesListDf["quantity"].astype(float)
        tradesListDf["average_cost"] = tradesListDf["average_cost"].astype(float)
        tradesListDf["total_taxes"] = tradesListDf["total_taxes"].astype(float)
        tradesListDf["total_cost"] = tradesListDf["quantity"] * tradesListDf["average_cost"]
        
        groupbyTradesListDf = tradesListDf.groupby(["stock_code", "action"], as_index=False)\
            .agg(quantity=("quantity","sum"), sum_total_cost=("total_cost","sum"), sum_total_taxes=("total_taxes","sum"))
            
        def costCalculator(row):
            row["total_cost_with_taxes"] = row["sum_total_cost"] + row["sum_total_taxes"] if row["action"] == "Buy" else row["sum_total_cost"] - row["sum_total_taxes"]
            return row
            
        def pnlMultiplier(row):
            mult = -1 if row["action"] == "Buy" else 1
            row["sum_total_cost"] *= mult
            row["total_cost_with_taxes"] *= mult
            return row
            
        groupbyTradesListDf = groupbyTradesListDf.apply(costCalculator, axis=1).apply(pnlMultiplier, axis=1)
        
        totalOpAmount = 0
        openPositionsDict = self.getOpenPositionsList()
        if openPositionsDict and openPositionsDict.get("Success"):
            today = datetime.now().date()
            toDate = datetime.strptime(params.get("toDate", datetime.now().strftime("%d-%b-%Y")), "%d-%b-%Y").date()
            if toDate == today:
                openPositionsDf = pd.json_normalize(openPositionsDict["Success"])
                openPositionsDf["total_op_amt"] = openPositionsDf["quantity"].astype(float) * openPositionsDf["average_price"].astype(float) * -1
                totalOpAmount = openPositionsDf['total_op_amt'].sum()

        realised_pnl = round(groupbyTradesListDf['sum_total_cost'].sum() - totalOpAmount, 2)
        realised_pnl_with_taxes = round(groupbyTradesListDf['total_cost_with_taxes'].sum() - totalOpAmount, 2)
        
        realisedPnlDf = pd.DataFrame({"realised_pnl": realised_pnl, 'realised_pnl_with_taxes': realised_pnl_with_taxes}, index=[0])
        tradesListJsonDict["Success"] = json.loads(realisedPnlDf.to_json(orient="records"))[0]
        return tradesListJsonDict

    def getFunds(self):
        return self.api.get_funds()

    def getMargin(self, params: Dict):
        return self.api.get_margin(params.get("exchangeCode", "NFO"))

    def marginCalculator(self, params: Dict):
        # Retained user's specific margin calculating logic
        newPosition = {
            "stock_code": params.get("stockCode", ""),
            "expiry_date": params.get("expiryDate", ""),
            "product": "options" if params.get("product", "").lower() == "option" else "futures",
            "action": params.get("action", ""),
            "price": params.get("price", ""),
            "quantity": params.get("quantity", ""),
            "strike_price": params.get("strike", ""),
            "right": RightType.from_str(params.get("rightType", "")).name if params.get("rightType") else ""
        }
        
        includeOpenPostions = str(params.get("includeOpenPositions", "")).lower() == "true"
        openPositionsList = []
        if includeOpenPostions:
            openPositionsDictList = self.getOpenPositionsList()
            if openPositionsDictList and openPositionsDictList.get("Success"):
                for op in openPositionsDictList["Success"]:
                    if op['action'] != 'NA':
                        openPositionsList.append({
                            "stock_code": op["stock_code"], "expiry_date": op["expiry_date"],
                            "action": op["action"], "price": op["average_price"],
                            "quantity": op["quantity"], "strike_price": op["strike_price"],
                            "right": op["right"], "product": op["product_type"]
                        })
                        
        listOfPositions = openPositionsList + [newPosition]
        return self.api.margin_calculator(listOfPositions, "NFO")

    # -------------------------------------------------------------------------
    # Instrument & Feeds Lookups
    # -------------------------------------------------------------------------

    def getBrokerages(self, params: Dict) -> Dict:
        product = params.get("product", "options").lower()
        if product == "option": product = "options"
        if product == "future": product = "futures"
        
        expiryStr, strike, rightTypeStr = "", "", ""
        if params.get("exchangeCode", "NFO") == "NFO":
            expiryStr = datetime.strptime(params.get("expiryDate"), "%Y-%m-%d").strftime('%Y-%m-%dT06:00:00.000Z')
            if product == "options":
                strike = params.get("strike", "NA")
                rightTypeStr = RightType.from_str(params.get("rightType", "NA")).name

        return self.api.preview_order(
            stock_code=params.get("stockCode", "CNXBAN"),
            exchange_code=params.get("exchangeCode", "NFO"),
            product=product,
            order_type="limit" if params.get("price", "1") != "0" else "market",
            price=params.get("price", "1"),
            action=params.get("action"),
            quantity=params.get("quantity", "1"),
            expiry_date=expiryStr, right=rightTypeStr, strike_price=strike, specialflag="N"
        )

    def getFnOStocks(self, *searchTuple) -> Dict:
        searchList = list(searchTuple)
        base, expr = r'^{}', '(?=.*{})'
        searchRegex = base.format(''.join(expr.format(w) for w in searchList[1:]))
        searchStockType = searchList[0]
        
        requiredCol = self.stockScriptdf[["trading_symbol","ExAllowed","ShortName","CompanyName", "LotSize","idirect_id","zerodha_id","upstox_id","Series","ExpiryDate","StrikePrice","OptionType","InstrumentName"]]
        result = requiredCol.loc[
            (self.stockScriptdf["Series"] == searchStockType) & 
            (self.stockScriptdf["trading_symbol"].str.contains(searchRegex, na=False, case=False) | 
             self.stockScriptdf["ShortName"].str.contains(searchRegex, na=False, case=False) | 
             self.stockScriptdf["CompanyName"].str.contains(searchRegex, na=False, case=False))
        ].head(10).copy()
        
        result.rename(columns={'trading_symbol':'code','ExAllowed':'exchangeCode','ShortName':'stockCode', 'LotSize':'lotSize','Series':'product','ExpiryDate':'expiry','StrikePrice':'strike','OptionType':'right','InstrumentName':'fnoType'}, inplace=True)
        result['token'] = result['idirect_id']
        result['fnoType'] = result['fnoType'].str[:3]
        return json.loads(result.to_json(orient="records"))

    def getTokenFromStockName(self, params: Dict) -> str:
        return self.api.get_stock_token_value(
            params.get("exchangeCode", "NFO"), params.get("stockCode", "CNXBAN"),
            params.get("productType", ""), params.get("expiryDate", ""),
            params.get("strike", ""), params.get("rightType", ""), True, True
        )

    def subscribeQuotes(self, token: str, interval: str):
        return self.api.subscribe_feeds(stock_token=f"4.1!{token}", interval=interval)
        
    def subscribeMarketDepth(self, token: str):
        return self.api.subscribe_feeds(stock_token=f"4.2!{token}", interval="")

    def unsubscribeQuotes(self, token: str, interval: str):
        return self.api.unsubscribe_feeds(stock_token=f"4.1!{token}", interval=interval)
        
    def unsubscribeMarketDepth(self, token: str):
        return self.api.unsubscribe_feeds(stock_token=f"4.2!{token}", interval="")

    def disconnectFeed(self):
        self.api.unsubscribe_feeds(get_order_notification=True)
        self.api.ws_disconnect()

    def getHistoricalData1(self, params: Dict) -> Dict:
        hDataJsonDict = self.api.get_historical_data_v2(
            params.get("interval", "15minute"), params.get("fromDate", "2023-11-01T00:00:00.000Z"),
            params.get("toDate", "2023-11-01T00:00:00.000Z"), params.get("stockCode", "CNXBAN"),
            params.get("exchangeCode", "NSE"), params.get("product", ""),
            params.get("expiry", ""), params.get("right", ""), params.get("strike", "")
        )
        if not hDataJsonDict or hDataJsonDict.get("Error"):
            return hDataJsonDict or {"Error": "Not connected"}
            
        hDataDf = pd.json_normalize(hDataJsonDict["Success"])
        hDataDf["time"] = hDataDf['datetime'].apply(lambda x: datetime.strptime(x,"%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
        hDataDf["value"] = hDataDf["volume"]
        hDataJsonDict["Success"] = json.loads(hDataDf.to_json(orient="records"))
        return hDataJsonDict

    def getApiVersion(self) -> str:
        import sys
        if sys.version_info >= (3, 8):
            from importlib import metadata
        else:
            from importlib_metadata import metadata
        return "breeze_connect " + metadata.version('breeze_connect')