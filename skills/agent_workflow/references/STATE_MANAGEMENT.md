# State Management Reference

## State Architecture

### Customer State Model

Define the structure for storing customer-specific state:

```python
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
import json

class CustomerState:
    def __init__(self, customer_id: str):
        self.customer_id = customer_id
        self.created_at = datetime.now()
        self.updated_at = datetime.now()

        # Customer profile information
        self.profile = {
            "name": "",
            "email": "",
            "phone": "",
            "company": "",
            "preferences": {},
            "loyalty_tier": "basic"
        }

        # Active conversation context
        self.conversation_context = {
            "current_topic": None,
            "intents": [],
            "entities": {},
            "last_interaction": None
        }

        # Active tickets and issues
        self.active_items = {
            "tickets": [],
            "orders": [],
            "appointments": []
        }

        # Conversation history
        self.history = {
            "messages": [],
            "sessions": [],
            "resolution_attempts": []
        }

        # Temporary state for multi-turn conversations
        self.temp_state = {}

    def update_profile(self, updates: Dict[str, Any]):
        """Update customer profile information."""
        self.profile.update(updates)
        self.updated_at = datetime.now()

    def add_message(self, role: str, content: str, timestamp: datetime = None):
        """Add a message to the conversation history."""
        if timestamp is None:
            timestamp = datetime.now()

        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat()
        }
        self.history["messages"].append(message)
        self.updated_at = datetime.now()

    def set_temp_state(self, key: str, value: Any):
        """Set temporary state for multi-turn conversations."""
        self.temp_state[key] = value

    def get_temp_state(self, key: str, default: Any = None):
        """Get temporary state value."""
        return self.temp_state.get(key, default)

    def clear_temp_state(self):
        """Clear all temporary state."""
        self.temp_state.clear()

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "customer_id": self.customer_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "profile": self.profile,
            "conversation_context": self.conversation_context,
            "active_items": self.active_items,
            "history": self.history,
            "temp_state": self.temp_state
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CustomerState':
        """Create CustomerState from dictionary."""
        state = cls(data["customer_id"])
        state.created_at = datetime.fromisoformat(data["created_at"])
        state.updated_at = datetime.fromisoformat(data["updated_at"])
        state.profile = data["profile"]
        state.conversation_context = data["conversation_context"]
        state.active_items = data["active_items"]
        state.history = data["history"]
        state.temp_state = data.get("temp_state", {})
        return state
```

## State Persistence Strategies

### In-Memory Storage

For simple applications with limited concurrency:

```python
import threading
from typing import Dict

class InMemoryStateManager:
    def __init__(self):
        self._states: Dict[str, CustomerState] = {}
        self._lock = threading.RLock()

    def get_state(self, customer_id: str) -> CustomerState:
        """Get customer state, creating if it doesn't exist."""
        with self._lock:
            if customer_id not in self._states:
                self._states[customer_id] = CustomerState(customer_id)
            return self._states[customer_id]

    def save_state(self, state: CustomerState):
        """Save customer state."""
        with self._lock:
            self._states[state.customer_id] = state

    def delete_state(self, customer_id: str):
        """Delete customer state."""
        with self._lock:
            if customer_id in self._states:
                del self._states[customer_id]

    def cleanup_expired_states(self, max_age_hours: int = 24):
        """Clean up expired states."""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

        with self._lock:
            expired_ids = [
                cid for cid, state in self._states.items()
                if state.updated_at < cutoff_time
            ]

            for customer_id in expired_ids:
                del self._states[customer_id]
```

### Redis-Based Storage

For distributed applications requiring shared state:

```python
import redis
import json
from typing import Optional

class RedisStateManager:
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379,
                 redis_db: int = 0, default_ttl: int = 3600):
        self.redis_client = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
        self.default_ttl = default_ttl  # Default TTL in seconds

    def get_state(self, customer_id: str) -> Optional[CustomerState]:
        """Get customer state from Redis."""
        key = f"customer_state:{customer_id}"
        serialized_state = self.redis_client.get(key)

        if serialized_state:
            data = json.loads(serialized_state)
            return CustomerState.from_dict(data)

        # Create new state if not found
        state = CustomerState(customer_id)
        self.save_state(state)
        return state

    def save_state(self, state: CustomerState, ttl: Optional[int] = None):
        """Save customer state to Redis with optional TTL override."""
        key = f"customer_state:{state.customer_id}"
        serialized_state = json.dumps(state.to_dict())

        if ttl is None:
            ttl = self.default_ttl

        self.redis_client.setex(key, ttl, serialized_state)

    def delete_state(self, customer_id: str):
        """Delete customer state from Redis."""
        key = f"customer_state:{customer_id}"
        self.redis_client.delete(key)

    def extend_state_ttl(self, customer_id: str, ttl: int):
        """Extend the TTL of a customer state."""
        key = f"customer_state:{customer_id}"
        if self.redis_client.exists(key):
            self.redis_client.expire(key, ttl)
```

### Database Storage

For persistent storage across application restarts:

```python
import sqlite3
import json
from typing import Optional

class DatabaseStateManager:
    def __init__(self, db_path: str = "customer_states.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database with required tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS customer_states (
                customer_id TEXT PRIMARY KEY,
                state_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def get_state(self, customer_id: str) -> Optional[CustomerState]:
        """Get customer state from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT state_data FROM customer_states WHERE customer_id = ?",
            (customer_id,)
        )
        row = cursor.fetchone()

        conn.close()

        if row:
            data = json.loads(row[0])
            return CustomerState.from_dict(data)

        # Create new state if not found
        state = CustomerState(customer_id)
        self.save_state(state)
        return state

    def save_state(self, state: CustomerState):
        """Save customer state to database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        state_data = json.dumps(state.to_dict())

        cursor.execute("""
            INSERT OR REPLACE INTO customer_states
            (customer_id, state_data, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (state.customer_id, state_data))

        conn.commit()
        conn.close()

    def delete_state(self, customer_id: str):
        """Delete customer state from database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM customer_states WHERE customer_id = ?",
            (customer_id,)
        )

        conn.commit()
        conn.close()
```

