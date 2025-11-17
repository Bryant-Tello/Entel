"""
Configuración del sistema
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Cargar variables de entorno
env_path = Path(__file__).parent.parent / "bryant.env"
if env_path.exists():
    # Leer API key directamente del archivo
    with open(env_path, 'r') as f:
        api_key = f.read().strip()
    os.environ["OPENAI_API_KEY"] = api_key
else:
    # Intentar cargar .env si existe
    load_dotenv()


class Settings(BaseSettings):
    """Configuración de la aplicación"""
    
    # OpenAI
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # Base de datos PostgreSQL
    # Formato: postgresql://usuario:password@host:puerto/database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/entel_transcripts"
    )
    
    # Para desarrollo local, también soporta SQLite como fallback
    # Por defecto usa SQLite (más fácil de configurar)
    USE_POSTGRES: bool = os.getenv("USE_POSTGRES", "false").lower() == "true"
    
    # Directorio de transcripciones originales (solo lectura)
    TRANSCRIPTS_DIR: Path = Path(__file__).parent.parent / "sample"
    
    # Directorio para nuevas transcripciones subidas por usuario
    UPLOADED_TRANSCRIPTS_DIR: Path = Path(__file__).parent.parent / "new"
    
    # Modelos OpenAI
    EMBEDDING_MODEL: str = "text-embedding-3-small"  # Más barato: $0.02/1M tokens
    CHAT_MODEL: str = "gpt-3.5-turbo"  # Para clasificación: $0.0015/1K tokens input
    
    # Configuración de embeddings
    EMBEDDING_DIMENSION: int = 1536  # Dimensión de text-embedding-3-small
    
    # Configuración de búsqueda
    MAX_SEARCH_RESULTS: int = 10
    SIMILARITY_THRESHOLD: float = 0.7
    
    # Configuración de temas
    NUM_TOPICS: int = 10
    MIN_TOPIC_SIZE: int = 3
    
    # Categorías de clasificación
    CATEGORIES: list = [
        "problema_tecnico",
        "soporte_comercial",
        "solicitud_administrativa",
        "consulta_informacion",
        "reclamo",
        "venta",
        "otro"
    ]
    
    # Presupuesto
    BUDGET_LIMIT_USD: float = 5.0
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()

