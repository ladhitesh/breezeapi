from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

class OrderAction(Enum):
    BUY = "BUY"
    SELL = "SELL"

class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"

class Product(Enum):
    EQUITY = "equity"
    FUTURES = "futures"
    OPTIONS = "options"

class OrderStatus(Enum):
    PENDING = "PENDING"
    ORDERED = "ORDERED"
    EXECUTED = "EXECUTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

@dataclass
class OrderRequest:
    """Type-safe order request (broker-agnostic)"""
    action: OrderAction
    stock_code: str
    quantity: int
    product: Product
    exchange_code: str = "NFO"
    
    order_type: OrderType = OrderType.LIMIT
    price: float = 0.0
    stoploss: float = 0.0
    
    # Optional for derivatives
    expiry_date: Optional[str] = None
    strike_price: Optional[float] = None
    right_type: Optional[str] = None  # CE/PE
    
    def validate(self) -> None:
        """Validate critical business logic for the order"""
        if self.quantity <= 0:
            raise ValueError("Quantity must be greater than 0")
        
        if self.order_type == OrderType.LIMIT and self.price <= 0:
            raise ValueError("Price is required and must be > 0 for LIMIT orders")
        
        if self.product == Product.OPTIONS:
            if not self.strike_price or not self.right_type:
                raise ValueError("Strike price and right_type (CE/PE) are required for options")

@dataclass
class OrderResponse:
    """Unified order response across all brokers"""
    order_id: str
    status: OrderStatus
    message: str
    timestamp: datetime
    broker: str
    quantity_filled: int = 0
