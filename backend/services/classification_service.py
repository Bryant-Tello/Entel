"""
Servicio de clasificación automática de conversaciones
"""
from typing import List
from sqlalchemy.orm import Session

from backend.database import Transcript
from backend.services.langchain_service import classify_text
from backend.config import settings


def classify_transcripts(
    db: Session,
    transcript_ids: List[int] = None
) -> List[dict]:
    """
    Clasifica transcripciones en categorías
    Carga transcripciones desde archivos en tiempo real
    """
    from backend.services.transcript_loader_service import (
        list_all_transcripts
    )
    
    results = []
    
    if transcript_ids:
        # Clasificar transcripciones específicas por ID
        for transcript_id in transcript_ids:
            db_transcript = db.query(Transcript).filter(
                Transcript.id == transcript_id
            ).first()
            
            if not db_transcript:
                continue
            
            # Cargar contenido limpio desde archivo (sin timestamps, con PII sanitizado)
            from backend.services.transcript_loader_service import get_transcript_cleaned
            cleaned_text = get_transcript_cleaned(db_transcript.filename)
            
            if not cleaned_text:
                # Si no hay contenido limpio, usar el de la BD
                cleaned_text = db_transcript.cleaned_content or ""
            
            if not cleaned_text:
                continue
            
            # Clasificar con texto limpio (sin timestamps, con PII sanitizado)
            classification = classify_text(cleaned_text, db)
            
            # Actualizar en BD
            db_transcript.category = classification["category"]
            db_transcript.tema_principal = classification.get("tema_principal", "")
            db_transcript.palabras_clave = classification.get("palabras_clave", [])
            db.commit()
            
            results.append({
                "transcript_id": db_transcript.id,
                "filename": db_transcript.filename,
                "category": classification["category"],
                "tema_principal": classification.get("tema_principal", ""),
                "palabras_clave": classification.get("palabras_clave", [])
            })
    else:
        # Clasificar solo transcripciones que YA tienen embeddings (subidas por usuario)
        # No generar embeddings automáticamente
        db_transcripts_with_embeddings = db.query(Transcript).filter(
            Transcript.embedding.isnot(None)
        ).all()
        
        for db_transcript in db_transcripts_with_embeddings:
            # Solo clasificar si no tiene categoría
            if db_transcript.category:
                continue
            
            # Cargar contenido limpio desde archivo (sin timestamps, con PII sanitizado)
            from backend.services.transcript_loader_service import get_transcript_cleaned
            cleaned_text = get_transcript_cleaned(db_transcript.filename)
            
            if not cleaned_text:
                # Si no hay contenido limpio, usar el de la BD
                cleaned_text = db_transcript.cleaned_content or ""
            
            if not cleaned_text:
                continue
            
            # Clasificar con texto limpio (sin timestamps, con PII sanitizado)
            classification = classify_text(cleaned_text, db)
            
            # Actualizar en BD
            db_transcript.category = classification["category"]
            db_transcript.tema_principal = classification.get("tema_principal", "")
            db_transcript.palabras_clave = classification.get("palabras_clave", [])
            db.commit()
            
            results.append({
                "transcript_id": db_transcript.id,
                "filename": db_transcript.filename,
                "category": classification["category"],
                "tema_principal": classification.get("tema_principal", ""),
                "palabras_clave": classification.get("palabras_clave", [])
            })
    
    return results

