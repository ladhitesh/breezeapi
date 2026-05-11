import pandas as pd
from app.config import Config
from app.services.session_manager import FileSessionStore, SessionManager
from brokerapi.base_transformers import InstrumentMapper

# Import our shiny new refactored adapters
from brokerapi.breezeApiAdapter import BreezeApiAdapter
from brokerapi.kiteApiAdapter import KiteApiAdapter
from brokerapi.upstoxApiAdapter import UpstoxApiAdapter

import logging
logger = logging.getLogger(__name__)

class Container:
    """
    Dependency Injection Container.
    Initializes shared services and manages broker adapter instances safely.
    """
    _instance = None

    def __init__(self):
        # 1. Initialize Shared Services
        self.session_store = FileSessionStore(Config.SESSION_DIR)
        self.session_manager = SessionManager(self.session_store)
        
        # 2. Initialize Instrument Mapper
        try:
            df = pd.read_csv(Config.INSTRUMENTS_PATH)
            self.instrument_mapper = InstrumentMapper(df)
            logger.info(f"Loaded {len(df)} instruments into memory.")
        except Exception as e:
            logger.error(f"Failed to load instruments CSV: {e}")
            self.instrument_mapper = InstrumentMapper(pd.DataFrame(columns=["ExAllowed", "ShortName", "trading_symbol", "idirect_id", "zerodha_id", "upstox_id", "Series"]))

        # 3. Cache for our adapters
        self.brokers = {}

    @classmethod
    def get_instance(cls):
        """Singleton pattern"""
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def set_feed_callback(self, callback_fn):
        """Allows the Application Factory to inject the socket.io emit function"""
        self.feed_callback = callback_fn
        # Update any already-initialized brokers
        for broker_name, adapter in self.brokers.items():
            adapter.registerFeedCallback(self.feed_callback)

    def get_broker_adapter(self, broker_name: str):
        """Get or initialize the requested broker adapter dynamically"""
        broker_name = broker_name.upper()
        
        if broker_name not in self.brokers:
            # Re-added the missing initialization logic!
            if broker_name == "IDIRECT":
                self.brokers[broker_name] = BreezeApiAdapter(self.session_manager, self.instrument_mapper)
            elif broker_name == "KITE":
                self.brokers[broker_name] = KiteApiAdapter(self.session_manager, self.instrument_mapper)
            elif broker_name == "UPSTOX":
                self.brokers[broker_name] = UpstoxApiAdapter(self.session_manager, self.instrument_mapper)
            else:
                raise ValueError(f"Unsupported broker: {broker_name}")
                
            # IMMEDIATELY register the websocket callback if we have one
            if hasattr(self, 'feed_callback'):
                self.brokers[broker_name].registerFeedCallback(self.feed_callback)
                
        return self.brokers[broker_name]

# Expose a simple function to get an adapter
def get_broker_adapter(broker_name: str):
    return Container.get_instance().get_broker_adapter(broker_name)