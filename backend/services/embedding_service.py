"""
Servicio para gestión de embeddings con cache y soporte vectorial
Usa LangChain y pgvector para búsqueda eficiente
"""
import json
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from sqlalchemy.sql import text

from backend.database import Transcript
from backend.services.langchain_service import get_embedding, get_embeddings_batch
import numpy as np
from backend.utils.text_cleaner import clean_transcript
from backend.config import settings


def get_or_create_embedding(db: Session, transcript: Transcript) -> np.ndarray:
    """
    Obtiene el embedding de una transcripción, usando cache si existe
    Retorna numpy array para compatibilidad con pgvector
    """
    # Si ya tiene embedding, retornarlo
    if transcript.embedding is not None:
        embedding_array = transcript.get_embedding_array()
        if embedding_array is not None:
            if isinstance(embedding_array, np.ndarray):
                return embedding_array
            return np.array(embedding_array)
    
    # Si no, generar y guardar
    cleaned = transcript.cleaned_content or clean_transcript(transcript.content)
    if not cleaned or not cleaned.strip():
        return None
    
    try:
        embedding = get_embedding(cleaned, db)
        if embedding is None:
            return None
        
        # Guardar en DB usando el método set_embedding
        # IMPORTANTE: Asegurar que estamos trabajando con el objeto correcto
        transcript.set_embedding(embedding)
        transcript.cleaned_content = cleaned
        db.flush()
        db.commit()
        
        # Verificar que se guardó correctamente
        db.refresh(transcript)
        
        return np.array(embedding)
    except Exception as e:
        print(f"Error generando embedding para {transcript.filename}: {e}")
        return None


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """Calcula similitud coseno entre dos vectores"""
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))
