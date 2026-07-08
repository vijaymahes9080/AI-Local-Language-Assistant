from sqlalchemy import Column, String, Boolean, DateTime, Float, ForeignKey, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.types import TypeDecorator, TEXT
import uuid
import json
from datetime import datetime, timezone
from app.core.db import Base

# Safe Vector implementation fallback if pgvector package isn't present
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    HAS_PGVECTOR = False

class SafeVector(TypeDecorator):
    """Fallback vector storage using JSON array serialization for non-postgres dialects."""
    impl = TEXT
    cache_ok = True
    
    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return json.dumps(value)
        
    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return json.loads(value)

# Helpers for dynamic ID assignment
def get_uuid():
    return str(uuid.uuid4())

# ==========================================
# MODELS
# ==========================================
class User(Base):
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(50), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class UserSession(Base):
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_info = Column(Text, nullable=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LanguageProfile(Base):
    __tablename__ = "language_profiles"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    preferred_language = Column(String(50), default="english")
    preferred_dialect = Column(String(100), nullable=True)
    transliteration_enabled = Column(Boolean, default=False)
    accessibility_mode = Column(String(50), default="standard")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class VoiceProfile(Base):
    __tablename__ = "voice_profiles"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    gender = Column(String(20), default="neutral")
    speech_speed = Column(Float, default=1.0)
    voice_tone = Column(String(50), default="default")
    age_mode = Column(String(20), default="standard")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    session_id = Column(String(36), nullable=False, index=True)
    user_id = Column(String(36), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    language = Column(String(50), default="english")
    audio_url = Column(Text, nullable=True)
    prompt_injection_flagged = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), primary_key=True, default=lambda: datetime.now(timezone.utc))

class UserMemory(Base):
    __tablename__ = "user_memory"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    memory_key = Column(String(255), nullable=False)
    memory_value = Column(Text, nullable=False)
    significance = Column(Float, default=0.5)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(100), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    
    # Dynamic vector column assignment
    embedding = Column(Vector(1536) if HAS_PGVECTOR else SafeVector, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class SystemAnalytics(Base):
    __tablename__ = "system_analytics"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    event_type = Column(String(100), nullable=False, index=True)
    metric_name = Column(String(255), nullable=False)
    metric_value = Column(Float, nullable=False)
    metric_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), nullable=True)
    action = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    ip_address = Column(String(45), nullable=True)
    request_payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), primary_key=True, default=lambda: datetime.now(timezone.utc))

class FeatureFlag(Base):
    __tablename__ = "feature_flags"
    
    id = Column(String(36), primary_key=True, default=get_uuid)
    flag_key = Column(String(100), unique=True, nullable=False)
    is_enabled = Column(Boolean, default=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
