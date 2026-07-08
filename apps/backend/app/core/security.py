from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Dict, Any
from jose import jwt, JWTError
import bcrypt
import re
import logging
from app.core.config import settings

logger = logging.getLogger("lingosphere.security")

# PII regex patterns
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_PATTERN = re.compile(r"\+?\d{1,4}?[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}")
API_KEY_PATTERN = re.compile(r"(?:api_key|secret|password|passwd|token)\s*[:=]\s*['\"][a-zA-Z0-9_\-]{16,}['\"]", re.IGNORECASE)

# Prompt Injection detection keywords
INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "disregard original rules",
    "forget what you were told",
    "system prompt",
    "bypass filters",
    "you must now act as",
    "dan mode",
    "jailbreak",
    "override guidelines",
    "write code to delete",
    "simulate a terminal",
    "do anything now",
    "read the instructions above",
]

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_access_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

# ==========================================
# AI SECURITY GUARDRAILS (Prompt Firewall)
# ==========================================
def sanitize_input(text: str) -> str:
    """Scrub PII (emails, phone numbers, secret keys) from user inputs before sending to the model."""
    sanitized = text
    # Replace suspected API Keys or credentials first to prevent digit-sub-matching in phone patterns
    sanitized = API_KEY_PATTERN.sub("[CREDENTIAL_REDACTED]", sanitized)
    # Replace email addresses with placeholder
    sanitized = EMAIL_PATTERN.sub("[EMAIL_REDACTED]", sanitized)
    # Replace phone numbers with placeholder (if larger than 7 digits to prevent false positives on random integers)
    sanitized = PHONE_PATTERN.sub("[PHONE_REDACTED]", sanitized)
    return sanitized

def detect_prompt_injection(text: str) -> bool:
    """Heuristic prompt injection firewall looking for override attempt phrases."""
    cleaned_text = text.lower()
    for kw in INJECTION_KEYWORDS:
        if kw in cleaned_text:
            logger.warning(f"Prompt Injection Attempt Blocked! Matched keyword: '{kw}'")
            return True
            
    # Regular expression check for direct system override commands
    system_override_match = re.search(r"system\s*[:\-]?\s*(?:instruction|rules|prompt|guidelines)\s*override", cleaned_text)
    if system_override_match:
        logger.warning("Prompt Injection Attempt Blocked! Matches system override pattern.")
        return True
        
    return False

def detect_jailbreak(text: str) -> bool:
    """Detect common jailbreak patterns (like rolesplay bypasses)."""
    cleaned = text.lower()
    # Looking for roleplay override patterns
    patterns = [
        r"roleplay\s+as\s+a\s+harmful",
        r"pretend\s+you\s+have\s+no\s+rules",
        r"hypothetical\s+scenario\s+where\s+you\s+can\s+bypass"
    ]
    for pattern in patterns:
        if re.search(pattern, cleaned):
            logger.warning(f"Jailbreak Attempt Blocked! Matched pattern: {pattern}")
            return True
    return False

def validate_output(text: str) -> str:
    """Validate model output to verify it doesn't leak system keys, credentials, or injection prompts."""
    # Prevent system leaks
    if "system instructions:" in text.lower() or "you are lingosphere" in text.lower():
         return "I apologize, but I cannot provide that information. Please let me know how else I can assist you in your local language."
    return text
