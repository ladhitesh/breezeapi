import json
import logging
from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO

from app.config import Config
from app.logging_config import setup_logging
from app.container import Container

# Initialize socketio globally
socketio = SocketIO()

def create_app():
    """Flask Application Factory."""
    Config.validate()
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # Define paths to your original static and templates folders
    app = Flask(__name__, 
                template_folder='../templates', 
                static_folder='../static')
                
    app.config.from_object(Config)
    
    # Initialize Extensions
    #CORS(app, resources={r"/*": {"origins": Config.ALLOWED_CORS_ORIGINS}})
    CORS(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Wire the adapters to push live websocket ticks to the frontend
    def emit_feed_data(event_name, data):
        socketio.emit(event_name, json.dumps(data))
    
    Container.get_instance().set_feed_callback(emit_feed_data)
    
    # Register Blueprints (Routes)
    from app.routes import register_blueprints
    register_blueprints(app)
    
    # Register SocketIO Events
    from app.events import register_socketio_events
    register_socketio_events(socketio)
    
    logger.info("BreezeAPI application factory initialized successfully.")
    return app