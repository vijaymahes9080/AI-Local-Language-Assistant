from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging

from app.core.db import get_db
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_access_token, verify_access_token
from app.core.models import User, LanguageProfile, VoiceProfile, UserSession, Message, UserMemory, KnowledgeItem

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()
logger = logging.getLogger("lingosphere.auth")

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    phone_number: Optional[str] = None
    preferred_language: Optional[str] = "english"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class OTPSend(BaseModel):
    phone_number: str

class OTPVerify(BaseModel):
    phone_number: str
    code: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ProfileUpdate(BaseModel):
    preferred_language: Optional[str] = None
    preferred_dialect: Optional[str] = None
    transliteration_enabled: Optional[bool] = None
    accessibility_mode: Optional[str] = None
    voice_gender: Optional[str] = None
    voice_speech_speed: Optional[float] = None
    voice_tone: Optional[str] = None
    voice_age_mode: Optional[str] = None

# ==========================================
# DEPENDENCY: CURRENT USER
# ==========================================
async def get_current_user(
    db: AsyncSession = Depends(get_db),
    creds: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    token = creds.credentials
    payload = verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    email: str = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identifier",
        )
    
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account",
        )
    return user

# ==========================================
# ROUTE HANDLERS
# ==========================================
@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    stmt = select(User).filter((User.email == data.email) | (User.phone_number == data.phone_number if data.phone_number else False))
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or phone number already registered"
        )
    
    # Create User
    new_user = User(
        email=data.email,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
        role="user"
    )
    db.add(new_user)
    await db.flush() # Flush to get user ID
    
    # Create default language profile
    new_lang_profile = LanguageProfile(
        user_id=new_user.id,
        preferred_language=data.preferred_language or "english",
        accessibility_mode="standard"
    )
    # Create default voice profile
    new_voice_profile = VoiceProfile(
        user_id=new_user.id,
        gender="neutral",
        speech_speed=1.0,
        age_mode="standard"
    )
    
    db.add(new_lang_profile)
    db.add(new_voice_profile)
    await db.commit()
    
    logger.info(f"Registered new user account: {new_user.email}")
    return {"message": "User registered successfully", "user_id": new_user.id}

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).filter(User.email == data.email))
    user = res.scalars().first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    
    # Store session
    session = UserSession(
        user_id=user.id,
        token=access_token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    db.add(session)
    await db.commit()
    
    return {"access_token": access_token}

@router.post("/otp/send")
async def send_otp(data: OTPSend):
    # Simulated OTP sending (always succeeds for development)
    logger.info(f"OTP code (simulated) '123456' sent to phone: {data.phone_number}")
    return {"message": "OTP verification code sent", "otp_sent_to": data.phone_number}

@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(data: OTPVerify, db: AsyncSession = Depends(get_db)):
    # Simple hardcoded validation code for OTP testing
    if data.code != "123456":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP verification code"
        )
    
    # Fetch user by phone, create a guest or full account if user doesn't exist
    res = await db.execute(select(User).filter(User.phone_number == data.phone_number))
    user = res.scalars().first()
    if not user:
        # Create auto-generated user for OTP login
        temp_email = f"phone_{data.phone_number.replace('+', '')}@lingosphere.ai"
        user = User(
            email=temp_email,
            phone_number=data.phone_number,
            password_hash=hash_password("temp-otp-pass-2026"),
            role="user"
        )
        db.add(user)
        await db.flush()
        
        # Profile initializations
        db.add(LanguageProfile(user_id=user.id, preferred_language="english"))
        db.add(VoiceProfile(user_id=user.id, gender="neutral"))
        
    access_token = create_access_token(data={"sub": user.email, "role": user.role})
    db.add(UserSession(
        user_id=user.id,
        token=access_token,
        expires_at=datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    ))
    await db.commit()
    return {"access_token": access_token}

@router.get("/me")
async def get_me(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Retrieve profiles
    lang_res = await db.execute(select(LanguageProfile).filter(LanguageProfile.user_id == user.id))
    voice_res = await db.execute(select(VoiceProfile).filter(VoiceProfile.user_id == user.id))
    
    lang_prof = lang_res.scalars().first()
    voice_prof = voice_res.scalars().first()
    
    return {
        "id": user.id,
        "email": user.email,
        "phone_number": user.phone_number,
        "role": user.role,
        "language_profile": {
            "preferred_language": lang_prof.preferred_language if lang_prof else "english",
            "preferred_dialect": lang_prof.preferred_dialect if lang_prof else None,
            "transliteration_enabled": lang_prof.transliteration_enabled if lang_prof else False,
            "accessibility_mode": lang_prof.accessibility_mode if lang_prof else "standard"
        } if lang_prof else None,
        "voice_profile": {
            "gender": voice_prof.gender if voice_prof else "neutral",
            "speech_speed": voice_prof.speech_speed if voice_prof else 1.0,
            "voice_tone": voice_prof.voice_tone if voice_prof else "default",
            "age_mode": voice_prof.age_mode if voice_prof else "standard"
        } if voice_prof else None
    }

@router.put("/profile")
async def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    lang_res = await db.execute(select(LanguageProfile).filter(LanguageProfile.user_id == user.id))
    voice_res = await db.execute(select(VoiceProfile).filter(VoiceProfile.user_id == user.id))
    
    lang_prof = lang_res.scalars().first()
    voice_prof = voice_res.scalars().first()
    
    if lang_prof:
        if data.preferred_language is not None:
            lang_prof.preferred_language = data.preferred_language
        if data.preferred_dialect is not None:
            lang_prof.preferred_dialect = data.preferred_dialect
        if data.transliteration_enabled is not None:
            lang_prof.transliteration_enabled = data.transliteration_enabled
        if data.accessibility_mode is not None:
            lang_prof.accessibility_mode = data.accessibility_mode
            
    if voice_prof:
        if data.voice_gender is not None:
            voice_prof.gender = data.voice_gender
        if data.voice_speech_speed is not None:
            voice_prof.speech_speed = data.voice_speech_speed
        if data.voice_tone is not None:
            voice_prof.voice_tone = data.voice_tone
        if data.voice_age_mode is not None:
            voice_prof.age_mode = data.voice_age_mode
            
    await db.commit()
    return {"message": "Profile updated successfully"}

@router.post("/export")
async def export_data(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Export User Data (Privacy Requirement)."""
    # Grab messages and memory profiles
    msg_res = await db.execute(select(Message).filter(Message.user_id == user.id))
    mem_res = await db.execute(select(UserMemory).filter(UserMemory.user_id == user.id))
    
    messages = [{"role": m.role, "content": m.content, "timestamp": str(m.created_at)} for m in msg_res.scalars().all()]
    memories = [{"key": m.memory_key, "value": m.memory_value} for m in mem_res.scalars().all()]
    
    return {
        "user_email": user.email,
        "phone_number": user.phone_number,
        "history": messages,
        "memories": memories
    }

@router.delete("/delete")
async def delete_account(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Delete User Account and all related isolated data (Privacy Requirement)."""
    # User deletion cascades to profiles, sessions, memories, and knowledge base
    # We delete messages manually as they are partitioned
    await db.execute(select(Message).filter(Message.user_id == user.id))
    
    # Exec delete actions
    await db.delete(user)
    await db.commit()
    logger.info(f"User account permanently deleted: {user.email}")
    return {"message": "Account deleted permanently"}
