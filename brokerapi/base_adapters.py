from abc import ABC, abstractmethod
from typing import Callable, Any, Dict, Optional
from app.services.session_manager import SessionManager
from brokerapi.base_transformers import InstrumentMapper, TickEventParser
from app.models.orders import OrderRequest, OrderResponse
import logging

logger = logging.getLogger(__name__)

class BaseApiAdapter(ABC):
    """
    Modern Abstract Base Class for all broker adapters.
    Handles session state, shared mappings, and standardizes the interface.
    """
    
    def __init__(self, broker_name: str, session_manager: SessionManager, instrument_mapper: InstrumentMapper):
        self.BROKER = broker_name
        self._session_manager = session_manager
        self._instrument_mapper = instrument_mapper
        self.api = None
        self.onMessage: Optional[Callable] = None
    
    def isConnected(self) -> bool:
        """Check if we have an active, valid session"""
        return self._session_manager.get_valid_session(self.BROKER) is not None
    
    def getSessionToken(self) -> Optional[str]:
        return self._session_manager.get_valid_session(self.BROKER)

    def registerFeedCallback(self, callback_fn: Callable):
        """Register the websocket callback"""
        self.onMessage = callback_fn
        
    def _parse_and_emit_tick(self, ticks: Dict):
        """Shared logic for processing incoming websocket ticks"""
        if not self.onMessage:
            return
            
        tick_type = TickEventParser.parse_tick_type(ticks)
        token = self._extract_token(ticks, tick_type)
        interval = self._extract_interval(ticks, tick_type)
        
        event_name = f"{token}_{interval}" if interval else token
        self.onMessage(event_name, ticks)
        
    @abstractmethod
    def _extract_token(self, ticks: Dict, tick_type: str) -> str:
        """Each broker extracts tokens differently from their raw ticks"""
        pass
        
    @abstractmethod
    def _extract_interval(self, ticks: Dict, tick_type: str) -> Optional[str]:
        """Each broker extracts intervals differently"""
        pass

    @abstractmethod
    def connect(self, query_params: Dict[str, str]) -> str:
        """Connect and initialize the API client"""
        pass
        
    @abstractmethod
    def placeOrder(self, request: OrderRequest) -> OrderResponse:
        """Place an order using the standardized OrderRequest model"""
        pass

    def getApiVersion(self) -> str:
        """Returns the SDK version to be displayed on the UI."""
        # Provides a safe fallback for all refactored adapters
        return f"{self.BROKER} SDK (Refactored)"