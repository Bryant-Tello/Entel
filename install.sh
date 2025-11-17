#!/bin/bash
# Script de instalación automática para el proyecto Entel
# Ejecuta todos los pasos necesarios para configurar el proyecto

set -e  # Salir si hay algún error

echo "=========================================="
echo "Instalación del Sistema de Análisis"
echo "=========================================="
echo ""

# Colores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Paso 1: Verificar Python
echo "Paso 1: Verificando Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 no está instalado. Por favor instálalo primero."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
print_step "Python $PYTHON_VERSION encontrado"

# Paso 2: Crear entorno virtual
echo ""
echo "Paso 2: Creando entorno virtual..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_step "Entorno virtual creado"
else
    print_warning "Entorno virtual ya existe, omitiendo creación"
fi

# Paso 3: Activar entorno virtual
echo ""
echo "Paso 3: Activando entorno virtual..."
source venv/bin/activate
print_step "Entorno virtual activado"

# Paso 4: Actualizar pip, setuptools y wheel
echo ""
echo "Paso 4: Actualizando pip, setuptools y wheel..."
pip install --upgrade pip setuptools wheel --quiet
print_step "Herramientas base actualizadas"

# Paso 5: Instalar psycopg2-binary primero (si hay problemas)
echo ""
echo "Paso 5: Instalando psycopg2-binary..."
if pip install psycopg2-binary --quiet 2>/dev/null; then
    print_step "psycopg2-binary instalado"
else
    print_warning "psycopg2-binary falló, continuando sin él (se usará SQLite)"
fi

# Paso 6: Instalar dependencias
echo ""
echo "Paso 6: Instalando dependencias desde requirements.txt..."
if pip install -r requirements.txt --quiet; then
    print_step "Todas las dependencias instaladas"
else
    print_error "Error instalando dependencias"
    echo "Intentando instalar numpy primero..."
    pip install numpy>=1.26.0 --quiet
    pip install -r requirements.txt --quiet
    print_step "Dependencias instaladas (con workaround)"
fi

# Paso 7: Verificar instalación
echo ""
echo "Paso 7: Verificando instalación..."
if python -c "import fastapi, langchain, openai, numpy, sqlalchemy" 2>/dev/null; then
    print_step "Todas las dependencias verificadas correctamente"
else
    print_error "Algunas dependencias no se importan correctamente"
    exit 1
fi

# Paso 8: Inicializar base de datos
echo ""
echo "Paso 8: Inicializando base de datos..."
if python -m backend.init_db 2>/dev/null; then
    print_step "Base de datos inicializada"
else
    print_warning "Error inicializando base de datos (puede que ya esté inicializada)"
fi

# Paso 9: Verificar API key
echo ""
echo "Paso 9: Verificando API key de OpenAI..."
if [ -f "bryant.env" ]; then
    if [ -s "bryant.env" ]; then
        print_step "API key encontrada en bryant.env"
    else
        print_warning "bryant.env existe pero está vacío"
    fi
else
    print_warning "bryant.env no encontrado - necesitarás configurarlo"
fi

echo ""
echo "=========================================="
echo -e "${GREEN}✓ Instalación completada${NC}"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. Configura tu API key de OpenAI en el archivo bryant.env"
echo "2. Activa el entorno virtual: source venv/bin/activate"
echo "3. Ejecuta el backend: cd backend && uvicorn main:app --reload"
echo "4. En otra terminal, ejecuta el frontend: cd frontend && npm install && npm run dev"
echo ""
echo "Documentación:"
echo "- README.md: Guía principal y uso de la interfaz"
echo "- API_DOCUMENTATION.md: Documentación completa de la API"
echo "- INFORME_TECNICO.md: Informe técnico del proyecto"
echo ""

