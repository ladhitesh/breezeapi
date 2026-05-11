from .base_provider import BaseDataProvider
from breeze_connect import BreezeConnect
from app.config import Config
import logging

logger = logging.getLogger(__name__)

class BreezeDataProvider(BaseDataProvider):
    def __init__(self, session_manager, instrument_mapper):
        # We pass "IDIRECT" so it looks for idirect_session.json
        super().__init__("IDIRECT", session_manager, instrument_mapper)
        self.api = BreezeConnect(api_key=Config.IDIRECT_API_KEY)
        
    def connect(self) -> bool:
        """Attempts to connect to the Breeze WebSocket"""
        token = self.get_session_token()
        
        if not token:
            logger.error("BreezeDataProvider cannot connect: No session token available.")
            self.is_connected = False
            return False

        try:
            # 1. Authorize the SDK with the saved token
            self.api.generate_session(api_secret=Config.IDIRECT_SECRET_KEY, session_token=token)
            
            # 2. Connect the WebSocket
            self.api.ws_connect()
            self.is_connected = True
            logger.info("BreezeDataProvider WebSocket connected successfully.")
            return True
            
        except Exception as e:
            logger.error(f"BreezeDataProvider WebSocket connection failed: {e}")
            self.is_connected = False
            return False

    def subscribe(self, instrument_token: str, callback=None):
        if not self.is_connected:
            logger.warning(f"Cannot subscribe to {instrument_token}. Breeze is not connected.")
            return
            
        try:
            # Example: Subscribing to an instrument. Update this to match your specific
            # Breeze callback logic (e.g., using on_ticks)
            self.api.subscribe_feeds(stock_token=instrument_token, get_exchange_quotes="T")
            if callback:
                self.api.on_ticks = callback
            logger.info(f"Subscribed to quotes for {instrument_token}")
        except Exception as e:
            logger.error(f"Failed to subscribe to {instrument_token}: {e}")

    def unsubscribe(self, instrument_token: str):
        if not self.is_connected:
            return
        try:
            self.api.unsubscribe_feeds(stock_token=instrument_token, get_exchange_quotes="T")
            logger.info(f"Unsubscribed from quotes for {instrument_token}")
        except Exception as e:
            logger.error(f"Failed to unsubscribe: {e}")