from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from typing import List, Dict, Any
import numpy as np
import httpx
import logging
import uuid
import hashlib

from app.core.db import get_db
from app.core.models import User, KnowledgeItem
from app.routers.auth import get_current_user
from app.core.config import settings

router = APIRouter(prefix="/rag", tags=["Knowledge & RAG"])
logger = logging.getLogger("lingosphere.rag")

# ==========================================
# PYDANTIC SCHEMAS
# ==========================================
class DocumentInfo(BaseModel):
    file_name: str
    file_type: str
    chunks_count: int

# ==========================================
# UTILITIES: EMBEDDINGS & CHUNKING
# ==========================================
def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """Simple sliding window chunker for raw texts."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

async def get_text_embedding(text: str) -> List[float]:
    """
    Generates a 1536-dimensional vector embedding.
    Uses OpenAI embedding API if key is available, else generates a high-entropy mock vector
    based deterministically on the chunk's content hash.
    """
    if settings.OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/embeddings"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            payload = {
                "input": text,
                "model": "text-embedding-3-small"
            }
            async with httpx.AsyncClient() as client:
                res = await client.post(url, json=payload, headers=headers, timeout=10.0)
                if res.status_code == 200:
                    return res.json()["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Failed to generate OpenAI embedding: {e}")

    # Deterministic Mock Vector generation (so that local search remains reproducible)
    hash_str = hashlib.sha256(text.encode("utf-8")).hexdigest()
    seed = int(hash_str[:8], 16)
    rng = np.random.default_rng(seed)
    
    # Generate 1536 floats and normalize them to unit length
    raw_vec = rng.standard_normal(1536)
    norm = np.linalg.norm(raw_vec)
    normalized_vec = (raw_vec / norm).tolist() if norm > 0 else [0.0] * 1536
    return normalized_vec

# ==========================================
# ROUTE HANDLERS
# ==========================================
@router.post("/upload", response_model=DocumentInfo)
async def upload_document(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        content_bytes = await file.read()
        content_text = content_bytes.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not read uploaded text file: {e}"
        )
        
    if not content_text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty"
        )
        
    # Chunk the document
    chunks = chunk_text(content_text)
    
    # Process & store chunks
    for idx, chunk in enumerate(chunks):
        embedding_vector = await get_text_embedding(chunk)
        
        knowledge_item = KnowledgeItem(
            id=str(uuid.uuid4()),
            user_id=user.id,
            file_name=file.filename,
            file_type=file.content_type or "text/plain",
            chunk_index=idx,
            content=chunk,
            embedding=embedding_vector
        )
        db.add(knowledge_item)
        
    await db.commit()
    logger.info(f"Successfully uploaded and indexed document: {file.filename} ({len(chunks)} chunks)")
    
    return DocumentInfo(
        file_name=file.filename,
        file_type=file.content_type or "text/plain",
        chunks_count=len(chunks)
    )

@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Group by file_name and get counts
    stmt = select(KnowledgeItem.file_name, KnowledgeItem.file_type).filter(KnowledgeItem.user_id == user.id).distinct()
    res = await db.execute(stmt)
    files = res.all()
    
    document_infos = []
    for file_name, file_type in files:
        count_stmt = select(KnowledgeItem).filter(KnowledgeItem.user_id == user.id, KnowledgeItem.file_name == file_name)
        count_res = await db.execute(count_stmt)
        chunks = len(count_res.scalars().all())
        
        document_infos.append(DocumentInfo(
            file_name=file_name,
            file_type=file_type,
            chunks_count=chunks
        ))
        
    return document_infos

@router.delete("/document/{file_name}")
async def delete_document(
    file_name: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(KnowledgeItem).filter(KnowledgeItem.user_id == user.id, KnowledgeItem.file_name == file_name)
    res = await db.execute(stmt)
    chunks = res.scalars().all()
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
        
    for chunk in chunks:
        await db.delete(chunk)
        
    await db.commit()
    logger.info(f"Deleted document index: {file_name}")
    return {"message": f"Successfully deleted document {file_name}"}
