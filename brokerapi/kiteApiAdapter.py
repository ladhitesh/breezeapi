import logging
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException

from app.config import Config
from brokerapi.base_adapters import BaseApiAdapter
from brokerapi.base_transformers import RightType
from app.models.orders import OrderStatus

logger = logging.getLogger(__name__)

class KiteApiAdapter(BaseApiAdapter):
    def __init__(self, session_manager, instrument_mapper):
        super().__init__(
            broker_name="KITE", 
            session_manager=session_manager, 
            instrument_mapper=instrument_mapper
        )
        self.api = KiteConnect(api_key=Config.KITE_API_KEY, debug=False)
        self.stockScriptdf = self._instrument_mapper.df
        
        token = self.getSessionToken()
        if token:
            self.api.set_access_token(token)
            try:
                userProfile = self.api.profile()
                if userProfile.get("user_id"):
                    self.user_id = userProfile.get("user_id")
                    self.user_name = userProfile.get("user_name")
                    logger.info("KiteApiAdapter initialized with existing session.")
                else:
                    logger.warning(f"Kite heartbeat failed. Status: {userDetails.status}")
                    self._session_manager.invalidate_session(f"{self.BROKER.lower()}_session")
                    self.access_token = None
            except Exception as e:
                logger.warning(f"Existing Kite session token invalid: {e}")
                # Invalidate the session file so it doesn't happen again
                self._session_manager.invalidate_session(f"{self.BROKER.lower()}_session")
                # Clear the token in memory so isConnected() returns False
                self.access_token = None

    def connect(self, query_params: Dict[str, str]) -> str:
        request_token = query_params.get("request_token")
        if not request_token:
            token = self.getSessionToken()
            if not token:
                raise ValueError("No valid request_token provided for Kite.")
                
        def auth_fn():
            token_data = self.api.generate_session(request_token=request_token, api_secret=Config.KITE_SECRET_KEY)
            access_token = token_data.get('access_token')
            self.api.set_access_token(access_token)
            return access_token

        if request_token:
            token = self._session_manager.connect_and_save(self.BROKER, auth_fn)
        userProfile = self.api.profile()
        self.user_id = userProfile.get("user_id")
        self.user_name = userProfile.get("user_name")
        return token

    def getLoginUrl(self):
        return self.api.login_url()

    def getCustomerDetails(self):
        try:
            userProfile = self.api.profile()
            customerDetails = {"Success": {}}
            if userProfile:
                customerDetails["Success"]["userid"] = userProfile.get("user_id")
                customerDetails["Success"]["user_name"] = userProfile.get("user_name")
                customerDetails["Success"]["broker"] = userProfile.get("broker", "KITE")
            return customerDetails
        except Exception as e:
            return {"Error": str(e)}

    def _extract_token(self, ticks: Dict, tick_type: str) -> str:
        if tick_type in ["MARKET_DEPTH", "QUOTES", "OHLV"]:
            return str(ticks.get('stock_code', ticks.get('symbol', '').split('!')[-1] if '!' in ticks.get('symbol', '') else ''))
        return "order_notification" if tick_type == "ORDER_NOTIFICATION" else "UNKNOWN"

    def _extract_interval(self, ticks: Dict, tick_type: str) -> Optional[str]:
        return str(ticks.get('interval', '')) if tick_type in ["OHLV", "QUOTES"] else None

    # -------------------------------------------------------------------------
    # Instrument Mapping Logic
    # -------------------------------------------------------------------------
    def getInstrumentDetailsByInstruId(self, zerodha_id):
        requiredCol = self.stockScriptdf[["ExAllowed","ShortName","tradingsymbol","trading_symbol","idirect_id","zerodha_id","upstox_id","Series"]]
        result = requiredCol.loc[(self.stockScriptdf["zerodha_id"].astype(str) == str(zerodha_id))].head(1).copy()
        result.rename(columns={'trading_symbol':'code','tradingsymbol':'zerodha_tradingsymbol'}, inplace=True)
        response = {}
        if not result.empty:
            response['token'] = result['idirect_id'].astype(str).item()
            response['idirect_id'] = result['idirect_id'].astype(str).item()
            response['zerodha_id'] = result['zerodha_id'].astype(str).item()
            response['upstox_id'] = result['upstox_id'].astype(str).item()
            response['code'] = result['code'].astype(str).item()
            response['zerodha_tradingsymbol'] = result['zerodha_tradingsymbol'].astype(str).item()
            product = result['Series'].astype(str).item()
            response['product_type'] = "OPTIONS" if product.lower() == 'option' else "FUTURES" if product.lower() == 'future' else product
        return response

    def addInstrumentIdColumns(self, df_row):
        if 'zerodha_id' in df_row.index:
            response = self.getInstrumentDetailsByInstruId(str(df_row["zerodha_id"]))
            df_row['idirect_id'] = response.get('idirect_id')
            df_row['upstox_id'] = response.get('upstox_id')
            df_row['code'] = response.get('code')
            df_row['product_type'] = response.get('product_type')
            return df_row
            
        exchangeCode = df_row['exchange_code']
        stockCode = df_row['stock_code']
        expiryDate = df_row['expiry_date']
        if exchangeCode == "NFO":
            expiryDate = (datetime.strptime(expiryDate,"%d-%b-%Y")).strftime('%Y-%m-%d')
        product = df_row['product_type']
        if product.lower() == 'options': product = "OPTION"
        elif product.lower() == 'futures': product = "FUTURE"
        
        strikePrice = str(df_row['strike_price']).split('.')[0]
        rightEnum = RightType.from_str(df_row['right'])
        
        requiredCol = self.stockScriptdf[["ExAllowed","ShortName","trading_symbol","idirect_id","zerodha_id","upstox_id"]]
        result = requiredCol.loc[
            (self.stockScriptdf["ExAllowed"] == exchangeCode) & (self.stockScriptdf["ShortName"] == stockCode) &
            (self.stockScriptdf["ExpiryDate"] == expiryDate) & (self.stockScriptdf["Series"] == product) &
            (self.stockScriptdf["StrikePrice"] == int(strikePrice)) & (self.stockScriptdf["OptionType"] == rightEnum.value)
        ].head(1).copy()
        
        result.rename(columns={'trading_symbol':'code'}, inplace=True)
        if not result.empty:
            df_row['idirect_id'] = result['idirect_id'].astype(str).item()
            df_row['zerodha_id'] = result['zerodha_id'].astype(str).item()
            df_row['upstox_id'] = result['upstox_id'].astype(str).item()
            df_row['code'] = result['code'].astype(str).item()
        return df_row

    def getFnOStocks(self, *searchList):
        base, expr = r'^{}', '(?=.*{})'
        searchRegex = base.format(''.join(expr.format(w) for w in searchList))
        requiredCol = self.stockScriptdf[["TK","CD","EC","SC","SN", "LS"]]
        result = requiredCol.loc[
            (self.stockScriptdf["SG"] == "DERIVATIVE") & 
            (self.stockScriptdf["CD"].str.contains(searchRegex, na=False, case=False) | self.stockScriptdf["SN"].str.contains(searchRegex, na=False, case=False))
        ].head(10).copy()
        result.rename(columns={'TK':'token', 'CD':'code','EC':'exchangeCode','SC':'stockCode', 'LS':'lotSize'}, inplace=True)
        result = result.apply(self.addInstrumentIdColumns, axis=1)
        return json.loads(result.to_json(orient="records"))

    # -------------------------------------------------------------------------
    # Orders Management
    # -------------------------------------------------------------------------
    def placeOrder(self, params: Dict) -> Dict:
        quantity = int(params.get("quantity", "1"))
        price = float(params.get("price", "1"))
        stoploss = float(params.get("stoploss", "0"))
        action = params.get("action").upper()
        instrumentId = params.get("zerodha_id", "")
        
        zerodha_tradingsymbol = ""
        if instrumentId:
            responseDict = self.getInstrumentDetailsByInstruId(instrumentId)
            zerodha_tradingsymbol = responseDict.get("zerodha_tradingsymbol", "")
            
        exchangeCode = "NFO"
        orderType = "MARKET" if price == 0 else "LIMIT"
        
        try:
            order_response = self.api.place_order(
                variety='regular', exchange=exchangeCode, tradingsymbol=zerodha_tradingsymbol,
                transaction_type=action, quantity=quantity, product='NRML',
                order_type=orderType, price=price, validity='DAY', trigger_price=stoploss, tag="hiteshapi"
            )
            return {"Success": {"message": "order placed successfully.check status.", "order_id": order_response}}
        except KiteException as ex:
            return {"Error": f"Check logs for error: {str(ex)}"}

    def squareOffOrder(self, params: Dict) -> Dict:
        # Preserved exact original logic for backward compatibility
        stockCode = params.get("stockCode", "CNXBAN")
        quantity = params.get("quantity", "1")
        priceStr = params.get("price", "1")
        stoploss = params.get("stoploss", "")
        action = params.get("action")
        product = "options" if params.get("product", "options").lower() == "option" else "futures"
        exchangeCode = params.get("exchangeCode", "NFO")
        
        strike, rightTypeStr = "", ""
        if exchangeCode == "NFO":
            expiryDateStr = params.get("expiryDate")
            expiryDate = datetime.strptime(expiryDateStr, "%d-%b-%Y")
            if product == "options":
                strike = params.get("strike", "NA")
                rightTypeStr = RightType.from_str(params.get("rightType", "NA")).name

        todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
        expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
        return self.api.square_off(
            stock_code=stockCode, exchange_code=exchangeCode, product=product,
            action=action, order_type="limit" if priceStr != "0" else "market",
            stoploss=stoploss, quantity=quantity, price=priceStr, validity="day",
            validity_date=todayStr, disclosed_quantity="0", expiry_date=expiryStr, right=rightTypeStr, strike_price=strike
        )

    def modifyOrder(self, params: Dict) -> Dict:
        orderIdStr = params.get("orderId", "")
        price = float(params.get("price", "0"))
        quantity = int(params.get("quantity", "0"))
        stopLoss = float(params.get("stoploss", "0"))
        orderType = "MARKET" if price == 0 else "LIMIT"
        if stopLoss > 0: orderType = "SL"

        try:
            modifyResponse = self.api.modify_order(
                variety='regular', order_id=orderIdStr, quantity=quantity,
                price=price, order_type=orderType, trigger_price=stopLoss, validity="DAY"
            )
            return {"Success": {"message": f"Order {orderIdStr} modified successfully", "order_id": modifyResponse}}
        except Exception as e:
            return {"Error": str(e)}

    def cancelOrder(self, orderRef: str) -> Dict:
        try:
            cancelResponse = self.api.cancel_order(variety='regular', order_id=orderRef)
            return {"Success": {"message": f"Order {cancelResponse} cancelled successfully"}}
        except Exception as e:
            return {"Error": str(e)}

    def getOrderDetails(self, orderId: str) -> Dict:
        return self.api.get_order_detail(exchange_code="NFO", order_id=orderId)

    def fixOrderStatus(self, df_row):
        status = df_row['status']
        statusMessage = df_row.get('status_message') or ""
        df_row['status'] = OrderStatus.from_str(status).name
        df_row['status_message'] = f"{status} {statusMessage}"
        return df_row

    def updatePrice(self, df_row):
        if df_row['price'] == 0:
            df_row["price"] = df_row["average_price"]
        return df_row

    def getOrdersList(self, params: Dict) -> Dict:
        fromDateStr = params.get("orderDate", "")
        today = datetime.now()
        
        if not fromDateStr:
            fromDate = today
            toDate = today
        else:
            fromDate = datetime.strptime(fromDateStr, "%d-%m-%Y").date()
            toDate = datetime.strptime(params.get("orderDate", ""), "%d-%m-%Y").date()

        moveBackDays, moveAheadDays = 0, 0
        if fromDate.weekday() == 6: moveBackDays = 1
        if toDate.weekday() == 5: moveAheadDays = 2
        elif toDate.weekday() == 6: moveAheadDays = 1
        if moveBackDays != 0 or moveAheadDays != 0:
            fromDate = fromDate - timedelta(days=moveBackDays)
            toDate = toDate + timedelta(days=moveAheadDays)
            
        orderList = self.api.orders()
        if not orderList:
            return {"Error": "Not connected or no orders"}

        orderListDf = pd.DataFrame(orderList)
        orderListDf["order_timestamp"] = orderListDf["order_timestamp"].astype(str)
        
        orderDateStr = datetime.now().strftime("%Y-%m-%d") if not params.get("orderDate") else fromDate.strftime("%Y-%m-%d")
        
        result = orderListDf.loc[
            (orderListDf["order_timestamp"].str.contains(orderDateStr, na=False, case=False)) & 
            (orderListDf["exchange"].str.contains("NFO", na=False, case=False) | orderListDf["exchange"].str.contains("BFO", na=False, case=False))
        ].copy()

        if not result.empty:
            result.rename(columns={'exchange':'exchange_code', 'order_timestamp':'order_datetime','transaction_type':'action','instrument_token':'zerodha_id', 'trigger_price':'stoploss'}, inplace=True)
            result = result.apply(self.addInstrumentIdColumns, axis=1)
            result = result.apply(self.fixOrderStatus, axis=1)
            result = result.apply(self.updatePrice, axis=1)
            result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
            result.sort_values(by='order_datetime_sorting', inplace=True, ascending=False)
            return {"Success": json.loads(result.to_json(orient="records"))}
        return {"Success": {}}

    # -------------------------------------------------------------------------
    # Portfolio & PnL
    # -------------------------------------------------------------------------
    def getOpenPositionsList(self):
        portfolioPositions = self.api.positions()
        positionList = []
        if portfolioPositions and portfolioPositions.get("net"):
            for position in portfolioPositions["net"]:
                if position["buy_quantity"] == position["sell_quantity"]: continue
                newPosition = {"code": position["tradingsymbol"], "zerodha_id": str(position["instrument_token"])}
                if position["buy_price"] > 0:
                    newPosition.update({"action": "BUY", "average_price": position["buy_price"], "quantity": position["quantity"]})
                instruDetails = self.getInstrumentDetailsByInstruId(newPosition["zerodha_id"])
                newPosition.update(instruDetails)
                positionList.append(newPosition)
        return {"Success": positionList}

    def getPnl(self, params: Dict) -> Dict:
        fromDateStr = params.get("fromDate", datetime.now().strftime("%d-%b-%Y"))
        toDateStr = params.get("toDate", datetime.now().strftime("%d-%b-%Y"))
        
        positionsList = self.api.positions()
        if not positionsList:
            return {"Error": "Not connected"}
            
        if not positionsList.get('day'):
            realisedPnlDf = pd.DataFrame({"realised_pnl": 0, 'realised_pnl_with_taxes': 0}, index=[0])
            return {"Success": json.loads(realisedPnlDf.to_json(orient="records"))[0]}

        tradesListDf = pd.DataFrame(positionsList['day'])
        realised_pnl = tradesListDf['pnl'].sum()
        
        totalCharges = 0
        realised_pnl_with_taxes = realised_pnl - totalCharges
        
        realisedPnlDf = pd.DataFrame({"realised_pnl": round(realised_pnl, 2), 'realised_pnl_with_taxes': round(realised_pnl_with_taxes, 2)}, index=[0])
        return {"Success": json.loads(realisedPnlDf.to_json(orient="records"))[0]}

    def marginCalculator(self, params: Dict) -> Dict:
        quantity = int(params.get("quantity", "1"))
        price = float(params.get("price", "0") or "0")
        action = str(params.get("action")).upper()
        orderType = "MARKET" if price == 0 else "LIMIT"
        zerodha_id = params.get("zerodha_id", "")
        
        instruDetails = self.getInstrumentDetailsByInstruId(zerodha_id)
        zerodha_tradingsymbol = instruDetails.get('zerodha_tradingsymbol')
        
        newPosition = {
            "exchange": "NFO", "product": "NRML", "variety": "regular",
            "tradingsymbol": zerodha_tradingsymbol, "transaction_type": action,
            "price": price, "quantity": quantity, "order_type": orderType
        }
        
        listOfPositions = [newPosition]
        
        if str(params.get("includeOpenPositions", "")).lower() == "true":
            openPositionsDictList = self.getOpenPositionsList()
            if openPositionsDictList and openPositionsDictList.get("Success"):
                for op in openPositionsDictList["Success"]:
                    if op.get('action') != 'NA':
                        listOfPositions.append({
                            "stock_code": op.get("stock_code"), "action": op.get("action"), 
                            "price": op.get("average_price"), "quantity": op.get("quantity"), 
                            "product": op.get("product_type", "NRML")
                        })
        try:
            marginResponse = self.api.order_margins(listOfPositions)
            span_margin_required = sum(float(m["total"]) for m in marginResponse if m["tradingsymbol"] == zerodha_tradingsymbol)
            return {"Success": {"span_margin_required": f"{span_margin_required:.2f}"}}
        except Exception as e:
            return {"Error": f"Check error in server logs: {e}"}

    def getBrokerages(self, params: Dict) -> Dict:
        quantity = params.get("quantity", "1")
        priceStr = params.get("price", "0")
        action = params.get("action")
        orderType = "MARKET" if priceStr in ["0", ""] else "LIMIT"
        
        zerodha_id = params.get("zerodha_id", "")
        instruDetails = self.getInstrumentDetailsByInstruId(zerodha_id)
        
        order = {
            "exchange": "NFO", "tradingsymbol": instruDetails.get('zerodha_tradingsymbol'),
            "transaction_type": str(action).upper(), "variety": "regular", "product": "NRML",
            "order_type": orderType, "quantity": int(quantity), "price": float(priceStr) if priceStr else 0.0
        }
        try:
            brokerageResponse = self.api.order_margins([order])
            brokerage = brokerageResponse[0]["charges"]
            return {"Success": {
                "total_brokerage": f"{brokerage['total']:.2f}",
                "brokerage": f"{brokerage['brokerage']:.2f}",
                "stamp_duty": f"{brokerage['stamp_duty']:.2f}",
                "stt": f"{brokerage['transaction_tax']:.2f}",
                "gst": f"{brokerage['gst']['total']:.2f}",
                "exchange_turnover_charges": f"{brokerage['exchange_turnover_charge']:.2f}",
                "sebi_charges": f"{brokerage['sebi_turnover_charge']:.2f}"
            }}
        except Exception as e:
            return {"Error": "Check error in server logs"}

    def getFunds(self):
        return self.api.get_funds()

    def getApiVersion(self) -> str:
        import sys
        if sys.version_info >= (3, 8):
            from importlib import metadata
        else:
            from importlib_metadata import metadata
        return "kiteconnect " + metadata.version('kiteconnect')