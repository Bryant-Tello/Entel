"""
Endpoint para eliminar transcripciones
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pathlib import Path
import logging
import os

from backend.database import get_db, Transcript
from backend.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/delete", tags=["delete"])


@router.delete("/transcript/{filename:path}")
def delete_transcript(
    filename: str,
    db: Session = Depends(get_db)
):
    """
    Elimina una transcripción subida por el usuario
    Elimina tanto el archivo como el registro en la base de datos
    """
    try:
        # Buscar en BD
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        if not db_transcript:
            raise HTTPException(
                status_code=404,
                detail=f"Transcripción {filename} no encontrada"
            )
        
        # Eliminar archivo del directorio 'new'
        upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
        filepath = upload_dir / filename
        
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info(f"Archivo eliminado: {filepath}")
            except Exception as e:
                logger.error(f"Error eliminando archivo {filepath}: {e}")
                # Continuar aunque falle la eliminación del archivo
        
        # Eliminar de BD
        db.delete(db_transcript)
        db.commit()
        
        logger.info(f"Transcripción eliminada: {filename}")
        
        return {
            "message": f"Transcripción {filename} eliminada exitosamente",
            "filename": filename
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando transcripción {filename}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar transcripción: {str(e)}"
        )


@router.delete("/all")
def delete_all_transcripts(
    db: Session = Depends(get_db)
):
    """
    Elimina TODAS las transcripciones subidas por el usuario
    Elimina archivos del directorio 'new' y registros de la BD
    """
    try:
        # Buscar todas las transcripciones en BD que están en 'new'
        upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
        all_transcripts = db.query(Transcript).all()
        
        deleted_count = 0
        deleted_files = []
        
        for db_transcript in all_transcripts:
            # Eliminar archivo si existe en 'new'
            filepath = upload_dir / db_transcript.filename
            if filepath.exists():
                try:
                    filepath.unlink()
                    deleted_files.append(db_transcript.filename)
                    logger.info(f"Archivo eliminado: {filepath}")
                except Exception as e:
                    logger.error(f"Error eliminando archivo {filepath}: {e}")
            
            # Eliminar de BD
            db.delete(db_transcript)
            deleted_count += 1
        
        db.commit()
        
        logger.info(f"Eliminadas {deleted_count} transcripciones")
        
        return {
            "message": f"Se eliminaron {deleted_count} transcripción(es) exitosamente",
            "deleted_count": deleted_count,
            "deleted_files": deleted_files
        }
    
    except Exception as e:
        logger.error(f"Error eliminando todas las transcripciones: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar todas las transcripciones: {str(e)}"
        )

