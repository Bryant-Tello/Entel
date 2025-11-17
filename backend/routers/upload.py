"""
Endpoint para subir nuevas transcripciones
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pathlib import Path
import logging

from backend.database import get_db, Transcript
from backend.config import settings
from backend.utils.text_cleaner import clean_transcript

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/transcript")
async def upload_transcript(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Sube una nueva transcripción desde el frontend
    
    **Objetivo**: Permitir agregar nuevas conversaciones dinámicamente
    
    **Proceso**:
    1. Recibe archivo desde frontend
    2. Guarda en directorio sample/
    3. Crea registro en BD (sin embedding aún)
    4. Embedding se generará automáticamente en la primera búsqueda
    """
    try:
        # Validar que es archivo de texto
        if not file.filename.endswith('.txt'):
            raise HTTPException(
                status_code=400,
                detail="Solo se permiten archivos .txt"
            )
        
        # Leer contenido y asegurar encoding correcto
        content = await file.read()
        if isinstance(content, bytes):
            text_content = content.decode('utf-8')
        else:
            text_content = str(content)
        
        if not text_content.strip():
            raise HTTPException(
                status_code=400,
                detail="El archivo está vacío"
            )
        
        # Generar nombre único si ya existe
        filename = file.filename
        upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
        filepath = upload_dir / filename
        
        counter = 1
        while filepath.exists():
            name_parts = filename.rsplit('.', 1)
            new_filename = f"{name_parts[0]}_{counter}.{name_parts[1]}"
            filepath = upload_dir / new_filename
            filename = new_filename
            counter += 1
        
        # Guardar archivo en directorio 'new'
        upload_dir.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(text_content)
        
        # Limpiar contenido
        cleaned_content = clean_transcript(text_content)
        
        # Crear registro en BD
        # IMPORTANTE: Re-consultar después de cada operación para evitar problemas de sincronización
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        if db_transcript:
            # Actualizar si ya existe - limpiar datos anteriores para re-procesar
            db_transcript.content = ""
            db_transcript.cleaned_content = cleaned_content
            # Limpiar campos de clasificación y embedding para re-procesar
            db_transcript.category = None
            db_transcript.tema_principal = None
            db_transcript.palabras_clave = None
            db_transcript.embedding = None
        else:
            # Crear nuevo
            db_transcript = Transcript(
                filename=filename,
                content="",  # No guardamos contenido completo
                cleaned_content=cleaned_content
            )
            db.add(db_transcript)
        
        # Flush para asegurar que el objeto tenga ID antes de continuar
        db.flush()
        db.commit()
        
        # Re-consultar para asegurar que tenemos el objeto más actualizado
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        if not db_transcript:
            raise HTTPException(status_code=500, detail="Error creando registro en BD")
        
        logger.info(f"Registro creado/actualizado para {filename} (ID: {db_transcript.id})")
        
        # GENERAR EMBEDDING Y CLASIFICAR AUTOMÁTICAMENTE cuando el usuario sube el archivo
        from backend.services.embedding_service import get_or_create_embedding
        from backend.services.langchain_service import classify_text
        
        embedding_generated = False
        classification_done = False
        category = None
        notes = []
        
        # 1. Generar embedding
        try:
            logger.info(f"Generando embedding para transcripción subida: {filename} (ID: {db_transcript.id})")
            # Re-consultar para asegurar que tenemos el objeto más actualizado
            db_transcript = db.query(Transcript).filter(
                Transcript.filename == filename
            ).first()
            
            if not db_transcript:
                raise Exception(f"No se encontró registro para {filename}")
            
            embedding = get_or_create_embedding(db, db_transcript)
            
            if embedding is not None:
                # Re-consultar después de generar embedding para asegurar sincronización
                db.refresh(db_transcript)
                # Verificar que el embedding se guardó correctamente
                db_transcript = db.query(Transcript).filter(
                    Transcript.filename == filename
                ).first()
                
                if db_transcript and db_transcript.embedding is not None:
                    logger.info(f"✓ Embedding generado para {filename} (ID: {db_transcript.id})")
                    embedding_generated = True
                    notes.append("Embedding generado exitosamente")
                else:
                    logger.warning(f"Embedding no se guardó correctamente para {filename}")
                    notes.append("Error: embedding no se guardó correctamente")
            else:
                notes.append("Error generando embedding, se intentará en la próxima búsqueda")
        except Exception as e:
            logger.error(f"Error generando embedding para {filename}: {e}", exc_info=True)
            db.rollback()
            notes.append(f"Error generando embedding: {str(e)}")
        
        # Re-consultar antes de continuar para asegurar sincronización
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        # 2. Clasificar automáticamente (solo si el embedding se generó correctamente)
        if embedding_generated:
            try:
                logger.info(f"Clasificando transcripción subida: {filename} (ID: {db_transcript.id})")
                # Re-consultar para asegurar que tenemos el objeto correcto
                db_transcript = db.query(Transcript).filter(
                    Transcript.filename == filename
                ).first()
                
                if not db_transcript:
                    raise Exception(f"No se encontró registro para {filename} antes de clasificar")
                
                # IMPORTANTE: Obtener el contenido limpio directamente del archivo o de la BD
                # para asegurar que estamos usando el contenido correcto de este archivo específico
                cleaned_content_for_classification = None
                
                # Primero intentar desde la BD
                if db_transcript.cleaned_content:
                    cleaned_content_for_classification = db_transcript.cleaned_content
                    logger.info(f"Usando cleaned_content de BD para {filename} (longitud: {len(cleaned_content_for_classification)})")
                else:
                    # Si no está en BD, leer directamente del archivo y limpiarlo
                    filepath = upload_dir / filename
                    if filepath.exists():
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                        cleaned_content_for_classification = clean_transcript(file_content)
                        logger.info(f"Leyendo y limpiando archivo {filename} directamente (longitud: {len(cleaned_content_for_classification)})")
                    else:
                        # Si no existe el archivo, usar el cleaned_content calculado al inicio
                        cleaned_content_for_classification = cleaned_content
                        logger.warning(f"Archivo {filename} no encontrado, usando cleaned_content calculado al inicio")
                
                if not cleaned_content_for_classification or not cleaned_content_for_classification.strip():
                    logger.error(f"No hay contenido limpio disponible para clasificar {filename}")
                    notes.append("Error: no hay contenido limpio disponible para clasificar")
                else:
                    # Log para verificar que estamos usando el contenido correcto
                    logger.info(f"Contenido a clasificar para {filename} (primeros 200 chars): {cleaned_content_for_classification[:200]}...")
                    
                    # Usar el contenido limpio (sin timestamps, con PII sanitizado)
                    classification = classify_text(cleaned_content_for_classification, db)
                
                    if classification and classification.get("category"):
                        # Re-consultar nuevamente antes de actualizar para evitar problemas de sincronización
                        # Usar el ID del registro para asegurar que obtenemos el correcto
                        transcript_id = db_transcript.id
                        db_transcript = db.query(Transcript).filter(
                            Transcript.id == transcript_id,
                            Transcript.filename == filename
                        ).first()
                        
                        if not db_transcript:
                            raise Exception(f"No se encontró registro para {filename} (ID: {transcript_id}) al actualizar clasificación")
                        
                        # Verificar que el ID y filename coinciden
                        if db_transcript.id != transcript_id or db_transcript.filename != filename:
                            raise Exception(f"ERROR: Registro incorrecto. Esperado: {filename} (ID: {transcript_id}), Obtenido: {db_transcript.filename} (ID: {db_transcript.id})")
                        
                        category = classification["category"]
                        tema_principal = classification.get("tema_principal", "")
                        palabras_clave = classification.get("palabras_clave", [])
                        
                        logger.info(f"Guardando clasificación para {filename} (ID: {db_transcript.id}):")
                        logger.info(f"  - Categoría: {category}")
                        logger.info(f"  - Tema: {tema_principal[:50] if tema_principal else 'N/A'}")
                        logger.info(f"  - Palabras clave: {palabras_clave[:3] if palabras_clave else 'N/A'}")
                        
                        # Actualizar campos
                        db_transcript.category = category
                        db_transcript.tema_principal = tema_principal
                        db_transcript.palabras_clave = palabras_clave
                        
                        # Flush y commit
                        db.flush()
                        db.commit()
                        
                        # Re-consultar usando ID y filename para verificar que se guardó correctamente
                        db_transcript = db.query(Transcript).filter(
                            Transcript.id == transcript_id,
                            Transcript.filename == filename
                        ).first()
                        
                        if db_transcript:
                            # Verificar que los datos guardados son correctos
                            if db_transcript.category == category and db_transcript.filename == filename and db_transcript.id == transcript_id:
                                logger.info(f"✓ Transcripción {filename} (ID: {db_transcript.id}) clasificada correctamente:")
                                logger.info(f"  - Categoría: {db_transcript.category}")
                                logger.info(f"  - Tema: {db_transcript.tema_principal[:50] if db_transcript.tema_principal else 'N/A'}")
                                logger.info(f"  - Palabras clave: {db_transcript.palabras_clave[:3] if db_transcript.palabras_clave else 'N/A'}")
                                notes.append(f"Clasificada como: {category}")
                                classification_done = True
                            else:
                                logger.error(f"ERROR: Datos no coinciden para {filename} (ID: {transcript_id})")
                                logger.error(f"  - Esperado categoría: {category}, Obtenido: {db_transcript.category}")
                                logger.error(f"  - Esperado filename: {filename}, Obtenido: {db_transcript.filename}")
                                logger.error(f"  - Esperado ID: {transcript_id}, Obtenido: {db_transcript.id}")
                                notes.append("Error: datos de clasificación no se guardaron correctamente")
                        else:
                            logger.error(f"ERROR: No se pudo verificar registro para {filename} (ID: {transcript_id}) después de clasificar")
                            notes.append("Error: no se pudo verificar clasificación")
                    else:
                        notes.append("Clasificación no pudo determinar categoría")
            except Exception as e:
                logger.error(f"Error clasificando transcripción {filename}: {e}", exc_info=True)
                db.rollback()
                notes.append(f"Error en clasificación: {str(e)}")
        
        # Re-consultar una última vez antes de retornar para asegurar datos correctos
        db_transcript = db.query(Transcript).filter(
            Transcript.filename == filename
        ).first()
        
        if not db_transcript:
            raise HTTPException(status_code=500, detail=f"Error: No se encontró registro para {filename} al finalizar")
        
        # Obtener valores finales directamente de la BD para asegurar que son correctos
        final_category = db_transcript.category
        final_tema = db_transcript.tema_principal
        final_keywords = db_transcript.palabras_clave
        
        logger.info(f"Transcripción subida: {filename} (ID: {db_transcript.id})")
        logger.info(f"  - Categoría final: {final_category}")
        logger.info(f"  - Tema final: {final_tema[:50] if final_tema else 'N/A'}")
        logger.info(f"  - Palabras clave finales: {final_keywords[:3] if final_keywords else 'N/A'}")
        
        return {
            "message": "Transcripción subida exitosamente",
            "filename": filename,
            "id": db_transcript.id,
            "embedding_generated": embedding_generated,
            "classification_done": classification_done,
            "category": final_category,
            "tema_principal": final_tema,
            "palabras_clave": final_keywords,
            "notes": " | ".join(notes) if notes else "Procesamiento completado"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error subiendo transcripción: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al subir transcripción: {str(e)}"
        )

