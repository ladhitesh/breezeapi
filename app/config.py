import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    BASE_DIR = Path(__file__).parent.parent
    
    # Flask
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "fallback-dev-key")
    DEBUG = os.environ.get("FLASK_DEBUG", "False").lower() == "true"

    # Server
    HOST = os.environ.get("HOST", "::")
    PORT = int(os.environ.get("PORT", 5000))
    SOCKETIO_HOST = os.environ.get("SOCKETIO_HOST", "::")
    SOCKETIO_PORT = int(os.environ.get("SOCKETIO_PORT", 5000))
    ALLOWED_CORS_ORIGINS = os.environ.get("ALLOWED_CORS_ORIGINS", "*").split(",")

    #Defaults
    BROKER_DEFAULT = os.environ.get("BROKER_DEFAULT")
    BROKER_IDIRECT = os.environ.get("BROKER_IDIRECT")
    BROKER_KITE = os.environ.get("BROKER_KITE")
    BROKER_UPSTOX = os.environ.get("BROKER_UPSTOX")
    BROKER_TEST = os.environ.get("BROKER_TEST")
    DATAPROVIDER_DEFAULT = os.environ.get("DATAPROVIDER_DEFAULT")
    DATAPROVIDER_IDIRECT = os.environ.get("DATAPROVIDER_IDIRECT")
    
    # Broker Credentials
    IDIRECT_API_KEY = os.environ.get("IDIRECT_API_KEY")
    IDIRECT_SECRET_KEY = os.environ.get("IDIRECT_SECRET_KEY")
    IDIRECT_LOGIN_URL = os.environ.get("IDIRECT_LOGIN_URL")
    IDIRECT_SESSION_TOKEN_NAME = os.environ.get("IDIRECT_SESSION_TOKEN_NAME")

    KITE_API_KEY = os.environ.get("KITE_API_KEY")
    KITE_SECRET_KEY = os.environ.get("KITE_SECRET_KEY")
    KITE_LOGIN_URL = os.environ.get("KITE_LOGIN_URL")
    KITE_SESSION_TOKEN_NAME = os.environ.get("KITE_SESSION_TOKEN_NAME")

    UPSTOX_API_KEY=os.environ.get("UPSTOX_API_KEY")
    UPSTOX_SECRET_KEY=os.environ.get("UPSTOX_SECRET_KEY")
    UPSTOX_LOGIN_URL=os.environ.get("UPSTOX_LOGIN_URL")
    UPSTOX_SESSION_TOKEN_NAME=os.environ.get("UPSTOX_SESSION_TOKEN_NAME")
    UPSTOX_LOGOUT_URL=os.environ.get("UPSTOX_LOGOUT_URL")
    UPSTOX_REDIRECT_URL=os.environ.get("UPSTOX_REDIRECT_URL")
    
    # Path Resolution
    SESSION_DIR = BASE_DIR / "idirectsessiontokens"
    LOG_DIR = BASE_DIR / "logs"
    INSTRUMENTS_PATH = BASE_DIR / "instruments" / "instruments-final.csv"

    @classmethod
    def validate(cls):
        """Validate that critical infrastructure keys exist."""
        required = ["SECRET_KEY", "IDIRECT_API_KEY", "IDIRECT_SECRET_KEY", "IDIRECT_LOGIN_URL", "IDIRECT_SESSION_TOKEN_NAME"]
        missing = [key for key in required if not getattr(cls, key)]
        if missing:
            raise RuntimeError(f"Missing critical environment variables: {', '.join(missing)}")