from dataclasses import dataclass
from typing import Optional, List
from app.models.orders import Product, OrderAction

@dataclass
class Position:
    """Type-safe position representation (broker-agnostic)"""
    stock_code: str
    product: Product
    action: OrderAction  # BUY (Long) or SELL (Short)
    quantity: int
    average_price: float
    current_price: float = 0.0
    
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    
    # Optional fields for derivatives
    expiry_date: Optional[str] = None
    strike_price: Optional[float] = None
    right_type: Optional[str] = None  # CE/PE
    
    @property
    def total_pnl(self) -> float:
        """Calculate total PnL dynamically"""
        return self.realized_pnl + self.unrealized_pnl

@dataclass
class PositionResponse:
    """Unified response for portfolio/positions"""
    broker: str
    positions: List[Position]
    total_realized_pnl: float = 0.0
    total_unrealized_pnl: float = 0.0