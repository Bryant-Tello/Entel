"""
Servicio de búsqueda semántica con soporte vectorial nativo
Usa pgvector para búsquedas eficientes a gran escala
"""
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
import numpy as np
import logging

from backend.database import Transcript
from backend.services.embedding_service import get_or_create_embedding, cosine_similarity
from backend.services.langchain_service import get_embedding as get_embedding_langchain
from backend.utils.text_cleaner import get_snippet
from backend.config import settings

logger = logging.getLogger(__name__)


def hybrid_search(
    db: Session,
    query: str,
    limit: int = 10,
    threshold: float = 0.5
) -> List[Tuple[Dict, float, str]]:
    """
    Búsqueda híbrida: combina búsqueda semántica y por palabras clave
    SIEMPRE usa búsqueda semántica para entender contexto y sinónimos
    También combina con búsqueda por palabras clave para resultados exactos
    """
    from backend.services.transcript_loader_service import get_transcript_cleaned
    
    query_words = query.strip().split()
    
    # SIEMPRE usar búsqueda semántica para entender contexto y sinónimos
    # Ejemplo: "iphone fallado" encontrará "iphone defectuoso", "iphone roto", etc.
    logger.info(f"Query: '{query}' ({len(query_words)} palabras), usando búsqueda semántica + keywords")
    semantic_results = semantic_search(db, query, limit * 2, threshold)  # Obtener más para combinar
    
    # También hacer búsqueda por palabras clave para matches exactos
    keyword_results = keyword_search_enhanced(db, query, limit)
    
    # Combinar resultados (priorizar semántica, pero incluir keyword si no está)
    combined = {}
    
    # Agregar resultados semánticos (estos entienden contexto y sinónimos)
    for transcript_dict, similarity, snippet in semantic_results:
        key = transcript_dict["filename"]
        combined[key] = (transcript_dict, similarity, snippet, "semantic")
    
    # Agregar resultados de keyword (matches exactos, si no están ya)
    for transcript_dict, similarity, snippet in keyword_results:
        key = transcript_dict["filename"]
        if key not in combined:
            # Asignar similitud alta para keyword matches exactos
            combined[key] = (transcript_dict, max(0.85, similarity), snippet, "keyword")
    
    # Convertir a lista y ordenar por relevancia
    results = [(t, s, sn) for t, s, sn, _ in combined.values()]
    results.sort(key=lambda x: x[1], reverse=True)
    
    logger.info(f"Búsqueda híbrida completada: {len(results)} resultados (semánticos: {len(semantic_results)}, keywords: {len(keyword_results)})")
    
    return results[:limit]


def keyword_search_enhanced(
    db: Session,
    query: str,
    limit: int = 10
) -> List[Tuple[Dict, float, str]]:
    """
    Búsqueda mejorada por palabras clave en transcripciones con embeddings
    Busca en el contenido limpio de las transcripciones
    """
    from backend.services.transcript_loader_service import get_transcript_cleaned
    
    query_lower = query.lower().strip()
    query_words = [w.strip() for w in query_lower.split() if w.strip()]
    
    if not query_words:
        return []
    
    # Solo buscar en transcripciones que tienen embeddings (las subidas por usuario)
    transcripts = db.query(Transcript).filter(
        Transcript.embedding.isnot(None)
    ).all()
    
    results = []
    
    for transcript in transcripts:
        # Obtener contenido limpio
        cleaned_content = transcript.cleaned_content
        if not cleaned_content:
            cleaned_content = get_transcript_cleaned(transcript.filename) or ""
        
        if not cleaned_content:
            continue
        
        content_lower = cleaned_content.lower()
        
        # Contar coincidencias de palabras
        matches = sum(1 for word in query_words if word in content_lower)
        
        if matches > 0:
            # Calcular score: más palabras coinciden = mayor score
            score = matches / len(query_words)
            
            # Generar snippet
            snippet = get_snippet(cleaned_content, query)
            
            transcript_dict = {
                "id": transcript.id,
                "filename": transcript.filename,
                "category": transcript.category
            }
            
            results.append((transcript_dict, snippet, score))
    
    # Ordenar por score (coincidencias) descendente
    results.sort(key=lambda x: x[2], reverse=True)
    
    # Retornar con formato (transcript_dict, similarity, snippet) donde similarity = score
    return [(t, score, s) for t, s, score in results[:limit]]


