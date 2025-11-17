#!/bin/bash
# Script para iniciar todo el sistema (Backend + Frontend)
# Ejecuta backend y frontend en procesos separados

set -e

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "=========================================="
echo "Iniciando Sistema de Análisis Entel"
echo "=========================================="
echo ""

# Verificar que estamos en el directorio correcto
if [ ! -f "backend/main.py" ]; then
    echo -e "${RED}Error: Debes ejecutar este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Activar entorno virtual
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ Entorno virtual no encontrado. Ejecuta ./install.sh primero${NC}"
    exit 1
fi

source venv/bin/activate
echo -e "${GREEN}✓ Entorno virtual activado${NC}"

# Inicializar base de datos si no existe
if [ ! -f "transcripts.db" ]; then
    echo ""
    echo "Inicializando base de datos..."
    python -m backend.init_db
    echo -e "${GREEN}✓ Base de datos inicializada${NC}"
else
    echo -e "${GREEN}✓ Base de datos ya existe${NC}"
fi

# Verificar que hay transcripciones
TRANSCRIPT_COUNT=$(python -c "from backend.services.transcript_loader_service import count_transcripts; print(count_transcripts())" 2>/dev/null || echo "0")
echo -e "${GREEN}✓ Transcripciones disponibles: ${TRANSCRIPT_COUNT}${NC}"

# Verificar transcripciones con embeddings (solo las subidas por usuario)
EMBEDDING_COUNT=$(python -c "from backend.database import SessionLocal, Transcript; db = SessionLocal(); count = db.query(Transcript).filter(Transcript.embedding.isnot(None)).count(); db.close(); print(count)" 2>/dev/null || echo "0")
echo -e "${GREEN}✓ Transcripciones procesadas (con embeddings): ${EMBEDDING_COUNT}${NC}"

if [ "$EMBEDDING_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}💡 TIP: Sube transcripciones desde el frontend para habilitar búsquedas${NC}"
    echo "   Los embeddings se generan automáticamente al subir archivos"
fi

# Verificar API key
if [ ! -f "bryant.env" ] || [ ! -s "bryant.env" ]; then
    echo -e "${YELLOW}⚠ Advertencia: bryant.env no encontrado o vacío${NC}"
    echo "   El sistema funcionará pero necesitarás configurar la API key de OpenAI"
fi

echo ""
echo "=========================================="
echo "Iniciando servicios..."
echo "=========================================="
echo ""

# Crear directorio para logs si no existe
mkdir -p logs

# Función para limpiar procesos al salir
cleanup() {
    echo ""
    echo "Deteniendo servicios..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Servicios detenidos"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Iniciar Backend
echo -e "${GREEN}Iniciando Backend en http://localhost:8000${NC}"
uvicorn backend.main:app --reload --port 8000 > logs/backend.log 2>&1 &
BACKEND_PID=$!

# Esperar un poco para que el backend inicie
sleep 5

# Verificar que el backend está corriendo
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Error: El backend no pudo iniciarse${NC}"
    echo "Revisa logs/backend.log para más detalles"
    echo ""
    echo "Últimas líneas del log:"
    tail -20 logs/backend.log
    exit 1
fi

# Verificar que el backend responde
sleep 2
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend respondiendo correctamente${NC}"
else
    echo -e "${YELLOW}⚠ Backend iniciado pero no responde aún (puede tardar unos segundos)${NC}"
fi

echo -e "${GREEN}✓ Backend iniciado (PID: $BACKEND_PID)${NC}"

# Iniciar Frontend
if [ -d "frontend" ]; then
    echo -e "${GREEN}Iniciando Frontend en http://localhost:5173${NC}"
    cd frontend
    
    # Verificar que node_modules existe
    if [ ! -d "node_modules" ]; then
        echo "Instalando dependencias del frontend..."
        npm install
    fi
    
    npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    cd ..
    
    # Esperar un poco
    sleep 2
    
    if ! kill -0 $FRONTEND_PID 2>/dev/null; then
        echo -e "${YELLOW}⚠ El frontend no pudo iniciarse${NC}"
        echo "Revisa logs/frontend.log para más detalles"
    else
        echo -e "${GREEN}✓ Frontend iniciado (PID: $FRONTEND_PID)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Directorio frontend no encontrado, solo iniciando backend${NC}"
    FRONTEND_PID=""
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Sistema iniciado correctamente${NC}"
echo "=========================================="
echo ""
echo "Servicios disponibles:"
echo "  - Backend API:  http://localhost:8000"
echo "  - API Docs:     http://localhost:8000/docs"
echo "  - ReDoc:        http://localhost:8000/redoc"
if [ -n "$FRONTEND_PID" ]; then
    echo "  - Frontend:      http://localhost:5173"
fi
echo ""
echo "Logs:"
echo "  - Backend:  logs/backend.log"
if [ -n "$FRONTEND_PID" ]; then
    echo "  - Frontend: logs/frontend.log"
fi
echo ""
if [ "$EMBEDDING_COUNT" -eq "0" ]; then
    echo -e "${YELLOW}💡 IMPORTANTE:${NC}"
    echo "   - Las búsquedas solo funcionan con transcripciones subidas desde el frontend"
    echo "   - Sube archivos .txt en la pestaña 'Subir Transcripción'"
    echo "   - Los embeddings se generan automáticamente al subir"
    echo ""
fi
echo "Presiona Ctrl+C para detener todos los servicios"
echo ""

# Mantener el script corriendo
wait

