# Documentación de API

Documentación completa de los endpoints disponibles en el Sistema de Análisis Semántico de Transcripciones.

## Base URL

```
http://localhost:8000
```

## Autenticación

Actualmente no se requiere autenticación. La API key de OpenAI se configura en el servidor.

## Endpoints

### 1. Búsqueda Semántica

#### `POST /api/search`

Realiza búsqueda semántica en transcripciones usando embeddings.

**Request Body:**
```json
{
  "query": "problema con internet",
  "limit": 10,
  "threshold": 0.5
}
```

**Parámetros:**
- `query` (string, requerido): Texto a buscar
- `limit` (int, opcional, default: 10): Número máximo de resultados (1-100)
- `threshold` (float, opcional, default: 0.5): Umbral de similitud (0-1)

**Response:**
```json
{
  "query": "problema con internet",
  "results": [
    {
      "transcript_id": 1,
      "filename": "sample_01.txt",
      "similarity": 0.8523,
      "snippet": "...problema con la conexión de internet...",
      "category": "problema_tecnico"
    }
  ],
  "total": 1
}
```

**Ejemplo con cURL:**
```bash
curl -X POST "http://localhost:8000/api/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "cambio de plan",
    "limit": 5,
    "threshold": 0.5
  }'
```

**Ejemplo con JavaScript:**
```javascript
const response = await fetch('http://localhost:8000/api/search', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    query: 'factura incorrecta',
    limit: 10,
    threshold: 0.5
  })
});
const data = await response.json();
```

---

### 2. Extracción de Temas

#### `GET /api/topics`

Extrae temas principales de las transcripciones usando clustering.

**Query Parameters:**
- `num_topics` (int, opcional, default: 10): Número de temas a extraer (1-50)
- `min_topic_size` (int, opcional, default: 1): Tamaño mínimo de transcripciones por tema

**Response:**
```json
{
  "topics": [
    {
      "topic_id": 0,
      "size": 5,
      "tema_principal": "Problemas de conexión a internet",
      "palabras_clave": ["internet", "conexión", "router", "señal"],
      "transcripciones": [
        {
          "conversacion": "sample_01.txt",
          "clasificacion": "problema_tecnico",
          "tema_principal": "Conexión inestable requiere visita técnica",
          "palabras_clave": ["internet", "señal", "router"]
        }
      ]
    }
  ],
  "total_transcripts": 25,
  "grouped_by_category": {
    "problema_tecnico": [
      {
        "conversacion": "sample_01.txt",
        "tema_principal": "...",
        "palabras_clave": [...]
      }
    ]
  }
}
```

**Ejemplo con cURL:**
```bash
curl "http://localhost:8000/api/topics?num_topics=10&min_topic_size=1"
```

---

### 3. Clasificación de Transcripciones

#### `POST /api/classify`

Clasifica transcripciones en categorías automáticamente.

**Request Body:**
```json
{
  "transcript_ids": [1, 2, 3]
}
```

O clasificar todas las no clasificadas:
```json
{
  "transcript_ids": null
}
```

**Parámetros:**
- `transcript_ids` (array[int] | null, opcional): IDs de transcripciones a clasificar. Si es `null`, clasifica todas las no clasificadas.

**Response:**
```json
{
  "results": [
    {
      "transcript_id": 1,
      "filename": "sample_01.txt",
      "category": "problema_tecnico",
      "confidence": null
    }
  ],
  "total": 1
}
```

**Categorías disponibles:**
- `problema_tecnico`: Problemas con servicios (internet, teléfono, etc.)
- `soporte_comercial`: Consultas y cambios de planes
- `solicitud_administrativa`: Solicitudes de documentos, facturas
- `consulta_informacion`: Consultas generales
- `reclamo`: Reclamos y quejas
- `venta`: Ventas de nuevos servicios
- `otro`: Otras categorías

**Ejemplo con cURL:**
```bash
curl -X POST "http://localhost:8000/api/classify" \
  -H "Content-Type: application/json" \
  -d '{"transcript_ids": [1, 2, 3]}'
```

---

### 4. Subir Transcripción

#### `POST /api/upload/transcript`

Sube un archivo de transcripción (.txt) al sistema.

**Request:**
- Content-Type: `multipart/form-data`
- Campo: `file` (archivo .txt)

