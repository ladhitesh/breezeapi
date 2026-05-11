import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Any

logger = logging.getLogger(__name__)

class SessionStore(ABC):
    """Abstract interface for session storage"""
    @abstractmethod
    def save(self, key: str, token: str, metadata: dict = None) -> None:
        pass
    
    @abstractmethod
    def load(self, key: str) -> Optional[str]:
        pass
    
    @abstractmethod
    def delete(self, key: str) -> None:
        pass
    
    @abstractmethod
    def is_valid(self, key: str) -> bool:
        pass

class FileSessionStore(SessionStore):
    """File-based session storage with automatic expiration (TTL)"""
    
    def __init__(self, storage_dir: Path, ttl_hours: int = 24):
        self.storage_dir = Path(storage_dir)
        self.ttl = timedelta(hours=ttl_hours)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, key: str) -> Path:
        # Sanitize key to prevent path traversal
        safe_key = "".join(c for c in key if c.isalnum() or c in ('_', '-'))
        return self.storage_dir / f"{safe_key}.json"

    def save(self, key: str, token: str, metadata: dict = None) -> None:
        """Save session with metadata and creation timestamp"""
        file_path = self._get_file_path(key)
        data = {
            "token": token,
            "created_at": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        file_path.write_text(json.dumps(data))
        logger.info(f"Session saved securely for key: {key}")
    
    def load(self, key: str) -> Optional[str]:
        """Load session token if it is still valid"""
        if not self.is_valid(key):
            self.delete(key)
            return None
            
        try:
            file_path = self._get_file_path(key)
            data = json.loads(file_path.read_text())
            return data.get("token")
        except Exception as e:
            logger.error(f"Failed to load session {key}: {e}")
            return None
            
    def delete(self, key: str) -> None:
        """Delete session file"""
        file_path = self._get_file_path(key)
        file_path.unlink(missing_ok=True)
        logger.info(f"Session deleted for key: {key}")
        
    def is_valid(self, key: str) -> bool:
        """Check if session exists and has not expired"""
        file_path = self._get_file_path(key)
        if not file_path.exists():
            return False
            
        try:
            data = json.loads(file_path.read_text())
            created_at = datetime.fromisoformat(data["created_at"])
            # Check if token is older than our TTL (24 hours)
            if datetime.utcnow() - created_at > self.ttl:
                logger.warning(f"Session {key} has expired.")
                return False
            return True
        except (json.JSONDecodeError, KeyError, ValueError):
            return False


class SessionManager:
    """Unified session management with built-in retry logic"""
    
    def __init__(self, store: SessionStore, max_retries: int = 3):
        self.store = store
        self.max_retries = max_retries
    
    def connect_and_save(self, broker_name: str, authenticator_fn, *args, **kwargs) -> str:
        """Connect to broker with exponential backoff retry, and save session"""
        token = self._retry(authenticator_fn, *args, **kwargs)
        
        self.store.save(
            key=f"{broker_name.lower()}_session", 
            token=token, 
            metadata={"broker": broker_name, "status": "active"}
        )
        return token
    
    def get_valid_session(self, broker_name: str) -> Optional[str]:
        """Get a valid session token, or None if expired/missing"""
        return self.store.load(f"{broker_name.lower()}_session")
    
    def invalidate_session(self, broker_name: str) -> None:
        """Forcefully delete a broker's session"""
        self.store.delete(f"{broker_name.lower()}_session")
        
    def _retry(self, fn, *args, **kwargs) -> Any:
        """Execute a function with exponential backoff (1s, 2s, 4s)"""
        for attempt in range(self.max_retries):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Action failed after {self.max_retries} attempts. Giving up.")
                    raise
                
                wait_time = 2 ** attempt  # 1, 2, 4 seconds
                logger.warning(f"Attempt {attempt+1} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)