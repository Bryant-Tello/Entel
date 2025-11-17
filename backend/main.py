"""
Aplicación principal FastAPI
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import transcripts, search, analysis, upload, delete
from backend.middleware import LoggingMiddleware

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema de Análisis Semántico de Transcripciones",
    description="API para análisis semántico de transcripciones de llamadas de atención al cliente",
    version="1.0.0"
)

# Configurar CORS para permitir frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Vite y otros
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agregar middleware de logging
app.add_middleware(LoggingMiddleware)

# Incluir routers
app.include_router(transcripts.router)
app.include_router(search.router)
app.include_router(analysis.router)
app.include_router(upload.router)
app.include_router(delete.router)


@app.get("/")
def root():
    """Endpoint raíz"""
    return {
        "message": "Sistema de Análisis Semántico de Transcripciones - Entel GenAI",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

