from flask import Blueprint, request, redirect, session, render_template, url_for, jsonify
from app.container import get_broker_adapter
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    query_params = request.args.to_dict()
    mode = query_params.get("mode", "broker") 
    broker_name = query_params.get("broker", "IDIRECT").upper()
    
    # NEW: Check if this is a "force" login (usually from clicking a link)
    # or if we should try to reuse the session.
    force_login = query_params.get("force", "false").lower() == "true"
    
    session["login_mode"] = mode 
    session["newbroker"] = broker_name
    
    try:
        adapter = get_broker_adapter(broker_name)

        # --- ADD THESE DEBUG LINES ---
        logger.warning(f"DEBUG: force_login flag is: {force_login}")
        logger.warning(f"DEBUG: adapter.isConnected() is: {adapter.isConnected()}")
        logger.warning(f"DEBUG: The token loaded by adapter is: {adapter.getSessionToken()}")
        # -----------------------------
        
        # Only skip the login redirect if the session is valid AND we aren't forcing a login
        if not force_login and adapter.isConnected():
            logger.info(f"Existing valid session found for {broker_name}. Skipping redirect.")
            return redirect(url_for('auth.connect_api', **request.args))
            
        # Otherwise, ALWAYS get a fresh URL from the broker
        # This clears the "Session key is expired" trap
        login_url = adapter.getLoginUrl()
        logger.info(f"Redirecting to {broker_name} login: {login_url}")
        return redirect(login_url)

    except Exception as e:
        logger.error(f"Login setup failed: {e}")
        return jsonify({"Error": f"Could not generate login URL: {str(e)}"}), 500

@auth_bp.route('/authorize', methods=['GET', 'POST'])
@auth_bp.route('/auth', methods=['GET', 'POST'])
def authorize():
    """OAuth callbacks from Upstox, Zerodha, and ICICI"""
    return redirect(url_for('auth.connect_api', **request.args))

@auth_bp.route('/connect', methods=['GET', 'POST'])
def connect_api():
    query_params = request.args.to_dict()
    # 1. SMART DETECTION: Identify the broker based on unique callback parameters
    if "code" in query_params:
        broker_name = "UPSTOX"
    elif "request_token" in query_params:
        broker_name = "KITE"
    elif "apisession" in query_params:
        broker_name = "IDIRECT"
    else:
        # Fallback to session if no recognizable parameters are found
        broker_name = session.get("newbroker", session.get("broker", "IDIRECT"))
        
    broker_name = broker_name.upper()
    current_mode = session.get("login_mode", "broker")
    
    try:
        adapter = get_broker_adapter(broker_name)
        # 1. Save the token first
        token = adapter.connect(query_params)
        
        # 2. Perform Heartbeat Check
        customer_details = adapter.getCustomerDetails()
        
        if "Success" in customer_details:
            # Connection is truly alive!
            session["broker"] = broker_name
            session["newbroker"] = ""
            
            user = customer_details["Success"]
            # FIXED: Check for IDIRECT specific keys here as well
            user_id = user.get("idirect_userid", user.get("userid", user.get("client_id", "")))
            user_name = user.get("idirect_user_name", user.get("user_name", user.get("name", "")))
            
            version = adapter.getApiVersion()
            
            login_message = f"{user_id} - {user_name} - {broker_name} ({version})"
            
            return render_template(
                "loginresponse.html", 
                userId=user_id, 
                sessionKey=token, 
                broker=broker_name,
                mode=current_mode,
					 loginMessage=login_message
            )
        else:
            # HEARTBEAT FAILED: Token is new/saved, but API is rejecting it
            error_msg = customer_details.get("Error", "Validation failed")
            logger.error(f"Heartbeat failed for {broker_name} despite new token: {error_msg}")
            try:
                get_broker_adapter(broker_name)._session_manager.invalidate_session(f"{broker_name.lower()}_session")
            except:
                pass
            # We pass the error to the template. The template's JS will 
            # send this message back to index.html to be displayed.
            return render_template(
                "loginresponse.html", 
                error=f"Connected, but API Heartbeat failed: {error_msg}", 
                mode=current_mode, 
                broker=broker_name,
                loginMessage=f"Connected, but API Heartbeat failed: {error_msg}"
            )

    except Exception as e:
        logger.error(f"Critical connection error: {e}")
        return render_template(
            "loginresponse.html", 
            error=f"Connection Error: {str(e)}", 
            mode=current_mode, 
            broker=broker_name,
            loginMessage=f"Connection Error: {str(e)}"
        )