**Response:**
```json
{
  "filename": "sample_27.txt",
  "message": "Transcripción subida exitosamente",
  "embedding_generated": true,
  "classification_done": true,
  "category": "soporte_comercial",
  "tema_principal": "Solicitud de cambio de plan móvil",
  "palabras_clave": ["plan", "cambio", "móvil", "gigas"]
}
```

**Ejemplo con cURL:**
```bash
curl -X POST "http://localhost:8000/api/upload/transcript" \
  -F "file=@/ruta/al/archivo.txt"
```

**Ejemplo con JavaScript:**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8000/api/upload/transcript', {
  method: 'POST',
  body: formData
});
const data = await response.json();
```

---

### 5. Obtener Transcripción

#### `GET /api/transcripts/{filename}`

Obtiene una transcripción específica.

**Path Parameters:**
- `filename` (string): Nombre del archivo (ej: `sample_01.txt`)

**Query Parameters:**
- `include_content` (bool, opcional, default: true): Incluir contenido completo

**Response:**
```json
{
  "id": 1,
  "filename": "sample_01.txt",
  "content": "[00:00:00] AGENTE: ...",
  "cleaned_content": "AGENTE: ...",
  "category": "problema_tecnico",
  "topics": null,
  "created_at": "2024-01-15T10:30:00",
  "updated_at": "2024-01-15T10:30:00"
}
```

**Ejemplo con cURL:**
```bash
curl "http://localhost:8000/api/transcripts/sample_01.txt?include_content=true"
```

---

### 6. Listar Transcripciones

#### `GET /api/transcripts`

Lista todas las transcripciones disponibles.

**Query Parameters:**
- `skip` (int, opcional, default: 0): Número de resultados a omitir
- `limit` (int, opcional, default: 100): Número máximo de resultados (1-100)

**Response:**
```json
[
  {
    "id": 1,
    "filename": "sample_01.txt",
    "content": null,
    "cleaned_content": "AGENTE: ...",
    "category": "problema_tecnico",
    "topics": null,
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:30:00"
  }
]
```

---

### 7. Eliminar Transcripción

#### `DELETE /api/delete/transcript/{filename}`

Elimina una transcripción específica (archivo y registro en BD).

**Path Parameters:**
- `filename` (string): Nombre del archivo

**Response:**
```json
{
  "message": "Transcripción sample_01.txt eliminada exitosamente",
  "filename": "sample_01.txt"
}
```

**Ejemplo con cURL:**
```bash
curl -X DELETE "http://localhost:8000/api/delete/transcript/sample_01.txt"
```

---

### 8. Eliminar Todas las Transcripciones

#### `DELETE /api/delete/all`

Elimina todas las transcripciones subidas por el usuario.

**Response:**
```json
{
  "message": "Se eliminaron 25 transcripción(es) exitosamente",
  "deleted_count": 25,
  "deleted_files": ["sample_01.txt", "sample_02.txt", ...]
}
```

**Ejemplo con cURL:**
```bash
curl -X DELETE "http://localhost:8000/api/delete/all"
```

---

## Queries Comunes

### Buscar problemas técnicos
```json
POST /api/search
{
  "query": "problema técnico internet señal router",
  "limit": 20
}
```

### Buscar cambios de plan
```json
POST /api/search
{
  "query": "cambio de plan móvil gigas",
  "limit": 10
}
```

### Buscar reclamos de facturación
```json
POST /api/search
{
  "query": "factura incorrecta cargo adicional",
  "limit": 15
}
```

### Obtener temas de problemas técnicos
```bash
GET /api/topics?num_topics=5&min_topic_size=2
# Luego filtrar por categoría en el frontend
```

## Códigos de Estado HTTP

- `200 OK`: Operación exitosa
- `400 Bad Request`: Parámetros inválidos
- `404 Not Found`: Recurso no encontrado
- `500 Internal Server Error`: Error del servidor

## Errores Comunes

### Error 400: "La consulta de búsqueda no puede estar vacía"
- Solución: Proporcionar un `query` no vacío

### Error 404: "Transcripción no encontrada"
- Solución: Verificar que el archivo existe en el directorio `new/`

### Error 500: "Error interno del servidor"
- Solución: Revisar logs en `logs/backend.log`

## Documentación Interactiva

Accede a la documentación interactiva de Swagger en:
```
http://localhost:8000/docs
```

O ReDoc en:
```
http://localhost:8000/redoc
```

