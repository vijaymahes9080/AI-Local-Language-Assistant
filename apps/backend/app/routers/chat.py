from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Optional
import time
import uuid
from datetime import datetime, timezone
import logging

from app.core.db import get_db
from app.core.models import User, Message, SystemAnalytics, AuditLog, KnowledgeItem
from app.routers.auth import get_current_user
from app.core.security import sanitize_input, detect_prompt_injection, detect_jailbreak, validate_output
from app.core.agents.orchestrator import AgentOrchestrator

router = APIRouter(prefix="/chat", tags=["Chat & Agents"])
logger = logging.getLogger("lingosphere.chat")

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class ChatMessageInput(BaseModel):
    session_id: str
    content: str

class ChatMessageOutput(BaseModel):
    id: str
    session_id: str
    role: str
    content: str
    language: str
    created_at: datetime

class ChatResponse(BaseModel):
    agent: str
    content: str
    latency_ms: float
    security_flagged: bool

# ==========================================
# ROUTE HANDLERS
# ==========================================
@router.post("/message", response_model=ChatResponse)
async def post_message(
    data: ChatMessageInput,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    start_time = time.time()
    
    # 1. AI Security Gate: Heuristic Firewall checks
    is_injection = detect_prompt_injection(data.content)
    is_jailbreak = detect_jailbreak(data.content)
    
    if is_injection or is_jailbreak:
        # Log incident in Audit Log (Security requirement)
        audit = AuditLog(
            id=str(uuid.uuid4()),
            user_id=user.id,
            action="prompt_injection_blocked",
            status="blocked",
            request_payload=data.content
        )
        db.add(audit)
        
        # Save flagged input to message logs
        flagged_message = Message(
            id=str(uuid.uuid4()),
            session_id=data.session_id,
            user_id=user.id,
            role="user",
            content=data.content,
            prompt_injection_flagged=True
        )
        db.add(flagged_message)
        
        # Track safety metric
        analytics = SystemAnalytics(
            event_type="safety_alert",
            metric_name="prompt_firewall_triggers",
            metric_value=1.0,
            metric_metadata={"trigger_type": "injection" if is_injection else "jailbreak", "user_id": user.id}
        )
        db.add(analytics)
        await db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Security Block: Prompt validation failed due to potential injection or jailbreak patterns."
        )
    
    # 2. Context Sanitization (PII Scrubbing)
    scrubbed_input = sanitize_input(data.content)
    
    # Save User message (Sanitized)
    user_msg_id = str(uuid.uuid4())
    user_message = Message(
        id=user_msg_id,
        session_id=data.session_id,
        user_id=user.id,
        role="user",
        content=scrubbed_input
    )
    db.add(user_message)
    
    # 3. Retrieve RAG Knowledge Context (Mock/SQL-based distance)
    rag_context = ""
    try:
        # Simple local fallback: lookup document chunks matching query terms
        words = [w for w in scrubbed_input.split() if len(w) > 3]
        if words:
            # Look up chunks containing query words
            like_filters = [KnowledgeItem.content.ilike(f"%{w}%") for w in words[:3]]
            rag_stmt = select(KnowledgeItem).filter(*like_filters).limit(2)
            rag_res = await db.execute(rag_stmt)
            chunks = rag_res.scalars().all()
            if chunks:
                rag_context = "\n".join([f"Source: {c.file_name} (Part {c.chunk_index}):\n{c.content}" for c in chunks])
                logger.info(f"Retrieved {len(chunks)} knowledge chunks for context.")
    except Exception as e:
        logger.error(f"Error fetching RAG context: {e}")
        
    # 4. Multi-Agent routing & execution
    try:
        agent_result = await AgentOrchestrator.route_and_execute(
            user_query=scrubbed_input,
            user_id=user.id,
            session_id=data.session_id,
            rag_context=rag_context
        )
        agent_name = agent_result["routed_agent"]
        raw_response = agent_result["content"]
    except Exception as e:
        logger.error(f"Agent engine error: {e}")
        agent_name = "GENERAL_ASSISTANT"
        raw_response = "I encountered an error. How can I assist you?"
        
    # 5. Output Validation
    sanitized_response = validate_output(raw_response)
    
    # Save Assistant Response
    assistant_msg_id = str(uuid.uuid4())
    assistant_message = Message(
        id=assistant_msg_id,
        session_id=data.session_id,
        user_id=user.id,
        role="assistant",
        content=sanitized_response
    )
    db.add(assistant_message)
    
    # 6. Observability Metrics
    latency = (time.time() - start_time) * 1000.0  # ms
    
    # Save latency & usage stats
    db.add(SystemAnalytics(
        event_type="api_latency",
        metric_name="chat_message_latency_ms",
        metric_value=latency,
        metric_metadata={"agent": agent_name}
    ))
    db.add(SystemAnalytics(
        event_type="token_usage",
        metric_name="estimated_tokens_total",
        # Mock calculation: 1 word ~ 1.3 tokens
        metric_value=float(len(scrubbed_input.split() + sanitized_response.split()) * 1.3)
    ))
    
    await db.commit()
    
    return ChatResponse(
        agent=agent_name,
        content=sanitized_response,
        latency_ms=latency,
        security_flagged=False
    )

@router.get("/history/{session_id}", response_model=List[ChatMessageOutput])
async def get_history(
    session_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc())
    res = await db.execute(stmt)
    messages = res.scalars().all()
    return messages
