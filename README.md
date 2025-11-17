# Sistema de Análisis Semántico de Transcripciones - Entel GenAI

Sistema completo para análisis semántico de transcripciones de llamadas de atención al cliente, con capacidades de búsqueda, clasificación automática y extracción de temas principales.

## Tabla de Contenidos

- [Requisitos](#requisitos)
- [Instalación](#instalación)
- [Configuración](#configuración)
- [Ejecución](#ejecución)
- [Gestión de Presupuesto OpenAI](#gestión-de-presupuesto-openai)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Frontend](#frontend)
  - [Guía de Uso de la Interfaz](#guía-de-uso-de-la-interfaz)
  - [Flujo de Trabajo Típico](#flujo-de-trabajo-típico)

## Requisitos

### Backend
- Python 3.11+ (probado con Python 3.13)
- pip (gestor de paquetes de Python)
- Base de datos: SQLite (por defecto) o PostgreSQL con extensión pgvector (opcional)

### Frontend
- Node.js 18+ y npm
- Navegador web moderno

### API Externa
- Cuenta de OpenAI con API key válida

## Instalación

### Opción 1: Instalación Automática (Recomendado)

Usa el script de instalación automática:

```bash
chmod +x install.sh
./install.sh
```

Este script:
- Verifica Python 3.11+
- Crea y activa entorno virtual
- Instala todas las dependencias
- Inicializa la base de datos
- Verifica la instalación

### Opción 2: Instalación Manual

### 1. Clonar o descargar el proyecto

```bash
cd /ruta/al/proyecto
```

### 2. Configurar Backend

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar entorno virtual
# En macOS/Linux:
source venv/bin/activate
# En Windows:
# venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Frontend

```bash
cd frontend
npm install
```

### 4. Configurar API Key de OpenAI

Copiar el archivo de ejemplo y agregar tu API key:

```bash
cp bryant.env.example bryant.env
```

Luego editar `bryant.env` y agregar tu API key de OpenAI:

```
sk-tu-api-key-aqui
```

**Nota**: El archivo `bryant.env` está en `.gitignore` y no se subirá a GitHub por seguridad. El archivo `bryant.env.example` es solo una plantilla.

O configurar variable de entorno:

```bash
export OPENAI_API_KEY="sk-tu-api-key-aqui"
```

## Configuración

### Configuración de Base de Datos

Por defecto, el sistema usa SQLite (no requiere configuración adicional). Para usar PostgreSQL:

1. Instalar PostgreSQL y extensión pgvector
2. Crear base de datos:
```sql
CREATE DATABASE entel_transcripts;
```

3. Configurar variable de entorno:
```bash
export USE_POSTGRES="true"
export DATABASE_URL="postgresql://usuario:password@localhost:5432/entel_transcripts"
```

### Inicializar Base de Datos

```bash
python backend/init_db.py
```

## Ejecución

### Opción 1: Script de inicio automático (recomendado)

```bash
chmod +x start.sh
./start.sh
```

Este script:
- Verifica dependencias
- Inicia backend en `http://localhost:8000`
- Inicia frontend en `http://localhost:5173`
- Muestra logs en tiempo real

### Opción 2: Ejecución manual

**Terminal 1 - Backend:**
```bash
source venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Acceso

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Documentación API**: http://localhost:8000/docs

## Gestión de Presupuesto OpenAI

### Modelos Utilizados y Costos

| Modelo | Uso | Costo |
|--------|-----|-------|
| `text-embedding-3-small` | Generación de embeddings | $0.02 por 1M tokens |
| `gpt-3.5-turbo` | Clasificación y extracción de temas/palabras clave | $0.0015 por 1K tokens input |

### Estrategias de Optimización Implementadas

#### 1. **Cache de Embeddings**
- Los embeddings se generan una sola vez por transcripción
- Se almacenan en base de datos para reutilización
- **Ahorro**: Evita regenerar embeddings en búsquedas repetidas

#### 2. **Rate Limiting Inteligente**
- Sistema de rate limiting que respeta límites de OpenAI
- Límites configurados: 1M tokens/minuto, 3,000 requests/minuto
- Espera automática solo cuando es necesario
- **Ahorro**: Evita errores 429 y reintentos costosos

#### 3. **Procesamiento en Batch**
- Embeddings generados en lotes de hasta 100 textos
- Clasificaciones procesadas eficientemente
- **Ahorro**: Reduce overhead de múltiples llamadas

#### 4. **Truncamiento de Texto**
- Textos truncados a 15,000 caracteres para clasificación
- Textos truncados a 32,000 caracteres para embeddings
- **Ahorro**: Reduce tokens innecesarios

#### 5. **Limpieza de Datos**
- Eliminación de timestamps, etiquetas de sistema
- Sanitización de PII (datos personales)
- **Ahorro**: Reduce tokens procesados sin perder información relevante

#### 6. **Clustering sin GPT**
- Extracción de temas usando K-means en embeddings (sin costo)
- Solo usa GPT para clasificación y extracción de tema/palabras clave específicas
- **Ahorro**: Evita procesar cada transcripción con GPT para temas

#### 7. **Tracking de Costos**
- Sistema de logging de uso de API
- Registro en base de datos de cada operación
- Cálculo automático de costos por operación

### Monitoreo de Presupuesto

El sistema registra automáticamente:
- Tokens usados por operación
- Costo en USD por operación
- Modelo utilizado
- Timestamp de cada operación

Consulta los logs en la base de datos:
```sql
SELECT * FROM usage_logs ORDER BY created_at DESC;
```

### Estimación de Costos

**Ejemplo para 100 transcripciones:**
- Embeddings: ~100 transcripciones × 1,000 tokens = 100K tokens = **$0.002**
- Clasificación: ~100 transcripciones × 500 tokens = 50K tokens = **$0.075**
- **Total estimado: ~$0.08 para 100 transcripciones**

**Para 1,000 transcripciones:**
- Embeddings: 1M tokens = **$0.02**
- Clasificación: 500K tokens = **$0.75**
- **Total estimado: ~$0.77 para 1,000 transcripciones**

### Configuración de Presupuesto

El presupuesto límite está configurado en `backend/config.py`:
```python
BUDGET_LIMIT_USD: float = 5.0
```

## Estructura del Proyecto

```
Entel/
├── backend/
│   ├── main.py                 # Aplicación FastAPI principal
│   ├── config.py               # Configuración del sistema
│   ├── database.py             # Modelos y configuración de BD
│   ├── models.py               # Modelos Pydantic para API
│   ├── middleware.py           # Middleware de logging
│   ├── routers/                # Endpoints de la API
│   │   ├── search.py          # Búsqueda semántica
│   │   ├── analysis.py        # Temas y clasificación
│   │   ├── upload.py          # Subida de transcripciones
│   │   ├── delete.py          # Eliminación de transcripciones
│   │   ├── transcripts.py    # Gestión de transcripciones
│   │   └── quality.py         # Análisis de calidad
│   ├── services/               # Lógica de negocio
│   │   ├── langchain_service.py    # Integración con OpenAI
│   │   ├── embedding_service.py    # Gestión de embeddings
│   │   ├── search_service.py        # Búsqueda semántica
│   │   ├── classification_service.py # Clasificación
│   │   ├── topic_service.py         # Extracción de temas
│   │   └── transcript_loader_service.py # Carga de archivos
│   └── utils/                  # Utilidades
│       ├── text_cleaner.py    # Limpieza de texto
│       └── rate_limiter.py    # Control de rate limits
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Componente principal React
│   │   ├── main.jsx           # Punto de entrada
│   │   ├── services/
│   │   │   └── api.js         # Cliente API
│   │   └── index.css          # Estilos
│   └── package.json
├── new/                        # Transcripciones subidas por usuario
├── sample/                     # Transcripciones de ejemplo (opcional)
├── logs/                       # Logs del sistema
├── requirements.txt            # Dependencias Python
├── bryant.env                  # API key de OpenAI
└── start.sh                   # Script de inicio
```

## Frontend

### Tecnologías

- **React 18**: Framework de UI
- **Vite**: Build tool y dev server
- **Axios**: Cliente HTTP para API

### Guía de Uso de la Interfaz

#### Pestaña "Búsqueda"

Esta pestaña contiene dos secciones principales:

**1. Subir Transcripciones**
- **Ubicación**: Parte superior de la pestaña "Búsqueda"
- **Funcionalidad**: 
  - Click en el botón de selección de archivos o arrastra archivos .txt
  - Selección múltiple permitida
  - Lista de archivos seleccionados con opción de eliminar antes de subir
  - Botón "Subir X Transcripción(es)" para enviar todos los archivos
- **Proceso automático al subir**:
  1. El archivo se guarda en el directorio `new/`
  2. Se genera el embedding automáticamente
  3. Se clasifica automáticamente (categoría, tema principal, palabras clave)
  4. Se muestra mensaje de éxito con el estado de cada archivo

**2. Buscar Transcripciones**
- **Ubicación**: Parte inferior de la pestaña "Búsqueda"
- **Funcionalidad**:
  - Campo de búsqueda para escribir palabras clave o frases
  - Búsqueda semántica (entiende sinónimos, ej: "iphone fallado" encuentra "iphone defectuoso")
  - Resultados mostrados como tarjetas con:
    - Nombre del archivo
    - Categoría
    - Snippet del texto relevante
    - Similitud (score)
    - Botones "Ver Completo" y "Ver Limpio"
- **Vista de Transcripción**:
  - Modal que se abre al hacer click en "Ver Completo" o "Ver Limpio"
  - Botones para alternar entre texto original y texto limpio (sin timestamps, PII sanitizado)
  - Botón X para cerrar el modal

#### Pestaña "Temas"

**Visualización de Transcripciones Agrupadas**
- **Organización**: Las transcripciones se agrupan automáticamente por categoría:
  - Problema Técnico
  - Soporte Comercial
  - Solicitud Administrativa
  - Reclamo
  - Otro
- **Tabla por Categoría**:
  - **Columna "Conversación"**: Nombre del archivo
  - **Columna "Tema Principal"**: Tema extraído por GPT (3-5 palabras)
  - **Columna "Palabras Clave"**: Keywords extraídas por GPT (separadas por comas)
  - **Columna "Acciones"**: 
    - Botón "Ver": Abre modal con texto original
    - Botón "Ver Limpio": Abre modal con texto limpio (sin timestamps, PII sanitizado)
    - Botón "Eliminar": Elimina la transcripción (archivo + registro en BD)
- **Paginación**: 
  - 10 transcripciones por página
  - Botones "Anterior" y "Siguiente"
  - Indicador de página actual
- **Eliminación Masiva**:
  - Botón "Eliminar Todas las Conversaciones" en la parte superior
  - Modal de confirmación antes de eliminar
  - Elimina todos los archivos del directorio `new/` y sus registros en BD

### Funcionalidades Principales

- **Subida de Archivos**: Selección múltiple, preview antes de subir, eliminación de la lista antes de enviar
- **Búsqueda Semántica**: Entiende sinónimos y contexto (ej: "problema" encuentra "falla", "error", "incidente")
- **Clasificación Automática**: Al subir un archivo, se clasifica automáticamente en una categoría
- **Extracción de Temas**: Cada transcripción tiene su tema principal y palabras clave extraídos por GPT
- **Gestión de Transcripciones**: Eliminación individual desde la tabla o eliminación masiva con confirmación
- **Vista Dual**: Opción de ver texto original (con timestamps) o texto limpio (sin timestamps, PII sanitizado)

### Flujo de Trabajo Típico

1. **Subir Transcripciones**:
   - Ir a pestaña "Búsqueda"
   - Seleccionar uno o más archivos .txt
   - Revisar la lista y eliminar archivos si es necesario
   - Click en "Subir X Transcripción(es)"
   - Esperar confirmación de éxito

2. **Buscar Información**:
   - En la misma pestaña "Búsqueda", usar el campo de búsqueda
   - Escribir palabras clave o frases (ej: "problema internet", "cambio plan")
   - Ver resultados con snippets
   - Click en "Ver Completo" o "Ver Limpio" para ver la transcripción completa

3. **Revisar Temas**:
   - Ir a pestaña "Temas"
   - Ver transcripciones agrupadas por categoría
   - Navegar entre páginas si hay más de 10 transcripciones
   - Ver detalles de cada transcripción (tema, palabras clave)
   - Eliminar transcripciones individuales o todas si es necesario

### Desarrollo Frontend

```bash
cd frontend
npm run dev      # Modo desarrollo
npm run build    # Build de producción
npm run preview  # Preview del build
```

## Troubleshooting

### Error: "No module named 'pgvector'"
- Solución: Instalar `pip install pgvector` o usar SQLite (por defecto)

### Error: "OPENAI_API_KEY not found"
- Solución: Copiar `bryant.env.example` a `bryant.env` y agregar tu API key de OpenAI

### Error: "Rate limit exceeded"
- Solución: El sistema maneja esto automáticamente con rate limiting. Si persiste, verifica tu plan de OpenAI.

### Frontend no se conecta al backend
- Verificar que backend esté corriendo en `http://localhost:8000`
- Verificar CORS en `backend/main.py`

## Notas Adicionales

- Las transcripciones se almacenan en archivos (directorio `new/`)
- Los embeddings y análisis se almacenan en base de datos
- El sistema soporta hasta 1,000+ transcripciones simultáneas
- Los logs se guardan en `logs/backend.log` y `logs/frontend.log`