def semantic_search(
    db: Session,
    query: str,
    limit: int = 10,
    threshold: float = 0.5  # Reducido de 0.7 a 0.5 para encontrar más resultados
) -> List[Tuple[Dict, float, str]]:
    """
    Realiza búsqueda semántica SOLO en transcripciones con embeddings
    Los embeddings solo se generan cuando el usuario sube archivos desde el frontend
    """
    from backend.services.transcript_loader_service import get_transcript_cleaned
    
    if not query or not query.strip():
        logger.warning("Query vacía para búsqueda")
        return []
    
    # Obtener embedding de la query
    try:
        logger.info(f"Generando embedding para query: '{query}'")
        query_embedding = get_embedding_langchain(query, db)
        if query_embedding is None:
            logger.warning("No se pudo generar embedding para la query")
            return []
        query_vector = np.array(query_embedding)
        logger.info(f"Embedding de query generado: shape={query_vector.shape}")
    except Exception as e:
        logger.error(f"Error generando embedding para query: {e}", exc_info=True)
        return []
    
    # OPTIMIZACIÓN: Solo buscar en transcripciones que YA tienen embeddings
    # Los embeddings solo se generan cuando el usuario sube archivos desde el frontend
    # NO se incluyen archivos de sample/ en las búsquedas
    db_transcripts_with_embeddings = db.query(Transcript).filter(
        Transcript.embedding.isnot(None)
    ).all()
    
    if not db_transcripts_with_embeddings:
        # No hay transcripciones con embeddings (ninguna subida por usuario)
        logger.info("No hay transcripciones con embeddings para buscar")
        return []
    
    logger.info(f"Buscando en {len(db_transcripts_with_embeddings)} transcripciones con embeddings (threshold={threshold})")
    
    results = []
    all_similarities = []  # Para debugging
    
    # Buscar solo en transcripciones con embeddings (RÁPIDO)
    for db_transcript in db_transcripts_with_embeddings:
        # Obtener embedding (ya existe, no generar)
        transcript_embedding = db_transcript.get_embedding_array()
        if transcript_embedding is None:
            logger.warning(f"Transcripción {db_transcript.filename} tiene embedding=None en BD")
            continue
        
        # Convertir a lista
        if isinstance(transcript_embedding, np.ndarray):
            transcript_emb_list = transcript_embedding.tolist()
        else:
            transcript_emb_list = transcript_embedding
        
        # Validar que el embedding tenga la dimensión correcta
        if len(transcript_emb_list) != len(query_vector):
            logger.warning(f"Embedding de {db_transcript.filename} tiene dimensión incorrecta: {len(transcript_emb_list)} vs {len(query_vector)}")
            continue
        
        # Calcular similitud
        try:
            similarity = cosine_similarity(query_vector.tolist(), transcript_emb_list)
            all_similarities.append((db_transcript.filename, similarity))
            logger.debug(f"Similitud con {db_transcript.filename}: {similarity:.4f}")
        except Exception as e:
            logger.error(f"Error calculando similitud para {db_transcript.filename}: {e}", exc_info=True)
            continue
        
        if similarity >= threshold:
            # Cargar contenido para snippet
            cleaned_content = db_transcript.cleaned_content
            if not cleaned_content:
                cleaned_content = get_transcript_cleaned(db_transcript.filename) or ""
            
            # Generar snippet (si no hay query, mostrar inicio del texto)
            if query and query.strip():
                snippet = get_snippet(cleaned_content, query)
            else:
                snippet = cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content
            
            transcript_dict = {
                "id": db_transcript.id,
                "filename": db_transcript.filename,
                "category": db_transcript.category
            }
            
            results.append((transcript_dict, similarity, snippet))
    
    # Ordenar por similitud descendente
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Log de todas las similitudes para debugging
    if all_similarities:
        all_similarities.sort(key=lambda x: x[1], reverse=True)
        logger.info(f"Todas las similitudes (top 5): {all_similarities[:5]}")
    
    logger.info(f"Búsqueda completada: {len(results)} resultados encontrados (threshold={threshold}, total transcripciones: {len(db_transcripts_with_embeddings)})")
    
    # Si no hay resultados pero hay transcripciones, mostrar las similitudes más altas
    if len(results) == 0 and all_similarities:
        max_sim = max(all_similarities, key=lambda x: x[1])
        logger.warning(f"No se encontraron resultados con threshold={threshold}. Similitud máxima: {max_sim[1]:.4f} con {max_sim[0]}")
    
    # Limitar resultados
    return results[:limit]


def _vector_search_native(
    db: Session,
    query_vector: np.ndarray,
    limit: int,
    threshold: float
) -> List[Tuple[Transcript, float, str]]:
    """
    Búsqueda vectorial nativa usando pgvector (muy eficiente)
    """
    # Convertir a lista para PostgreSQL
    query_list = query_vector.tolist()
    
    # Query SQL con búsqueda por similitud coseno
    sql = text("""
        SELECT 
            id,
            filename,
            content,
            cleaned_content,
            category,
            1 - (embedding <=> :query_vector::vector) as similarity
        FROM transcripts
        WHERE embedding IS NOT NULL
        AND 1 - (embedding <=> :query_vector::vector) >= :threshold
        ORDER BY embedding <=> :query_vector::vector
        LIMIT :limit
    """)
    
    results = db.execute(
        sql,
        {
            "query_vector": str(query_list),
            "threshold": threshold,
            "limit": limit
        }
    ).fetchall()
    
    transcripts_results = []
    for row in results:
        transcript = db.query(Transcript).filter(Transcript.id == row.id).first()
        if transcript:
            similarity = float(row.similarity)
            snippet = get_snippet(
                row.cleaned_content or row.content or "",
                ""  # No tenemos el query original aquí, usar inicio
            )
            transcripts_results.append((transcript, similarity, snippet))
    
    return transcripts_results


def _vector_search_fallback(
    db: Session,
    query_vector: np.ndarray,
    limit: int,
    threshold: float
) -> List[Tuple[Transcript, float, str]]:
    """
    Búsqueda vectorial en memoria (fallback para SQLite o cuando pgvector no está disponible)
    """
    # Obtener todas las transcripciones con embeddings
    transcripts = db.query(Transcript).filter(
        Transcript.embedding.isnot(None)
    ).all()
    
    results = []
    
    for transcript in transcripts:
        # Obtener embedding de la transcripción (con cache)
        transcript_embedding = get_or_create_embedding(db, transcript)
        
        if transcript_embedding is None:
            continue
        
        # Calcular similitud
        similarity = cosine_similarity(query_vector.tolist(), transcript_embedding.tolist())
        
        if similarity >= threshold:
            # Extraer snippet relevante
            content = transcript.cleaned_content or transcript.content or ""
            snippet = get_snippet(content, "")
            
            results.append((transcript, similarity, snippet))
    
    # Ordenar por similitud descendente
    results.sort(key=lambda x: x[1], reverse=True)
    
    # Limitar resultados
    return results[:limit]


