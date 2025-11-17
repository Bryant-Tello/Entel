-- Script SQL para configurar PostgreSQL con pgvector
-- Ejecutar como: psql -U postgres -d entel_transcripts -f setup_postgres.sql

-- Crear base de datos (ejecutar desde postgres)
-- CREATE DATABASE entel_transcripts;

-- Habilitar extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Verificar instalación
SELECT * FROM pg_extension WHERE extname = 'vector';

