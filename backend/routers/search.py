"""
Endpoints para búsqueda semántica
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import logging

from backend.models import SearchRequest, SearchResponse, SearchResult
from backend.services.search_service import hybrid_search
from backend.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/search", tags=["search"])


@router.post("", response_model=SearchResponse)
def search_transcripts(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    """
    Búsqueda semántica en transcripciones
    
    Permite buscar palabras clave o frases usando embeddings semánticos.
    Los resultados se ordenan por relevancia (similitud coseno).
    
    **Objetivo del proyecto**: Realizar búsquedas específicas de palabras clave o frases.
    
    **Ejemplos de uso**:
    - "problema con internet" - Encuentra problemas técnicos relacionados
    - "cambio de plan" - Encuentra solicitudes comerciales
    - "factura incorrecta" - Encuentra reclamos administrativos
    """
    try:
        # Validar query
        if not request.query or not request.query.strip():
            raise HTTPException(
                status_code=400,
                detail="La consulta de búsqueda no puede estar vacía"
            )
        
        # Validar límites
        if request.limit and (request.limit < 1 or request.limit > 100):
            raise HTTPException(
                status_code=400,
                detail="El límite debe estar entre 1 y 100"
            )
        
        if request.threshold and (request.threshold < 0 or request.threshold > 1):
            raise HTTPException(
                status_code=400,
                detail="El umbral debe estar entre 0 y 1"
            )
        
        results = hybrid_search(
            db=db,
            query=request.query.strip(),
            limit=request.limit or 10,
            threshold=request.threshold or 0.5  # Reducido a 0.5 para encontrar más resultados
        )
        
        search_results = [
            SearchResult(
                transcript_id=transcript.get("id") or 0,
                filename=transcript["filename"],
                similarity=round(similarity, 4),
                snippet=snippet,
                category=transcript.get("category")
            )
            for transcript, similarity, snippet in results
        ]
        
        return SearchResponse(
            query=request.query,
            results=search_results,
            total=len(search_results)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor durante la búsqueda: {str(e)}"
        )

