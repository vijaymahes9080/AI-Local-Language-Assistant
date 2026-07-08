from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

from app.core.db import get_db
from app.core.models import User, Message, SystemAnalytics, AuditLog, FeatureFlag
from app.routers.auth import get_current_user

router = APIRouter(prefix="/admin", tags=["Admin Portal Operations"])
logger = logging.getLogger("lingosphere.admin")

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class FeatureFlagToggle(BaseModel):
    flag_key: str
    is_enabled: bool
    description: str = ""

# ==========================================
# ADMIN DECORATOR (RBAC)
# ==========================================
async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        logger.warning(f"Unauthorized admin access attempt by: {current_user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin credentials required."
        )
    return current_user

# ==========================================
# ROUTE HANDLERS
# ==========================================
@router.get("/metrics")
async def get_system_metrics(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Aggregates latency, usage quotas, failures, and safety alarms (Observability)."""
    # 1. Total users count
    user_stmt = select(func.count(User.id))
    user_res = await db.execute(user_stmt)
    total_users = user_res.scalar() or 0
    
    # 2. Total messages count
    msg_stmt = select(func.count(Message.id))
    msg_res = await db.execute(msg_stmt)
    total_messages = msg_res.scalar() or 0
    
    # 3. Security logs / injection counts
    sec_stmt = select(func.count(AuditLog.id)).filter(AuditLog.action == "prompt_injection_blocked")
    sec_res = await db.execute(sec_stmt)
    firewall_blocks = sec_res.scalar() or 0
    
    # 4. Latency performance metrics
    latency_stmt = select(func.avg(SystemAnalytics.metric_value)).filter(SystemAnalytics.event_type == "api_latency")
    latency_res = await db.execute(latency_stmt)
    avg_latency = latency_res.scalar() or 0.0
    
    # 5. Token metrics
    token_stmt = select(func.sum(SystemAnalytics.metric_value)).filter(SystemAnalytics.event_type == "token_usage")
    token_res = await db.execute(token_stmt)
    total_tokens = token_res.scalar() or 0.0
    
    return {
        "active_users": total_users,
        "total_messages": total_messages,
        "prompt_firewall_triggers": firewall_blocks,
        "average_latency_ms": round(avg_latency, 2),
        "total_tokens_consumed": int(total_tokens)
    }

@router.get("/audit-logs")
async def get_audit_logs(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 50
):
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()
    
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "status": l.status,
            "payload": l.request_payload,
            "timestamp": l.created_at
        } for l in logs
    ]

@router.get("/flags")
async def get_feature_flags(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(FeatureFlag))
    return res.scalars().all()

@router.post("/flags")
async def toggle_feature_flag(
    data: FeatureFlagToggle,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(FeatureFlag).filter(FeatureFlag.flag_key == data.flag_key))
    flag = res.scalars().first()
    
    if not flag:
        flag = FeatureFlag(
            flag_key=data.flag_key,
            is_enabled=data.is_enabled,
            description=data.description
        )
        db.add(flag)
    else:
        flag.is_enabled = data.is_enabled
        if data.description:
            flag.description = data.description
            
    await db.commit()
    logger.info(f"Feature flag updated: {data.flag_key} = {data.is_enabled}")
    return {"message": f"Feature flag {data.flag_key} updated successfully", "flag": data.flag_key, "enabled": data.is_enabled}

@router.get("/db-health")
async def check_database_health(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    try:
        # Trivial check command query
        await db.execute(select(1))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "error": str(e)}
