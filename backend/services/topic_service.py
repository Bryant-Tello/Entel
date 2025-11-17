"""
Servicio para extracción de temas principales
Retorna transcripciones agrupadas por categoría con sus temas individuales extraídos por GPT
"""
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from backend.database import Transcript


def extract_topics(
    db: Session,
    num_topics: int = None,
    min_topic_size: int = None
) -> List[Dict[str, Any]]:
    """
    Retorna transcripciones con sus temas principales extraídos por GPT
    
    NOTA: Este endpoint ahora solo retorna las transcripciones agrupadas.
    El agrupamiento real por categoría se hace en el router.
    Cada transcripción ya tiene su tema_principal y palabras_clave extraídos por GPT.
    """
    # Obtener todas las transcripciones que tienen embeddings (subidas por usuario)
    db_transcripts = db.query(Transcript).filter(
        Transcript.embedding.isnot(None)
    ).all()
    
    if not db_transcripts:
        return []
    
    # Procesar cada transcripción para obtener detalles
    transcripts_details = []
    for transcript in db_transcripts:
        transcripts_details.append({
            "conversacion": transcript.filename,
            "clasificacion": transcript.category or "sin_clasificar",
            "tema_principal": transcript.tema_principal or "N/A",
            "palabras_clave": transcript.palabras_clave or []
        })
    
    # Retornar como lista de "temas" (cada transcripción es su propio tema)
    # Esto mantiene compatibilidad con el formato esperado por el frontend
    topics = []
    for idx, trans_detail in enumerate(transcripts_details):
        topics.append({
            "topic_id": idx,
            "size": 1,
            "tema_principal": trans_detail["tema_principal"],
            "palabras_clave": trans_detail["palabras_clave"],
            "transcripciones": [trans_detail]
        })
    
    return topics




