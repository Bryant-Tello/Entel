"""
Servicio para cargar transcripciones desde archivos en tiempo real
Busca en 'sample' (originales) y 'new' (subidas por usuario)
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
import re

from backend.config import settings
from backend.utils.text_cleaner import clean_transcript


def _get_sample_dir() -> Path:
    """Retorna la ruta al directorio de transcripciones originales."""
    return settings.TRANSCRIPTS_DIR


def load_transcript_file(filepath: Path) -> Optional[Dict[str, str]]:
    """
    Carga una transcripción desde un archivo.
    Retorna dict con filename y content.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "filename": filepath.name,
            "content": content
        }
    except Exception as e:
        print(f"Error cargando {filepath}: {e}")
        return None


def list_all_transcripts(include_sample: bool = False) -> List[Dict[str, Any]]:
    """
    Lista todas las transcripciones disponibles.
    Por defecto solo incluye archivos de 'new' (subidos por usuario).
    Si include_sample=True, también incluye 'sample' (originales).
    Incluye un preview del contenido limpio.
    """
    transcripts_info = []
    
    # Buscar en directorio 'new' (subidos por usuario) - SIEMPRE
    upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
    if upload_dir.exists():
        pattern = re.compile(r'.*\.txt')
        for filepath in upload_dir.iterdir():
            if filepath.is_file() and pattern.match(filepath.name):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    cleaned_content = clean_transcript(content)
                    preview = cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content
                    
                    transcripts_info.append({
                        "filename": filepath.name,
                        "preview": preview,
                        "source": "new"
                    })
                except Exception as e:
                    print(f"Error procesando {filepath}: {e}")
    
    # Buscar en directorio 'sample' (originales) - SOLO si se solicita
    if include_sample:
        sample_dir = _get_sample_dir()
        if sample_dir.exists():
            pattern = re.compile(r'.*\.txt')
            for filepath in sample_dir.iterdir():
                if filepath.is_file() and pattern.match(filepath.name):
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        cleaned_content = clean_transcript(content)
                        preview = cleaned_content[:200] + "..." if len(cleaned_content) > 200 else cleaned_content
                        
                        transcripts_info.append({
                            "filename": filepath.name,
                            "preview": preview,
                            "source": "sample"
                        })
                    except Exception as e:
                        print(f"Error procesando {filepath}: {e}")
    
    # Ordenar por nombre de archivo
    transcripts_info.sort(key=lambda x: x["filename"])
    
    return transcripts_info


def get_transcript_from_file(filename: str) -> Optional[Dict[str, str]]:
    """
    Obtiene el contenido completo de una transcripción por su nombre de archivo.
    Busca primero en 'new' (subidos), luego en 'sample' (originales).
    """
    # Buscar primero en 'new' (subidos por usuario)
    upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
    filepath = upload_dir / filename
    if filepath.exists():
        content_data = load_transcript_file(filepath)
        if content_data:
            content_data["cleaned_content"] = clean_transcript(content_data["content"])
        return content_data
    
    # Si no está en 'new', buscar en 'sample' (originales)
    sample_dir = _get_sample_dir()
    filepath = sample_dir / filename
    if filepath.exists():
        content_data = load_transcript_file(filepath)
        if content_data:
            content_data["cleaned_content"] = clean_transcript(content_data["content"])
        return content_data
    
    return None


def get_transcript_content(filename: str) -> Optional[str]:
    """Retorna el contenido original de una transcripción."""
    data = get_transcript_from_file(filename)
    return data["content"] if data else None


def get_transcript_cleaned(filename: str) -> Optional[str]:
    """Retorna el contenido limpio de una transcripción."""
    data = get_transcript_from_file(filename)
    return data["cleaned_content"] if data else None


def count_transcripts(include_sample: bool = False) -> int:
    """
    Cuenta el número total de transcripciones.
    Por defecto solo cuenta archivos de 'new' (subidos por usuario).
    Si include_sample=True, también cuenta 'sample' (originales).
    """
    count = 0
    
    # Contar en 'new' (subidos por usuario) - SIEMPRE
    upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
    if upload_dir.exists():
        pattern = re.compile(r'.*\.txt')
        count += len([f for f in upload_dir.iterdir() if f.is_file() and pattern.match(f.name)])
    
    # Contar en 'sample' (originales) - SOLO si se solicita
    if include_sample:
        sample_dir = _get_sample_dir()
        if sample_dir.exists():
            pattern = re.compile(r'.*\.txt')
            count += len([f for f in sample_dir.iterdir() if f.is_file() and pattern.match(f.name)])
    
    return count


def save_transcript_file(filename: str, content: str) -> Path:
    """Guarda una nueva transcripción en el directorio 'new'."""
    upload_dir = settings.UPLOADED_TRANSCRIPTS_DIR
    upload_dir.mkdir(parents=True, exist_ok=True)
    filepath = upload_dir / filename
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    return filepath
