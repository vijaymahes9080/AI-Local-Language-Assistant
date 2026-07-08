from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import engine, Base
from app.core.models import User, LanguageProfile, VoiceProfile, FeatureFlag
from app.core.security import hash_password
from app.routers import auth, chat, voice, rag, admin

# Configure server logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("lingosphere.main")

# ==========================================
# LIFECYCLE SEEDING & SCHEMAS
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks: Create database structures (especially for local SQLite)
    logger.info("Initializing database schemas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schemas ready.")
    
    # Seed default Admin and Feature Flags
    from app.core.db import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        try:
            # Check for existing admin
            from sqlalchemy.future import select
            admin_stmt = select(User).filter(User.email == "admin@lingosphere.ai")
            res = await session.execute(admin_stmt)
            admin_user = res.scalars().first()
            
            if not admin_user:
                logger.info("Seeding default administrator (admin@lingosphere.ai)...")
                new_admin = User(
                    email="admin@lingosphere.ai",
                    phone_number="+919876543210",
                    password_hash=hash_password("adminpass"),
                    role="admin"
                )
                session.add(new_admin)
                await session.flush()
                
                # Seed admin language profile & voice profile
                session.add(LanguageProfile(user_id=new_admin.id, preferred_language="english"))
                session.add(VoiceProfile(user_id=new_admin.id, gender="neutral"))
                logger.info("Admin seeded successfully.")
                
            # Seed default system feature flags
            flags = [
                ("wake_phrase_detection", "Enable voice command trigger engine", True),
                ("dyslexia_font_rendering", "Toggle custom heavy-onset letters render helper", True),
                ("elder_slower_tts", "Auto-slow speech synthesis audio playback speed", True),
                ("realtime_noise_suppression", "Enable client-side noise reduction filters", False)
            ]
            for key, desc, val in flags:
                flag_stmt = select(FeatureFlag).filter(FeatureFlag.flag_key == key)
                flag_res = await session.execute(flag_stmt)
                if not flag_res.scalars().first():
                    session.add(FeatureFlag(flag_key=key, description=desc, is_enabled=val))
                    logger.info(f"Seeded Feature Flag: {key} = {val}")
                    
            await session.commit()
        except Exception as e:
            logger.error(f"Failed database seeding on startup: {e}")
            await session.rollback()
            
    yield
    
    # Shutdown tasks (if any)
    logger.info("Shutting down backend services...")
    await engine.dispose()

# ==========================================
# FASTAPI APP INSTANTIATION
# ==========================================
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Multilingual Local-Language AI Assistant Platform Backend API Gateway",
    lifespan=lifespan
)

# CORS configurations for local developer testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Bind router endpoints
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(chat.router, prefix=settings.API_V1_STR)
app.include_router(voice.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)
app.include_router(admin.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "LingoSphere AI Gateway",
        "docs_url": "/docs"
    }
