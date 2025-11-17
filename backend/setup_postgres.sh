#!/bin/bash
# Script para configurar PostgreSQL con pgvector

echo "Configurando PostgreSQL con pgvector..."

# Crear base de datos si no existe
psql -U postgres -c "CREATE DATABASE entel_transcripts;" 2>/dev/null || echo "Base de datos ya existe"

# Conectar y habilitar extensión pgvector
psql -U postgres -d entel_transcripts -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "✓ PostgreSQL configurado correctamente"
echo "✓ Extensión pgvector habilitada"

