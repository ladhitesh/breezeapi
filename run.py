import os
from app import create_app, socketio
from app.config import Config
import logging

app = create_app()
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(f"Starting SocketIO server on {Config.HOST}:{Config.PORT}")
    
    # Check if SSL certificates exist in the root folder
    ssl_args = {}
    if os.path.exists('cert.pem') and os.path.exists('key.pem'):
        logger.info("SSL certificates found. Starting with HTTPS.")
        ssl_args['ssl_context'] = ('cert.pem', 'key.pem')
    else:
        logger.warning("No SSL certificates found. Starting with HTTP.")

   
    # Run the server
    socketio.run(
        app, 
        host=Config.SOCKETIO_HOST, 
        port=Config.SOCKETIO_PORT, 
        use_reloader=Config.DEBUG,
        allow_unsafe_werkzeug=True,
        **ssl_args
    )
