"""
Modelos Pydantic para request/response
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class TranscriptResponse(BaseModel):
    """Respuesta de transcripción"""
    id: int
    cleaned_content: Optional[str] = None
    category: Optional[str] = None
    topics: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class SearchRequest(BaseModel):
    """Request de búsqueda"""
    query: str
    limit: Optional[int] = 10
    threshold: Optional[float] = 0.7


class SearchResult(BaseModel):
    """Resultado de búsqueda"""
    transcript_id: int
    filename: str
    similarity: float
    snippet: str
    category: Optional[str] = None


class SearchResponse(BaseModel):
    """Respuesta de búsqueda"""
    query: str
    results: List[SearchResult]
    total: int


class TopicResponse(BaseModel):
    """Respuesta de temas"""
    topics: List[Dict[str, Any]]
    total_transcripts: int
    grouped_by_category: Optional[Dict[str, List[Dict[str, Any]]]] = None


class ClassificationRequest(BaseModel):
    """Request de clasificación"""
    transcript_ids: Optional[List[int]] = None  # Si None, clasifica todas


class ClassificationResult(BaseModel):
    """Resultado de clasificación"""
    transcript_id: int
    filename: str
    category: str
    confidence: Optional[float] = None


class ClassificationResponse(BaseModel):
    """Respuesta de clasificación"""
    results: List[ClassificationResult]
    total: int

