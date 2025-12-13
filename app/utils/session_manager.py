"""
SESSION MANAGER - In-Memory Message Storage

Stores conversation messages in memory for active sessions only.
No database bloat - messages exist only while session is active.

Key Features:
- In-memory storage per session
- Auto-cleanup of inactive sessions
- Thread-safe operations
- Optional persistence for important messages

Usage:
    from app.utils.session_manager import SessionManager
    
    session_mgr = SessionManager()
    
    # Add message to session
    session_mgr.add_message(
        session_id="session-123",
        message_type="questionnaire",
        content="What style are you looking for?",
        metadata={"client_id": "user-456"}
    )
    
    # Get session history
    history = session_mgr.get_session_history("session-123")
    
    # Clear session when done
    session_mgr.clear_session("session-123")
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import threading
import time


@dataclass
class SessionMessage:
    """Single message in a session"""
    message_type: str
    content: str
    timestamp: str
    metadata: Dict
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SessionManager:
    """
    Manages in-memory message storage for active sessions
    
    Messages are stored only while session is active.
    No database persistence unless explicitly requested.
    """
    
    def __init__(self, session_timeout_minutes: int = 30):
        """
        Initialize session manager
        
        Parameters:
        - session_timeout_minutes: Auto-cleanup inactive sessions after this time
        """
        self._sessions: Dict[str, List[SessionMessage]] = {}
        self._session_metadata: Dict[str, Dict] = {}
        self._last_activity: Dict[str, datetime] = {}
        self._lock = threading.Lock()
        self._timeout_minutes = session_timeout_minutes
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_thread.start()
    
    def add_message(
        self,
        session_id: str,
        message_type: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Add a message to session history (in-memory only)
        
        Parameters:
        - session_id: Unique session identifier (e.g., booking_id or conversation_id)
        - message_type: Type of message (questionnaire, reminder, followup, etc.)
        - content: The actual message content
        - metadata: Optional extra data (client_id, booking_id, etc.)
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = []
                self._session_metadata[session_id] = metadata or {}
            
            message = SessionMessage(
                message_type=message_type,
                content=content,
                timestamp=datetime.utcnow().isoformat(),
                metadata=metadata or {}
            )
            
            self._sessions[session_id].append(message)
            self._last_activity[session_id] = datetime.utcnow()
    
    def get_session_history(self, session_id: str) -> List[Dict]:
        """
        Get all messages for a session
        
        Parameters:
        - session_id: Session identifier
        
        Returns:
        - List of message dictionaries (empty list if session not found)
        """
        with self._lock:
            if session_id not in self._sessions:
                return []
            
            # Update last activity
            self._last_activity[session_id] = datetime.utcnow()
            
            return [msg.to_dict() for msg in self._sessions[session_id]]
    
    def get_session_metadata(self, session_id: str) -> Dict:
        """Get metadata for a session"""
        with self._lock:
            return self._session_metadata.get(session_id, {})
    
    def clear_session(self, session_id: str) -> bool:
        """
        Clear all messages for a session
        
        Call this when session ends (booking completed, user logs out, etc.)
        
        Parameters:
        - session_id: Session to clear
        
        Returns:
        - True if session existed and was cleared, False otherwise
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                del self._session_metadata[session_id]
                del self._last_activity[session_id]
                return True
            return False
    
    def get_active_sessions(self) -> List[str]:
        """Get list of all active session IDs"""
        with self._lock:
            return list(self._sessions.keys())
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        with self._lock:
            return len(self._sessions)
    
    def get_message_count(self, session_id: Optional[str] = None) -> int:
        """
        Get message count
        
        Parameters:
        - session_id: If provided, count for that session. Otherwise, total across all sessions.
        
        Returns:
        - Message count
        """
        with self._lock:
            if session_id:
                return len(self._sessions.get(session_id, []))
            else:
                return sum(len(msgs) for msgs in self._sessions.values())
    
    def _cleanup_loop(self) -> None:
        """Background thread to cleanup inactive sessions"""
        while True:
            time.sleep(60)  # Check every minute
            self._cleanup_inactive_sessions()
    
    def _cleanup_inactive_sessions(self) -> int:
        """
        Remove sessions that have been inactive for too long
        
        Returns:
        - Number of sessions cleaned up
        """
        with self._lock:
            now = datetime.utcnow()
            timeout = timedelta(minutes=self._timeout_minutes)
            
            inactive_sessions = [
                session_id
                for session_id, last_active in self._last_activity.items()
                if now - last_active > timeout
            ]
            
            for session_id in inactive_sessions:
                del self._sessions[session_id]
                del self._session_metadata[session_id]
                del self._last_activity[session_id]
            
            return len(inactive_sessions)
    
    def get_stats(self) -> Dict:
        """
        Get statistics about current sessions
        
        Returns:
        - Dictionary with session stats
        """
        with self._lock:
            return {
                "active_sessions": len(self._sessions),
                "total_messages": sum(len(msgs) for msgs in self._sessions.values()),
                "timeout_minutes": self._timeout_minutes,
                "sessions": {
                    session_id: {
                        "message_count": len(messages),
                        "last_activity": self._last_activity[session_id].isoformat(),
                        "metadata": self._session_metadata.get(session_id, {})
                    }
                    for session_id, messages in self._sessions.items()
                }
            }


# Global singleton instance
_session_manager: Optional[SessionManager] = None


def get_session_manager(timeout_minutes: int = 30) -> SessionManager:
    """
    Get or create the global session manager instance
    
    Parameters:
    - timeout_minutes: Session timeout (only used on first call)
    
    Returns:
    - SessionManager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(session_timeout_minutes=timeout_minutes)
    return _session_manager


# Example usage
if __name__ == "__main__":
    import time
    
    # Create session manager
    mgr = SessionManager(session_timeout_minutes=1)  # 1 minute timeout for testing
    
    # Add messages to a session
    session_id = "booking-123"
    
    mgr.add_message(
        session_id=session_id,
        message_type="questionnaire",
        content="What style are you looking for?",
        metadata={"client_id": "user-456"}
    )
    
    mgr.add_message(
        session_id=session_id,
        message_type="response",
        content="I prefer natural outdoor shots",
        metadata={"client_id": "user-456"}
    )
    
    # Get session history
    print("Session history:")
    history = mgr.get_session_history(session_id)
    for msg in history:
        print(f"  [{msg['message_type']}] {msg['content']}")
    
    # Get stats
    print("\nSession stats:")
    stats = mgr.get_stats()
    print(f"  Active sessions: {stats['active_sessions']}")
    print(f"  Total messages: {stats['total_messages']}")
    
    # Clear session
    print("\nClearing session...")
    mgr.clear_session(session_id)
    print(f"Active sessions: {mgr.get_session_count()}")
