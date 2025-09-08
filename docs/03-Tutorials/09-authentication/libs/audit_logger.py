"""
Audit logging for MCP authentication system
Provides comprehensive security event logging and monitoring.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
from dataclasses import dataclass, asdict
import aiosqlite


class AuditEventType(str, Enum):
    """Types of audit events"""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    TOKEN_REFRESH = "token_refresh"
    TOKEN_EXPIRED = "token_expired"
    
    # Authorization events
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    PERMISSION_CHECK = "permission_check"
    
    # API Key events
    API_KEY_CREATED = "api_key_created"
    API_KEY_USED = "api_key_used"
    API_KEY_EXPIRED = "api_key_expired"
    API_KEY_REVOKED = "api_key_revoked"
    
    # User management events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DELETED = "user_deleted"
    USER_DISABLED = "user_disabled"
    USER_ENABLED = "user_enabled"
    
    # Security events
    BRUTE_FORCE_DETECTED = "brute_force_detected"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SECURITY_VIOLATION = "security_violation"
    
    # System events
    SERVER_START = "server_start"
    SERVER_STOP = "server_stop"
    CONFIG_CHANGE = "config_change"


class AuditLevel(str, Enum):
    """Audit event severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Audit event data structure"""
    event_type: AuditEventType
    level: AuditLevel
    user_id: Optional[int]
    username: Optional[str]
    resource: Optional[str]
    action: Optional[str]
    details: Dict[str, Any]
    client_info: Dict[str, Any]
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class AuditLogger:
    """Comprehensive audit logging system"""
    
    def __init__(self, db_path: str = "./auth.db", log_file: str = "./logs/audit.log"):
        self.db_path = db_path
        self.log_file = log_file
        self.logger = self._setup_file_logger()
        self._db_initialized = False
    
    def _setup_file_logger(self) -> logging.Logger:
        """Set up file-based logging"""
        logger = logging.getLogger("audit")
        logger.setLevel(logging.INFO)
        
        # Create logs directory if it doesn't exist
        import os
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        
        # File handler
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        
        # JSON formatter for structured logging
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        )
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        return logger
    
    async def init_db(self):
        """Initialize audit database tables"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    level TEXT NOT NULL,
                    user_id INTEGER,
                    username TEXT,
                    resource TEXT,
                    action TEXT,
                    details TEXT,
                    client_info TEXT,
                    success BOOLEAN NOT NULL,
                    error_message TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for common queries
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_events(timestamp)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user 
                ON audit_events(user_id, timestamp)
            """)
            
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_event_type 
                ON audit_events(event_type, timestamp)
            """)
            
            await db.commit()
        
        self._db_initialized = True
    
    async def log_event(self, event: AuditEvent):
        """Log an audit event to both database and file"""
        if not self._db_initialized:
            await self.init_db()
        
        # Log to database
        await self._log_to_database(event)
        
        # Log to file
        self._log_to_file(event)
    
    async def _log_to_database(self, event: AuditEvent):
        """Log event to database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_events (
                    event_type, level, user_id, username, resource, action,
                    details, client_info, success, error_message, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event.event_type.value,
                event.level.value,
                event.user_id,
                event.username,
                event.resource,
                event.action,
                json.dumps(event.details),
                json.dumps(event.client_info),
                event.success,
                event.error_message,
                event.timestamp
            ))
            await db.commit()
    
    def _log_to_file(self, event: AuditEvent):
        """Log event to file"""
        log_data = event.to_dict()
        
        # Choose appropriate log level
        if event.level == AuditLevel.CRITICAL:
            self.logger.critical(json.dumps(log_data))
        elif event.level == AuditLevel.ERROR:
            self.logger.error(json.dumps(log_data))
        elif event.level == AuditLevel.WARNING:
            self.logger.warning(json.dumps(log_data))
        else:
            self.logger.info(json.dumps(log_data))
    
    async def log_authentication(self, event_type: AuditEventType, user_id: Optional[int],
                               username: Optional[str], success: bool,
                               client_info: Dict[str, Any], details: Dict[str, Any] = None,
                               error_message: Optional[str] = None):
        """Log authentication-related events"""
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        if event_type == AuditEventType.BRUTE_FORCE_DETECTED:
            level = AuditLevel.ERROR
        
        event = AuditEvent(
            event_type=event_type,
            level=level,
            user_id=user_id,
            username=username,
            resource="authentication",
            action=event_type.value,
            details=details or {},
            client_info=client_info,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message
        )
        
        await self.log_event(event)
    
    async def log_authorization(self, user_id: int, username: str, resource: str,
                              action: str, success: bool, client_info: Dict[str, Any],
                              details: Dict[str, Any] = None):
        """Log authorization events"""
        event_type = AuditEventType.ACCESS_GRANTED if success else AuditEventType.ACCESS_DENIED
        level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        event = AuditEvent(
            event_type=event_type,
            level=level,
            user_id=user_id,
            username=username,
            resource=resource,
            action=action,
            details=details or {},
            client_info=client_info,
            timestamp=datetime.utcnow(),
            success=success
        )
        
        await self.log_event(event)
    
    async def log_security_event(self, event_type: AuditEventType, level: AuditLevel,
                               client_info: Dict[str, Any], details: Dict[str, Any],
                               user_id: Optional[int] = None, username: Optional[str] = None):
        """Log security-related events"""
        event = AuditEvent(
            event_type=event_type,
            level=level,
            user_id=user_id,
            username=username,
            resource="security",
            action=event_type.value,
            details=details,
            client_info=client_info,
            timestamp=datetime.utcnow(),
            success=False  # Security events are typically failures/violations
        )
        
        await self.log_event(event)
    
    async def log_api_key_event(self, event_type: AuditEventType, user_id: int,
                              username: str, api_key_name: str,
                              client_info: Dict[str, Any], details: Dict[str, Any] = None):
        """Log API key related events"""
        event = AuditEvent(
            event_type=event_type,
            level=AuditLevel.INFO,
            user_id=user_id,
            username=username,
            resource="api_key",
            action=event_type.value,
            details={**(details or {}), "api_key_name": api_key_name},
            client_info=client_info,
            timestamp=datetime.utcnow(),
            success=True
        )
        
        await self.log_event(event)
    
    async def get_audit_events(self, user_id: Optional[int] = None,
                             event_type: Optional[AuditEventType] = None,
                             start_time: Optional[datetime] = None,
                             end_time: Optional[datetime] = None,
                             limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve audit events with filtering"""
        if not self._db_initialized:
            await self.init_db()
        
        query = "SELECT * FROM audit_events WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            events = []
            for row in rows:
                event_data = {
                    "id": row[0],
                    "event_type": row[1],
                    "level": row[2],
                    "user_id": row[3],
                    "username": row[4],
                    "resource": row[5],
                    "action": row[6],
                    "details": json.loads(row[7]) if row[7] else {},
                    "client_info": json.loads(row[8]) if row[8] else {},
                    "success": bool(row[9]),
                    "error_message": row[10],
                    "timestamp": row[11]
                }
                events.append(event_data)
            
            return events
    
    async def get_security_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get security summary for the last N hours"""
        if not self._db_initialized:
            await self.init_db()
        
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with aiosqlite.connect(self.db_path) as db:
            # Failed login attempts
            cursor = await db.execute("""
                SELECT COUNT(*) FROM audit_events 
                WHERE event_type = ? AND timestamp >= ? AND success = 0
            """, (AuditEventType.LOGIN_FAILURE.value, start_time))
            failed_logins = (await cursor.fetchone())[0]
            
            # Successful logins
            cursor = await db.execute("""
                SELECT COUNT(*) FROM audit_events 
                WHERE event_type = ? AND timestamp >= ? AND success = 1
            """, (AuditEventType.LOGIN_SUCCESS.value, start_time))
            successful_logins = (await cursor.fetchone())[0]
            
            # Security violations
            cursor = await db.execute("""
                SELECT COUNT(*) FROM audit_events 
                WHERE event_type IN (?, ?, ?) AND timestamp >= ?
            """, (
                AuditEventType.BRUTE_FORCE_DETECTED.value,
                AuditEventType.SUSPICIOUS_ACTIVITY.value,
                AuditEventType.SECURITY_VIOLATION.value,
                start_time
            ))
            security_violations = (await cursor.fetchone())[0]
            
            # Rate limit violations
            cursor = await db.execute("""
                SELECT COUNT(*) FROM audit_events 
                WHERE event_type = ? AND timestamp >= ?
            """, (AuditEventType.RATE_LIMIT_EXCEEDED.value, start_time))
            rate_limit_violations = (await cursor.fetchone())[0]
            
            # Top users by activity
            cursor = await db.execute("""
                SELECT username, COUNT(*) as activity_count 
                FROM audit_events 
                WHERE timestamp >= ? AND username IS NOT NULL
                GROUP BY username 
                ORDER BY activity_count DESC 
                LIMIT 10
            """, (start_time,))
            top_users = await cursor.fetchall()
            
            return {
                "period_hours": hours,
                "failed_logins": failed_logins,
                "successful_logins": successful_logins,
                "security_violations": security_violations,
                "rate_limit_violations": rate_limit_violations,
                "top_users": [{"username": row[0], "activity_count": row[1]} for row in top_users],
                "generated_at": datetime.utcnow().isoformat()
            }
