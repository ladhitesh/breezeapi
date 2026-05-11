import logging
from flask import request, session
from app.container import get_broker_adapter
from dataprovider import get_data_provider

logger = logging.getLogger(__name__)

def register_socketio_events(socketio):
    """Registers all websocket events for the frontend"""

    @socketio.on('subscribeQuotes')
    def subscribe_quotes(token, interval):
        logger.info(f"Subscribe Quotes -> {token}-{interval}")
        adapter = get_broker_adapter(session.get('broker', 'IDIRECT'))
        adapter.subscribeQuotes(token, interval)
        
        existing_subs = session.get(request.sid, "")
        new_sub = f"{token}-{interval}"
        session[request.sid] = f"{existing_subs};{new_sub}" if existing_subs else new_sub

    @socketio.on('unsubscribeQuotes')
    def unsubscribe_quotes(token, interval):
        logger.info(f"Unsubscribe Quotes -> {token}-{interval}")
        adapter = get_broker_adapter(session.get('broker', 'IDIRECT'))
        adapter.unsubscribeQuotes(token, interval)

    @socketio.on('subscribeMarketDepth')
    def subscribe_market_depth(token):
        logger.info(f"Subscribe Market Depth -> {token}")
        adapter = get_broker_adapter(session.get('broker', 'IDIRECT'))
        adapter.subscribeMarketDepth(token)
        
        existing_subs = session.get(f"md-{request.sid}", "")
        session[f"md-{request.sid}"] = f"{existing_subs};{token}" if existing_subs else token

    @socketio.on('unsubscribeMarketDepth')
    def unsubscribe_market_depth(token):
        logger.info(f"Unsubscribe Market Depth -> {token}")
        adapter = get_broker_adapter(session.get('broker', 'IDIRECT'))
        adapter.unsubscribeMarketDepth(token)

    @socketio.on('disconnect')
    def disconnect():
        try:
            logger.info(f"Client disconnected: {request.sid}")
            adapter = get_broker_adapter(session.get('broker', 'IDIRECT'))
            
            # Clean up quote subscriptions
            client_subs = session.get(request.sid, "")
            for sub in client_subs.split(";"):
                if sub:
                    token, interval = sub.split("-")
                    adapter.unsubscribeQuotes(token, interval)
            
            # Clean up market depth subscriptions
            md_subs = session.get(f"md-{request.sid}", "")
            for sub in md_subs.split(";"):
                if sub:
                    adapter.unsubscribeMarketDepth(sub)
                    
        except Exception as e:
            logger.error(f"Error during disconnect cleanup: {e}")

    @socketio.on_error_default
    def default_error_handler(e):
        logger.error(f"SocketIO Error: {e}")


    @socketio.on('subscribe_quotes')
    def handle_subscribe(data):
        # Determine which provider the user wants to use for data (e.g., from their session)
        provider_name = session.get("dataprovider", "IDIRECT") 
    
        # Get the factory instance
        provider = get_data_provider(provider_name, session_manager, instrument_mapper)
    
        # Connect if it isn't already
        if not provider.is_connected:
            provider.connect()
        
        # Subscribe to the specific token requested by the UI
        instrument_token = data.get("instrument_token")
    
        # Create a callback to push live data back to the frontend
        def emit_to_frontend(tick_data):
            socketio.emit('quote_update', tick_data)
        
        provider.subscribe(instrument_token, callback=emit_to_frontend)