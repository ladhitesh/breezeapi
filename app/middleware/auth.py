from functools import wraps
from flask import session, jsonify
import logging

logger = logging.getLogger(__name__)

def require_broker_connection(f):
    """Decorator ensuring the user has a selected and connected broker"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from app.container import get_broker_adapter
        
        broker_name = session.get('broker')
        if not broker_name:
            logger.warning("API accessed without a selected broker in session")
            return jsonify({"Error": "No broker selected. Please login."}), 401
            
        try:
            adapter = get_broker_adapter(broker_name)
            if not adapter.isConnected():
                return jsonify({"Error": f"{broker_name} is not connected. Please login."}), 401
        except Exception as e:
            return jsonify({"Error": str(e)}), 500
            
        # Pass the initialized adapter to the route
        return f(adapter, *args, **kwargs)
        
    return decorated_function