## State Management Patterns

### Session Management

Track conversation sessions and their states:

```python
class SessionManager:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.active_sessions = {}

    def start_session(self, customer_id: str, session_type: str = "chat") -> str:
        """Start a new conversation session."""
        import uuid
        session_id = str(uuid.uuid4())

        state = self.state_manager.get_state(customer_id)

        session_info = {
            "session_id": session_id,
            "customer_id": customer_id,
            "type": session_type,
            "started_at": datetime.now().isoformat(),
            "ended_at": None,
            "status": "active"
        }

        # Add to customer's session history
        state.history["sessions"].append(session_info)

        # Track active session
        self.active_sessions[session_id] = session_info

        # Save updated state
        self.state_manager.save_state(state)

        return session_id

    def end_session(self, session_id: str):
        """End an active session."""
        if session_id in self.active_sessions:
            session_info = self.active_sessions[session_id]

            # Update session info
            session_info["ended_at"] = datetime.now().isoformat()
            session_info["status"] = "completed"

            # Update customer state
            state = self.state_manager.get_state(session_info["customer_id"])

            # Find and update the session in history
            for session in state.history["sessions"]:
                if session["session_id"] == session_id:
                    session.update(session_info)
                    break

            # Clear temporary state for this session
            state.clear_temp_state()

            self.state_manager.save_state(state)

            # Remove from active sessions
            del self.active_sessions[session_id]

    def get_active_session(self, customer_id: str) -> Optional[Dict]:
        """Get the active session for a customer."""
        for session_id, session_info in self.active_sessions.items():
            if session_info["customer_id"] == customer_id and session_info["status"] == "active":
                return session_info
        return None
```

### State Synchronization

Handle concurrent access to customer state:

```python
import asyncio
from contextlib import asynccontextmanager

class SynchronizedStateManager:
    def __init__(self, backend):
        self.backend = backend
        self._locks = {}
        self._lock = threading.Lock()

    def _get_lock(self, customer_id: str):
        """Get or create a lock for a specific customer."""
        with self._lock:
            if customer_id not in self._locks:
                self._locks[customer_id] = threading.Lock()
            return self._locks[customer_id]

    @asynccontextmanager
    async def acquire_state(self, customer_id: str):
        """Context manager to safely access customer state."""
        lock = self._get_lock(customer_id)

        # Acquire lock
        acquired = lock.acquire(timeout=10)  # 10-second timeout
        if not acquired:
            raise TimeoutError(f"Could not acquire lock for customer {customer_id}")

        try:
            # Get the current state
            state = self.backend.get_state(customer_id)
            yield state

            # Save the state back
            self.backend.save_state(state)
        finally:
            # Release the lock
            lock.release()

    async def update_state_safe(self, customer_id: str, update_func):
        """Safely update customer state with a function."""
        async with self.acquire_state(customer_id) as state:
            return update_func(state)
```

## State Migration

Handle schema changes over time:

```python
class StateMigrator:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.migrations = {
            "1.0": self._migrate_v1_to_v2,
            "1.1": self._migrate_v1_1_to_v2,
        }

    def migrate_state(self, state: CustomerState) -> CustomerState:
        """Apply necessary migrations to the state."""
        # Determine current schema version
        current_version = state.profile.get("schema_version", "1.0")

        # Apply migrations in order
        migration_keys = sorted(self.migrations.keys())
        for migration_version in migration_keys:
            if current_version < migration_version:
                state = self.migrations[migration_version](state)
                current_version = migration_version

        # Update schema version
        state.profile["schema_version"] = "2.0"
        return state

    def _migrate_v1_to_v2(self, state: CustomerState) -> CustomerState:
        """Migration from version 1.0 to 2.0."""
        # Add new fields
        if "preferences" not in state.profile:
            state.profile["preferences"] = {}

        # Transform old data structure
        if "contact_info" in state.profile:
            # Move to new structure
            state.profile["email"] = state.profile["contact_info"].get("email", "")
            state.profile["phone"] = state.profile["contact_info"].get("phone", "")
            del state.profile["contact_info"]

        return state

    def _migrate_v1_1_to_v2(self, state: CustomerState) -> CustomerState:
        """Migration from version 1.1 to 2.0."""
        # Additional migration logic if needed
        return state
```

## Performance Considerations

### State Caching

Cache frequently accessed state to improve performance:

```python
from functools import lru_cache
import time

class CachedStateManager:
    def __init__(self, backend, cache_ttl: int = 300):  # 5 minutes default
        self.backend = backend
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_timestamps = {}

    def get_state(self, customer_id: str) -> CustomerState:
        """Get customer state with caching."""
        current_time = time.time()

        # Check if cached and not expired
        if (customer_id in self._cache and
            current_time - self._cache_timestamps[customer_id] < self.cache_ttl):
            return self._cache[customer_id]

        # Load from backend
        state = self.backend.get_state(customer_id)

        # Cache the result
        self._cache[customer_id] = state
        self._cache_timestamps[customer_id] = current_time

        return state

    def invalidate_cache(self, customer_id: str):
        """Invalidate cache for a specific customer."""
        if customer_id in self._cache:
            del self._cache[customer_id]
            del self._cache_timestamps[customer_id]

    def save_state(self, state: CustomerState):
        """Save state and update cache."""
        self.backend.save_state(state)

        # Update cache
        self._cache[state.customer_id] = state
        self._cache_timestamps[state.customer_id] = time.time()
```