from dataclasses import dataclass
from typing import Dict, Any, Optional
import pandas as pd
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class RightType(Enum):
    """Unified option type across brokers"""
    CALL = "CE"
    PUT = "PE"
    
    @classmethod
    def from_str(cls, label: str) -> 'RightType':
        if not label:
            raise ValueError("Right type cannot be empty")
        label = label.lower()
        if label in ('ce', 'call'):
            return cls.CALL
        elif label in ('pe', 'put'):
            return cls.PUT
        else:
            raise ValueError(f"Invalid right type: {label}")

@dataclass
class InstrumentFilter:
    """Type-safe instrument filtering parameters"""
    exchange_code: str
    stock_code: str
    expiry_date: Optional[str] = None
    product_type: Optional[str] = None
    strike_price: Optional[float] = None
    right_type: Optional[str] = None

class InstrumentMapper:
    """Centralized instrument mapping to eliminate duplication across brokers"""
    
    def __init__(self, instruments_df: pd.DataFrame):
        self.df = instruments_df
        self._validate_df()
    
    def _validate_df(self):
        """Ensure the CSV has the required standard columns"""
        required_cols = [
            "ExAllowed", "ShortName", "trading_symbol"
        ]
        missing = set(required_cols) - set(self.df.columns)
        if missing:
            logger.warning(f"Instruments CSV is missing expected columns: {missing}")
    
    def get_by_filter(self, filter_: InstrumentFilter) -> Dict[str, Any]:
        """Get instrument details safely across any broker"""
        query = (
            (self.df["ExAllowed"] == filter_.exchange_code) &
            (self.df["ShortName"] == filter_.stock_code)
        )
        
        if filter_.product_type:
            query &= (self.df["Series"] == filter_.product_type)
        if filter_.expiry_date:
            query &= (self.df["ExpiryDate"] == filter_.expiry_date)
        if filter_.strike_price is not None:
            query &= (self.df["StrikePrice"] == filter_.strike_price)
            
        result = self.df[query].head(1)
        if result.empty:
            raise ValueError(f"No instrument found for {filter_}")
        
        # We safely extract whatever ID columns exist for the different brokers
        return {
            "code": str(result["trading_symbol"].iloc[0]),
            "idirect_id": str(result["idirect_id"].iloc[0]) if "idirect_id" in self.df.columns else None,
            "zerodha_id": str(result["zerodha_id"].iloc[0]) if "zerodha_id" in self.df.columns else None,
            "upstox_id": str(result["upstox_id"].iloc[0]) if "upstox_id" in self.df.columns else None,
        }

class TickEventParser:
    """Centralized tick/event parsing logic to remove duplication"""
    
    @staticmethod
    def parse_tick_type(ticks: Dict) -> str:
        """Determine what kind of tick data just arrived from the websocket"""
        if "quotes" in ticks:
            if ticks["quotes"] == "Market Depth":
                return "MARKET_DEPTH"
            elif ticks["quotes"] == "Quotes Data":
                return "QUOTES"
        
        if "sourceNumber" in ticks:
            return "ORDER_NOTIFICATION"
            
        if "feeds" in ticks:
            return "FEEDS_UPDATE"
            
        if "update_type" in ticks:
            if ticks["update_type"] == "order":
                return "ORDER_UPDATE"
                
        return "OHLV"