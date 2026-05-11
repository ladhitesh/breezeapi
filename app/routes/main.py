from flask import Blueprint, render_template, session, redirect
from app.container import get_broker_adapter
import logging

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET', 'POST'])
def home_page():
    broker_name = session.get("broker")
    
    # 1. If no broker is in session, redirect to login as usual
    if not broker_name:
        logger.info("No broker in session. Redirecting to login.")
        return redirect("/login", code=302)
        
    # Default values for the template in case of failure
    user_id = ""
    session_key = ""
    login_message = "Not Connected"
    
    try:
        adapter = get_broker_adapter(broker_name)
        
        # 2. Check connection without crashing
        if not adapter.isConnected():
            logger.warning(f"{broker_name} is not connected. Attempting reconnection via connect API.")
            return redirect(f"/connect?broker={broker_name}", code=302)
            
        # 3. Attempt to get customer details
        customer_details = adapter.getCustomerDetails()
        
        # Inside home_page() in main.py...
        customer_details = adapter.getCustomerDetails()
        
        if "Success" in customer_details:
            user = customer_details["Success"]
            
            # FIXED: Check for IDIRECT specific keys first, then fallback to standard keys
            user_id = user.get("idirect_userid", user.get("userid", user.get("client_id", "")))
            user_name = user.get("idirect_user_name", user.get("user_name", user.get("name", "")))
            
            version = adapter.getApiVersion()
            
            login_message = f"{user_id} - {user_name} - {broker_name} ({version})"
            session_key = adapter.getSessionToken()
        else:
            # If we are on the homepage and the heartbeat fails, 
            # kill the session so we don't keep trying a dead connection.
            adapter._session_manager.invalidate_session(broker_name)
            return redirect("/login?force=true")

    except Exception as e:
        # 4. Catch-all for unexpected crashes: Pass the error to the UI instead of a raw JSON screen
        logger.error(f"Unexpected error loading home page: {e}")
        login_message = f"Connection Error: {str(e)}"

    # 5. ALWAYS render index.html, even if there was an error
    return render_template(
        "index.html", 
        output="Session Check Completed", 
        broker=broker_name, 
        userId=user_id, 
        sessionKey=session_key, 
        loginMessage=login_message
    )

# Also expose a route for the manifest file
@main_bp.route('/manifest.json')
def serve_manifest():
    from flask import send_from_directory
    import os
    return send_from_directory(os.path.join(main_bp.root_path, '../../static'), "manifest.json")

from app import socketio
from dataprovider import get_data_provider
from flask import session

@socketio.on('init_dataprovider')
def handle_init_dataprovider(data):
    broker_name = data.get("broker", "IDIRECT")
    
    # Save the preferred data provider in the session so other events know which one to use
    session["dataprovider"] = broker_name
    
    try:
        # 1. Ask the factory for the provider (e.g., BreezeDataProvider)
        provider = get_data_provider(broker_name, session_manager, instrument_mapper)
        
        # 2. Check if it's already connected to avoid duplicate websocket connections
        if not provider.is_connected:
            success = provider.connect()
            
            if success:
                socketio.emit('dataprovider_status', {"status": "Connected", "broker": broker_name})
            else:
                socketio.emit('dataprovider_status', {"status": "Failed to connect", "broker": broker_name})
        else:
            socketio.emit('dataprovider_status', {"status": "Already Connected", "broker": broker_name})
            
    except Exception as e:
        socketio.emit('dataprovider_status', {"status": f"Error: {str(e)}", "broker": broker_name})