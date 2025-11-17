"""
Configuración de base de datos SQLAlchemy con PostgreSQL + pgvector
"""
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, Index, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
import numpy as np

from backend.config import settings

# Importar pgvector si está disponible
try:
    from pgvector.sqlalchemy import Vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    PGVECTOR_AVAILABLE = False
    Vector = None

# Crear engine
if settings.USE_POSTGRES and PGVECTOR_AVAILABLE:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,  # Verificar conexiones antes de usarlas
        pool_size=10,
        max_overflow=20
    )
else:
    # Fallback a SQLite para desarrollo
    engine = create_engine(
        "sqlite:///./transcripts.db",
        connect_args={"check_same_thread": False}
    )

# Crear session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


class Transcript(Base):
    """Modelo de transcripción con soporte vectorial"""
    __tablename__ = "transcripts"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, unique=True, index=True)
    content = Column(Text)
    cleaned_content = Column(Text)  # Contenido limpio
    category = Column(String, nullable=True, index=True)  # Categoría clasificada
    tema_principal = Column(Text, nullable=True)  # Tema principal extraído
    palabras_clave = Column(JSON, nullable=True)  # Palabras clave extraídas
    topics = Column(JSON, nullable=True)  # Temas extraídos (legacy)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Embedding vectorial usando pgvector (solo si está disponible)
    if PGVECTOR_AVAILABLE and settings.USE_POSTGRES:
        embedding = Column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)
        
        # Índice para búsqueda vectorial eficiente
        __table_args__ = (
            Index('idx_transcript_embedding', 'embedding', postgresql_using='ivfflat'),
        )
    else:
        # Fallback: almacenar como JSON para SQLite
        embedding = Column(Text, nullable=True)
    
    def get_embedding_array(self):
        """Convierte el embedding a array numpy"""
        if self.embedding is None:
            return None
        
        if isinstance(self.embedding, (list, np.ndarray)):
            return np.array(self.embedding) if not isinstance(self.embedding, np.ndarray) else self.embedding
        
        # Si es string (SQLite fallback)
        if isinstance(self.embedding, str):
            return np.array(json.loads(self.embedding))
        
        return np.array(self.embedding)
    
    def set_embedding(self, embedding_array):
        """Establece el embedding desde un array"""
        if isinstance(embedding_array, list):
            embedding_array = np.array(embedding_array)
        
        if PGVECTOR_AVAILABLE and settings.USE_POSTGRES:
            self.embedding = embedding_array.tolist()
        else:
            # Fallback para SQLite
            self.embedding = json.dumps(embedding_array.tolist())


class UsageLog(Base):
    """Log de uso de OpenAI para tracking de costos"""
    __tablename__ = "usage_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    operation = Column(String, index=True)  # embedding, classification, etc.
    model = Column(String)
    tokens_used = Column(Integer)
    cost_usd = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


def init_db():
    """Inicializar base de datos y extensiones necesarias"""
    global engine, SessionLocal
    
    try:
        # Si usamos PostgreSQL, habilitar extensión pgvector primero
        if settings.USE_POSTGRES and PGVECTOR_AVAILABLE:
            with engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
                conn.commit()
        
        # Crear tablas
        Base.metadata.create_all(bind=engine)
        
        # Crear índice vectorial si usamos PostgreSQL
        if settings.USE_POSTGRES and PGVECTOR_AVAILABLE:
            try:
                with engine.connect() as conn:
                    # Verificar si el índice ya existe
                    result = conn.execute(text("""
                        SELECT COUNT(*) FROM pg_indexes 
                        WHERE indexname = 'idx_transcript_embedding'
                    """))
                    if result.scalar() == 0:
                        conn.execute(text("""
                            CREATE INDEX idx_transcript_embedding 
                            ON transcripts USING ivfflat (embedding vector_cosine_ops)
                            WITH (lists = 100)
                        """))
                        conn.commit()
            except Exception as e:
                print(f"Nota: No se pudo crear índice vectorial (puede que ya exista): {e}")
    except Exception as e:
        # Si falla PostgreSQL, cambiar a SQLite automáticamente
        print(f"⚠ PostgreSQL no disponible, usando SQLite: {e}")
        try:
            engine.dispose()  # Cerrar conexiones anteriores
        except:
            pass
        engine = create_engine(
            "sqlite:///./transcripts.db",
            connect_args={"check_same_thread": False}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency para obtener sesión de DB"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
