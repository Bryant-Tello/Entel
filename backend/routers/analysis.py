"""
Endpoints para análisis (temas y clasificación)
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.models import (
    TopicResponse,
    ClassificationRequest,
    ClassificationResponse,
    ClassificationResult
)
from backend.services.topic_service import extract_topics
from backend.services.classification_service import classify_transcripts
from backend.database import get_db

router = APIRouter(prefix="/api", tags=["analysis"])


@router.get("/topics", response_model=TopicResponse)
def get_topics(
    num_topics: int = 10,
    min_topic_size: int = 1,  # Reducido a 1 para permitir temas con pocas transcripciones
    db: Session = Depends(get_db)
):
    """
    Retorna transcripciones con sus temas principales extraídos por GPT
    
    **Objetivo del proyecto**: Extraer temas principales o problemas frecuentes.
    
    Cada transcripción ya tiene su tema_principal y palabras_clave extraídos por GPT.
    Las transcripciones se agrupan por categoría para facilitar la visualización.
    """
    from fastapi import HTTPException
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validar parámetros
        if num_topics < 1 or num_topics > 50:
            raise HTTPException(
                status_code=400,
                detail="num_topics debe estar entre 1 y 50"
            )
        
        if min_topic_size < 1:
            raise HTTPException(
                status_code=400,
                detail="min_topic_size debe ser al menos 1"
            )
        
        topics = extract_topics(db, num_topics=num_topics, min_topic_size=min_topic_size)
        
        # Agrupar transcripciones por clasificación
        from collections import defaultdict
        grouped_by_category = defaultdict(list)
        
        for topic in topics:
            if "transcripciones" in topic:
                for trans in topic["transcripciones"]:
                    category = trans.get("clasificacion", "sin_clasificar")
                    grouped_by_category[category].append({
                        **trans,
                        "topic_id": topic.get("topic_id", 0),
                        "tema_principal_topic": topic.get("tema_principal", "")
                    })
        
        # Contar total de transcripciones desde archivos
        from backend.services.transcript_loader_service import count_transcripts
        total = count_transcripts()
        
        return TopicResponse(
            topics=topics,
            total_transcripts=total,
            grouped_by_category=dict(grouped_by_category)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error extrayendo temas: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.post("/classify", response_model=ClassificationResponse)
def classify(
    request: ClassificationRequest,
    db: Session = Depends(get_db)
):
    """
    Clasifica conversaciones en categorías
    
    **Objetivo del proyecto**: Clasificar automáticamente según categorías relevantes
    (problemas técnicos, soporte comercial, solicitudes administrativas, etc.)
    
    **Categorías disponibles**:
    - `problema_tecnico`: Problemas con servicios (internet, teléfono, etc.)
    - `soporte_comercial`: Consultas y cambios de planes
    - `solicitud_administrativa`: Solicitudes de documentos, facturas
    - `consulta_informacion`: Consultas generales
    - `reclamo`: Reclamos y quejas
    - `venta`: Ventas de nuevos servicios
    - `otro`: Otras categorías
    
    Si no se especifican IDs, clasifica todas las transcripciones
    que aún no tienen categoría asignada.
    
    **Optimización**: Usa few-shot learning con GPT-3.5-turbo para minimizar costos.
    """
    from fastapi import HTTPException
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Validar IDs si se proporcionan
        if request.transcript_ids is not None:
            if not isinstance(request.transcript_ids, list):
                raise HTTPException(
                    status_code=400,
                    detail="transcript_ids debe ser una lista"
                )
            
            if len(request.transcript_ids) > 100:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden clasificar más de 100 transcripciones a la vez"
                )
        
        results = classify_transcripts(
            db=db,
            transcript_ids=request.transcript_ids
        )
        
        classification_results = [
            ClassificationResult(
                transcript_id=r["transcript_id"],
                filename=r["filename"],
                category=r["category"],
                confidence=round(r.get("confidence", 0.0), 2) if r.get("confidence") else None
            )
            for r in results
        ]
        
        return ClassificationResponse(
            results=classification_results,
            total=len(classification_results)
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en clasificación: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del servidor durante la clasificación: {str(e)}"
        )



