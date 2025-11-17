"""
Endpoints para gestión de transcripciones
Carga transcripciones desde archivos en tiempo real
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from backend.database import get_db, Transcript
from backend.models import TranscriptResponse
from backend.services.transcript_loader_service import (
    list_all_transcripts,
    get_transcript_from_file,
    get_transcript_content,
    get_transcript_cleaned,
    count_transcripts
)

router = APIRouter(prefix="/api/transcripts", tags=["transcripts"])


@router.get("")
def list_transcripts(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Lista todas las transcripciones disponibles (desde archivos en tiempo real)
    
    **Parámetros**:
    - `skip`: Número de resultados a omitir (paginación)
    - `limit`: Número máximo de resultados (máximo 100)
    
    **Nota**: Las transcripciones se cargan desde archivos en tiempo real.
    La base de datos solo almacena embeddings y resultados de análisis.
    """
    # Validar parámetros
    if skip < 0:
        raise HTTPException(status_code=400, detail="skip debe ser >= 0")
    
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit debe estar entre 1 y 100")
    
    # Cargar desde archivos (solo 'new' por defecto, no 'sample')
    all_transcripts = list_all_transcripts(include_sample=False)
    
    # Aplicar paginación
    paginated = all_transcripts[skip:skip + limit]
    
    # Para cada transcripción, verificar si tiene análisis en BD
    results = []
    for transcript_info in paginated:
        filename = transcript_info["filename"]
        
        # Buscar en BD si tiene embedding, categoría, etc.
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        # Construir respuesta combinando archivo + BD
        result = {
            "id": db_transcript.id if db_transcript else None,
            "filename": filename,
            "content": None,  # No cargar contenido completo en lista
            "cleaned_content": transcript_info.get("preview", ""),
            "category": db_transcript.category if db_transcript else None,
            "topics": db_transcript.topics if db_transcript else None,
            "created_at": db_transcript.created_at if db_transcript else datetime.utcnow(),
            "updated_at": db_transcript.updated_at if db_transcript else datetime.utcnow()
        }
        results.append(result)
    
    return results


@router.get("/{filename:path}")
def get_transcript(
    filename: str,
    include_content: bool = Query(True, description="Incluir contenido completo"),
    db: Session = Depends(get_db)
):
    """
    Obtiene una transcripción específica desde archivo en tiempo real
    
    **Parámetros**:
    - `filename`: Nombre del archivo (ej: sample_01.txt)
    - `include_content`: Si incluir el contenido completo (default: true)
    """
    # Cargar desde archivo
    transcript_data = get_transcript_from_file(filename)
    
    if not transcript_data:
        raise HTTPException(status_code=404, detail=f"Transcripción {filename} no encontrada")
    
    # Buscar análisis en BD
    db_transcript = db.query(Transcript).filter(
        Transcript.filename == filename
    ).first()
    
    # Construir respuesta
    result = {
        "id": db_transcript.id if db_transcript else None,
        "filename": filename,
        "content": transcript_data["content"] if include_content else None,
        "cleaned_content": transcript_data.get("cleaned_content", ""),
        "category": db_transcript.category if db_transcript else None,
        "topics": db_transcript.topics if db_transcript else None,
        "created_at": db_transcript.created_at if db_transcript else datetime.utcnow(),
        "updated_at": db_transcript.updated_at if db_transcript else datetime.utcnow()
    }
    
    return result

