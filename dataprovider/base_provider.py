from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class BaseDataProvider(ABC):
    def __init__(self, provider_name: str, session_manager, instrument_mapper):
        self.provider_name = provider_name.upper()
        self._session_manager = session_manager
        self._instrument_mapper = instrument_mapper
        self.is_connected = False

    def get_session_token(self):
        """Fetches the token saved by the Broker Adapter"""
        token = self._session_manager.get_session(f"{self.provider_name.lower()}_session")
        if not token:
            logger.warning(f"No session file found for {self.provider_name}")
        return token

    @abstractmethod
    def connect(self) -> bool:
        """Initialize the connection (e.g., WebSocket or API client)"""
        pass

    @abstractmethod
    def subscribe(self, instrument_token: str, callback):
        """Subscribe to live ticks/quotes"""
        pass

    @abstractmethod
    def unsubscribe(self, instrument_token: str):
        """Unsubscribe from live ticks/quotes"""
        pass