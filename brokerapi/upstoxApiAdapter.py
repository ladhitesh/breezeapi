import logging
import json
from typing import Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import time

import upstox_client
from upstox_client.rest import ApiException

from app.config import Config
from brokerapi.base_adapters import BaseApiAdapter
from brokerapi.base_transformers import RightType
from app.models.orders import OrderStatus

logger = logging.getLogger(__name__)

class UpstoxApiAdapter(BaseApiAdapter):
    def __init__(self, session_manager, instrument_mapper):
        super().__init__(
            broker_name="UPSTOX", 
            session_manager=session_manager, 
            instrument_mapper=instrument_mapper
        )
        self.loginapi = upstox_client.LoginApi()
        self.stockScriptdf = self._instrument_mapper.df
        self.apiversion = "2.0"
        # 2. DECLARE VARIABLES IMMEDIATELY so they always exist
        self.access_token = None
        # Check if we have a token saved in upstox_session.json
        token = self.getSessionToken()
        # --- ADD THIS DEBUG LINE ---
        logger.warning(f"DEBUG Upstox Init: Token read from file is: {token}")
        if token:
            self._init_upstox_services(token)
            self.access_token = token
            logger.info("UpstoxApiAdapter initialized with existing session.")

    def _init_upstox_services(self, token: str):
        configuration = upstox_client.Configuration()
        configuration.access_token = token
        api_client = upstox_client.ApiClient(configuration)
        
        self.userapi = upstox_client.UserApi(api_client)
        self.orderapi = upstox_client.OrderApi(api_client)
        self.portfolioapi = upstox_client.PortfolioApi(api_client)
        self.marketHolidaysapi = upstox_client.MarketHolidaysAndTimingsApi(api_client)
        self.chargeApi = upstox_client.ChargeApi(api_client)
        self.pnlApi = upstox_client.TradeProfitAndLossApi(api_client)
        
        try:
            userDetails = self.userapi.get_profile(self.apiversion)
            if userDetails.status == "success":
                self.user_id = userDetails.data.user_id
                self.user_name = userDetails.data.user_name
            else:
                # HEARTBEAT FAILED cleanly (No Exception, but status is not success)
                logger.warning(f"Upstox heartbeat failed. Status: {userDetails.status}")
                self._session_manager.invalidate_session(f"{self.BROKER.lower()}_session")
                self.access_token = None
        except Exception as e:
            logger.error(f"Error initializing Upstox services: {e}")
            # Invalidate the session file so it doesn't happen again
            self._session_manager.invalidate_session(f"{self.BROKER.lower()}_session")
            # Clear the token in memory so isConnected() returns False
            self.access_token = None

    def connect(self, query_params: Dict[str, str]) -> str:
        api_session = query_params.get(Config.UPSTOX_SESSION_TOKEN_NAME)
        if not api_session:
            api_session = self.getSessionToken()
            if not api_session:
                raise ValueError("No valid code provided for Upstox OAuth.")
                
        def auth_fn():
            # If the code passed is actually an auth code from redirect, generate token
            # Otherwise assume it's an existing access token
            if len(api_session) < 100:  # Simple heuristic for auth code vs JWT token
                token_res = self.loginapi.token("2", code=api_session, client_id=Config.UPSTOX_API_KEY, 
                                            client_secret=Config.UPSTOX_SECRET_KEY, redirect_uri=Config.UPSTOX_REDIRECT_URL, 
                                            grant_type="authorization_code")
                return token_res.access_token
            return api_session

        token = self._session_manager.connect_and_save(self.BROKER, auth_fn)
        self._init_upstox_services(token)
        return token

    def getLoginUrl(self):
        import urllib.parse
        return Config.UPSTOX_LOGIN_URL + urllib.parse.quote_plus(Config.UPSTOX_API_KEY)

    def getCustomerDetails(self):
        try:
            userDetails = self.userapi.get_profile(self.apiversion)
            customerDetails = {"Success": {}}
            if userDetails.status == "success":
                customerDetails["Success"]["userid"] = userDetails.data.user_id
                customerDetails["Success"]["user_name"] = userDetails.data.user_name
                customerDetails["Success"]["broker"] = userDetails.data.broker
            return customerDetails
        except Exception as e:
            return {"Error": str(e)}

    def _extract_token(self, ticks: Dict, tick_type: str) -> str:
        if "order_id" in ticks:
            return "order_notification"
        return "UNKNOWN"

    def _extract_interval(self, ticks: Dict, tick_type: str) -> Optional[str]:
        return None

    # -------------------------------------------------------------------------
    # Instrument Mapping Logic
    # -------------------------------------------------------------------------
    def getInstrumentDetailsByInstruId(self, upstox_id):
        requiredCol = self.stockScriptdf[["ExAllowed","ShortName","trading_symbol","idirect_id","zerodha_id","upstox_id","Series"]]
        result = requiredCol.loc[(self.stockScriptdf["upstox_id"] == upstox_id)].head(1).copy()
        result.rename(columns={'trading_symbol':'code'}, inplace=True)
        response = {}
        if not result.empty:
            response['token'] = result['idirect_id'].astype(str).item()
            response['idirect_id'] = result['idirect_id'].astype(str).item()
            response['zerodha_id'] = result['zerodha_id'].astype(str).item()
            response['upstox_id'] = result['upstox_id'].astype(str).item()
            response['code'] = result['code'].astype(str).item()
            product = result['Series'].astype(str).item()
            response['product_type'] = "OPTIONS" if product.lower() == 'option' else "FUTURES" if product.lower() == 'future' else product
        return response

    def addInstrumentIdColumns(self, df_row):
        if 'upstox_id' in df_row.index:
            response = self.getInstrumentDetailsByInstruId(df_row["upstox_id"])
            df_row['idirect_id'] = response.get('idirect_id')
            df_row['zerodha_id'] = response.get('zerodha_id')
            df_row['code'] = response.get('code')
            df_row['product_type'] = response.get('product_type')
            return df_row
            
        exchangeCode = df_row['exchange_code']
        stockCode = df_row['stock_code']
        expiryDate = (datetime.strptime(df_row['expiry_date'],"%d-%b-%Y")).strftime('%Y-%m-%d') if exchangeCode == "NFO" else df_row['expiry_date']
        
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
        instrumentId = params.get("upstox_id", "")
        orderType = "MARKET" if price == 0 else "LIMIT"
        amoOrder = False
        
        try:
            marketStatus = self.marketHolidaysapi.get_market_status("NFO").data
            if marketStatus.status != "NORMAL_OPEN": amoOrder = True
        except:
            pass
            
        body = upstox_client.PlaceOrderRequest(
            quantity=quantity, product='D', price=price, order_type=orderType,
            transaction_type=action, trigger_price=stoploss, instrument_token=instrumentId,
            validity='DAY', disclosed_quantity=quantity, is_amo=amoOrder, tag="hitesh"
        )
        
        try:
            order_response = self.orderapi.place_order(body, self.apiversion)
            order_details = self.orderapi.get_order_status(order_id=order_response.data.order_id)
            details = order_details.data
            if details.status_message is None:
                return {"Success": {"message": details.status, "order_id": details.order_id}}
            else:
                return {"Error": details.status_message}
        except Exception as ex:
            return {"Error": "Error occured while placing order. Check logs."}

    def squareOffOrder(self, params: Dict) -> Dict:
        # Preserved backward compatible dummy square_off structure
        stockCode = params.get("stockCode", "CNXBAN")
        quantity = params.get("quantity", "1")
        priceStr = params.get("price", "1")
        stoploss = params.get("stoploss", "")
        action = params.get("action")
        product = "options" if params.get("product", "options").lower() == "option" else "futures"
        exchangeCode = params.get("exchangeCode", "NFO")
        
        strike, rightTypeStr = "", ""
        if exchangeCode == "NFO":
            expiryDate = datetime.strptime(params.get("expiryDate"), "%d-%b-%Y")
            if product == "options":
                strike = params.get("strike", "NA")
                rightTypeStr = RightType.from_str(params.get("rightType", "NA")).name

        todayStr = datetime.now().strftime('%Y-%m-%dT06:00:00.000Z')
        expiryStr = expiryDate.strftime('%Y-%m-%dT06:00:00.000Z')
        # In Upstox, native API doesn't have square_off. Preserving structure.
        return {"Error": "square_off direct call requires explicit implementation in upstox_client."}

    def modifyOrder(self, params: Dict) -> Dict:
        orderIdStr = params.get("orderId", "")
        price = float(params.get("price", "0"))
        quantity = int(params.get("quantity", "0"))
        stopLoss = float(params.get("stoploss", "0"))
        orderType = "MARKET" if price == 0 else "LIMIT"
        if stopLoss > 0: orderType = "SL"

        try:
            body = upstox_client.ModifyOrderRequest(
                price=price, quantity=quantity, validity="DAY", order_id=orderIdStr,
                trigger_price=stopLoss, order_type=orderType
            )
            modifyResponse = self.orderapi.modify_order(body, self.apiversion)
            return {"Success": {"message": f"Order {modifyResponse.data.order_id} modified successfully", "order_id": modifyResponse.data.order_id}}
        except Exception as e:
            return {"Error": str(e)}

    def cancelOrder(self, orderRef: str) -> Dict:
        try:
            cancelResponse = self.orderapi.cancel_order(order_id=orderRef, api_version=self.apiversion)
            return {"Success": {"message": f"Order {cancelResponse.data.order_id} cancelled successfully"}}
        except Exception as e:
            return {"Error": str(e)}

    def fixOrderStatus(self, df_row):
        status = df_row['status']
        statusMessage = df_row.get('status_message') or ""
        df_row['status'] = OrderStatus.from_str(status).name
        df_row['status_message'] = f"{status} {statusMessage}"
        return df_row

    def getOrdersList(self, params: Dict) -> Dict:
        fromDateStr = params.get("orderDate", "")
        today = datetime.now()
        
        if not fromDateStr:
            fromDate, toDate = today, today
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
            
        orderList = self.orderapi.get_order_book(self.apiversion)
        if not orderList or orderList.status == "error":
            return {"Error": "Not connected"}

        if orderList.data:
            orderListDf = pd.DataFrame([o.to_dict() for o in orderList.data])
            orderDateStr = datetime.now().strftime("%Y-%m-%d") if not params.get("orderDate") else fromDate.strftime("%Y-%m-%d")
            
            result = orderListDf.loc[
                (orderListDf["order_timestamp"].str.contains(orderDateStr, na=False, case=False)) & 
                (orderListDf["exchange"].str.contains("NFO", na=False, case=False) | orderListDf["exchange"].str.contains("BFO", na=False, case=False))
            ].copy()
            
            if not result.empty:
                result.rename(columns={'exchange':'exchange_code', 'order_timestamp':'order_datetime','transaction_type':'action','instrument_token':'upstox_id', 'trigger_price':'stoploss'}, inplace=True)
                result = result.apply(self.addInstrumentIdColumns, axis=1)
                result = result.apply(self.fixOrderStatus, axis=1)
                result["order_datetime_sorting"] = pd.to_datetime(result['order_datetime'])
                result.sort_values(by='order_datetime_sorting', inplace=True, ascending=False)
                return {"Success": json.loads(result.to_json(orient="records"))}
        return {"Success": {}}

    # -------------------------------------------------------------------------
    # Portfolio, PnL & Margin
    # -------------------------------------------------------------------------
    def getOpenPositionsList(self):
        portfolioPositionsResponse = self.portfolioapi.get_positions(api_version=self.apiversion)
        positionList = []
        if portfolioPositionsResponse and portfolioPositionsResponse.data:
            for positionData in portfolioPositionsResponse.data:
                position = positionData.to_dict()
                newPosition = {"code": position["trading_symbol"], "upstox_id": position["instrument_token"]}
                if position["buy_price"] > 0:
                    newPosition.update({"action": "BUY", "average_price": position["buy_price"], "quantity": position["quantity"]})
                instruDetails = self.getInstrumentDetailsByInstruId(newPosition["upstox_id"])
                newPosition.update(instruDetails)
                positionList.append(newPosition)
        return {"Success": positionList}

    def getPnl(self, params: Dict) -> Dict:
        fromDate = datetime.strptime(params.get("fromDate", datetime.now().strftime("%d-%b-%Y")), "%d-%b-%Y")
        toDate = datetime.strptime(params.get("toDate", datetime.now().strftime("%d-%b-%Y")), "%d-%b-%Y")
        
        financial_year = str((toDate.year%100)-1) + str(toDate.year%100) if toDate.month < 4 else str((toDate.year%100)) + str((toDate.year%100)+1)
        
        tradesListJsonDict = self.pnlApi.get_trade_wise_profit_and_loss_data(
            api_version=self.apiversion, segment="FO", financial_year=financial_year,
            from_date=fromDate.strftime("%d-%m-%Y"), to_date=toDate.strftime("%d-%m-%Y"), page_number=1, page_size=5000
        )
        
        if not tradesListJsonDict or tradesListJsonDict.status != "success":
            return {"Error": "Not connected"}
            
        if not tradesListJsonDict.data:
            return {"Success": {"realised_pnl": 0, "realised_pnl_with_taxes": 0}}
            
        tradesListDf = pd.DataFrame([o.to_dict() for o in tradesListJsonDict.data])
        realised_pnl = (tradesListDf['sell_amount'] - tradesListDf['buy_amount']).sum()
        
        chargesResponse = self.pnlApi.get_profit_and_loss_charges(
            api_version=self.apiversion, segment="FO", financial_year=financial_year,
            from_date=fromDate.strftime("%d-%m-%Y"), to_date=toDate.strftime("%d-%m-%Y")
        )
        totalCharges = chargesResponse.data.charges_breakdown.to_dict()["total"]
        realised_pnl_with_taxes = realised_pnl - totalCharges
        
        return {"Success": {"realised_pnl": round(realised_pnl, 2), "realised_pnl_with_taxes": round(realised_pnl_with_taxes, 2)}}

    def marginCalculator(self, params: Dict) -> Dict:
        newPosition = upstox_client.Instrument(
            instrument_key=params.get("upstox_id", ""), quantity=int(params.get("quantity", 0)),
            transaction_type=params.get("action", "BUY").upper(), price=float(params.get("price", 0)), product='D'
        )
        
        listOfPositions = []
        if str(params.get("includeOpenPositions", "")).lower() == "true":
            openPositionsDictList = self.getOpenPositionsList()
            if openPositionsDictList and openPositionsDictList.get("Success"):
                for op in openPositionsDictList["Success"]:
                    if op.get('action') != 'NA':
                        listOfPositions.append({"product": op.get("product_type"), "price": op.get("average_price")}) # Simplified struct mapping
        
        listOfPositions.append(newPosition)
        try:
            body = upstox_client.MarginRequest(instruments=listOfPositions)
            marginResponse = self.chargeApi.post_margin(body)
            return {"Success": {"span_margin_required": f"{marginResponse.data.to_dict()['final_margin']:.2f}"}}
        except Exception as e:
            return {"Error": str(e)}

    def getBrokerages(self, params: Dict) -> Dict:
        try:
            brokerageResponse = self.chargeApi.get_brokerage(
                instrument_token=params.get("upstox_id", "None"), quantity=params.get("quantity", 0),
                transaction_type=params.get("action").upper(), price=float(params.get("price", 1) or 1), 
                product='D', api_version=self.apiversion
            )
            brokerage = brokerageResponse.data.charges.to_dict()
            return {"Success": {
                "total_brokerage": str(brokerage["total"]), "brokerage": str(brokerage["brokerage"]),
                "stamp_duty": str(brokerage["taxes"]["stamp_duty"]), "stt": str(brokerage["taxes"]["stt"]),
                "gst": str(brokerage["taxes"]["gst"]), "exchange_turnover_charges": str(brokerage["other_taxes"]["transaction"]),
                "sebi_charges": str(brokerage["other_taxes"]["sebi_turnover"])
            }}
        except Exception as e:
            return {"Error": "Check error in server logs"}

    def getApiVersion(self) -> str:
        import sys
        if sys.version_info >= (3, 8):
            from importlib import metadata
        else:
            from importlib_metadata import metadata
        return "upstox-python-sdk " + metadata.version('upstox-python-sdk')