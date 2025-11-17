"""
Servicio LangChain para operaciones con OpenAI
Optimizado para costos y escalabilidad
Incluye rate limiting y manejo de errores 429
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import time
import logging
import re
try:
    from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
except ImportError:
    # Fallback para versiones antiguas
    from langchain.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
try:
    from langchain_community.callbacks import get_openai_callback
except ImportError:
    try:
        from langchain.callbacks import get_openai_callback
    except ImportError:
        try:
            from langchain_openai import get_openai_callback
        except ImportError:
            # Si no está disponible, crear una versión simplificada
            class MockCallback:
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    pass
                @property
                def total_tokens(self):
                    return 0
                @property
                def prompt_tokens(self):
                    return 0
                @property
                def completion_tokens(self):
                    return 0
            get_openai_callback = lambda: MockCallback()

from backend.config import settings
from backend.database import UsageLog

logger = logging.getLogger(__name__)

# Inicializar embeddings con LangChain
embeddings = OpenAIEmbeddings(
    model=settings.EMBEDDING_MODEL,
    openai_api_key=settings.OPENAI_API_KEY
)

# Inicializar chat model con temperatura más alta para variabilidad
# NO usar JSON mode porque puede causar respuestas genéricas
# En su lugar, usamos un prompt estricto que fuerza JSON válido
chat_model = ChatOpenAI(
    model=settings.CHAT_MODEL,
    temperature=0.7,  # Mayor temperatura para más variabilidad y análisis único por transcripción
    openai_api_key=settings.OPENAI_API_KEY
)


def log_usage(db: Session, operation: str, model: str, tokens: int, cost: float):
    """Registra el uso de OpenAI para tracking de costos"""
    log = UsageLog(
        operation=operation,
        model=model,
        tokens_used=tokens,
        cost_usd=cost
    )
    db.add(log)
    db.commit()


def get_embedding(text: str, db: Session, max_retries: int = 3) -> List[float]:
    """
    Obtiene embedding para un texto usando LangChain con rate limiting y retry
    Costo: ~$0.02 por 1M tokens
    
    Maneja automáticamente:
    - Rate limits (429 errors)
    - Retry con backoff exponencial
    - Límites de tokens por segundo/minuto
    
    OPTIMIZACIÓN: No espera rate limiting si no es necesario (límites más altos)
    """
    from backend.utils.rate_limiter import get_rate_limiter
    
    # Truncar texto si es muy largo
    text = text[:32000]
    
    # Estimar tokens (aproximado: 1 token = 4 caracteres)
    estimated_tokens = max(100, len(text) // 4)
    
    # Rate limiting (solo si realmente es necesario)
    rate_limiter = get_rate_limiter()
    
    for attempt in range(max_retries):
        try:
            # Esperar capacidad (sincrónico) - pero con timeout corto
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Si hay loop corriendo, usar run_in_executor con timeout corto
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(
                            asyncio.run, 
                            rate_limiter.wait_for_capacity(estimated_tokens)
                        )
                        future.result(timeout=10)  # Timeout de 10s máximo
                else:
                    loop.run_until_complete(rate_limiter.wait_for_capacity(estimated_tokens))
            except RuntimeError:
                asyncio.run(rate_limiter.wait_for_capacity(estimated_tokens))
            except concurrent.futures.TimeoutError:
                logger.warning("Timeout en rate limiter, continuando de todas formas")
            
            # Generar embedding
            with get_openai_callback() as cb:
                embedding = embeddings.embed_query(text)
                tokens_used = cb.total_tokens
                cost = (tokens_used / 1_000_000) * 0.02
                log_usage(db, "embedding", settings.EMBEDDING_MODEL, tokens_used, cost)
                rate_limiter.record_usage(tokens_used)
                return embedding
                
        except Exception as e:
            error_msg = str(e).lower()
            if ("rate limit" in error_msg or "429" in error_msg) and attempt < max_retries - 1:
                # Rate limit: esperar con backoff exponencial (reducido)
                wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s (reducido de 60s)
                logger.warning(f"Rate limit alcanzado (intento {attempt + 1}/{max_retries}), esperando {wait_time}s...")
                time.sleep(wait_time)
                continue
            else:
                # Otro error o último intento
                logger.error(f"Error obteniendo embedding: {e}")
                raise
    
    raise Exception("No se pudo generar embedding después de múltiples intentos")


def get_embeddings_batch(texts: List[str], db: Session, max_retries: int = 3) -> List[List[float]]:
    """
    Obtiene embeddings para múltiples textos en batch usando LangChain
    Más eficiente que llamadas individuales
    Incluye rate limiting, procesamiento en chunks y retry automático
    
    Optimizado para manejar 1000+ documentos:
    - Procesa en chunks de 100 (límite de OpenAI)
    - Rate limiting automático
    - Retry con backoff exponencial
    """
    from backend.utils.rate_limiter import get_rate_limiter
    
    # Truncar textos largos
    texts = [text[:32000] for text in texts]
    
    # Procesar en chunks (máximo 100 textos por batch de OpenAI)
    BATCH_SIZE = 100
    all_embeddings = []
    rate_limiter = get_rate_limiter()
    
    for i in range(0, len(texts), BATCH_SIZE):
        chunk = texts[i:i + BATCH_SIZE]
        chunk_processed = False
        
        # Estimar tokens del chunk
        estimated_tokens = sum(max(100, len(text) // 4) for text in chunk)
        
        for attempt in range(max_retries):
            try:
                # Rate limiting antes de cada chunk
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                rate_limiter.wait_for_capacity(estimated_tokens)
                            )
                            future.result(timeout=10)  # Timeout de 10s máximo
                    else:
                        loop.run_until_complete(rate_limiter.wait_for_capacity(estimated_tokens))
                except RuntimeError:
                    asyncio.run(rate_limiter.wait_for_capacity(estimated_tokens))
                except concurrent.futures.TimeoutError:
                    logger.warning("Timeout en rate limiter para batch, continuando de todas formas")
                
                # Procesar chunk
                with get_openai_callback() as cb:
                    chunk_embeddings = embeddings.embed_documents(chunk)
                    tokens_used = cb.total_tokens
                    cost = (tokens_used / 1_000_000) * 0.02
                    log_usage(db, "embedding_batch", settings.EMBEDDING_MODEL, tokens_used, cost)
                    rate_limiter.record_usage(tokens_used)
                    all_embeddings.extend(chunk_embeddings)
                    chunk_processed = True
                    break
                    
            except Exception as e:
                error_msg = str(e).lower()
                if ("rate limit" in error_msg or "429" in error_msg) and attempt < max_retries - 1:
                    # Rate limit: esperar con backoff exponencial (reducido)
                    wait_time = (2 ** attempt) * 2  # 2s, 4s, 8s (reducido de 60s)
                    logger.warning(f"Rate limit en chunk {i//BATCH_SIZE + 1} (intento {attempt + 1}/{max_retries}), esperando {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Error procesando chunk {i//BATCH_SIZE + 1}: {e}")
                    if attempt == max_retries - 1:
                        # Último intento falló: usar embeddings vacíos para este chunk
                        logger.error(f"Chunk {i//BATCH_SIZE + 1} falló después de {max_retries} intentos")
                        all_embeddings.extend([None] * len(chunk))
                    raise
        
        if not chunk_processed:
            # Si no se procesó, agregar placeholders
            all_embeddings.extend([None] * len(chunk))
    
    return all_embeddings


def classify_conversation(cleaned_text: str, db: Session) -> Dict[str, Any]:
    """
    Paso 1: Solo clasifica la conversación en una categoría general.
    """
    import json
    
    if not cleaned_text or not cleaned_text.strip():
        return {"clasificacion_general": "otro", "category": "otro"}
    
    if isinstance(cleaned_text, bytes):
        cleaned_text = cleaned_text.decode('utf-8')
    
    text_to_analyze = cleaned_text[:15000] if len(cleaned_text) > 15000 else cleaned_text
    
    system_prompt = """Eres un asistente que clasifica transcripciones de llamadas de un call center de telecomunicaciones.

Clasifica el MOTIVO PRINCIPAL de la llamada en una de estas categorías (usa EXACTAMENTE estas cadenas):

- "reclamo"
- "problema_tecnico"
- "soporte_comercial"
- "solicitud_administrativa"
- "otro"

Motivo principal = lo que el CLIENTE llama a resolver (no la validación de datos).

Reglas:
- "reclamo": quejas por cobros, mala atención, problemas no resueltos.
- "problema_tecnico": fallas de servicio (internet, señal, router, etc.).
- "soporte_comercial": planes, promociones, cambio de plan, más gigas, contratar o dar de baja servicios.
- "solicitud_administrativa": bloqueo de número, cambio de titular, actualización de datos, documentos.
- "otro": solo si no encaja en ninguna de las anteriores.

Responde SOLO con JSON:
{
  "clasificacion_general": ""
}

Lee TODO el texto completo. Identifica el MOTIVO PRINCIPAL que el CLIENTE menciona."""

    # Construir el mensaje humano con el texto directamente
    human_message_content = f"Transcripción de la llamada:\n\n{text_to_analyze}"
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message_content)
    ])
    
    chain = prompt | chat_model
    
    with get_openai_callback() as cb:
        response = chain.invoke({})
        content = response.content.strip()
        
        # Log la respuesta cruda antes de limpiar
        logger.debug(f"Respuesta cruda del modelo (clasificación): {content[:1000]}")
        
        # Limpiar posibles ```json
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        # Log la respuesta completa para debugging
        logger.debug(f"Respuesta completa del modelo (clasificación): {content}")
        
        try:
            result = json.loads(content)
        except Exception as e:
            logger.error(f"Error parseando JSON de clasificación: {e}")
            logger.error(f"Contenido recibido (primeros 500 chars): {content[:500]}")
            logger.error(f"Contenido completo recibido: {content}")
            result = {"clasificacion_general": None}
        
        clasificacion = result.get("clasificacion_general")
        
        # Log la clasificación recibida
        if clasificacion:
            logger.info(f"Clasificación recibida del modelo: '{clasificacion}'")
        else:
            logger.error(f"Clasificación vacía o None recibida del modelo. Contenido completo: {content}")
            logger.error(f"Resultado parseado: {result}")
        
        # Validar que la clasificación sea una de las permitidas
        categorias_validas = ["problema_tecnico", "reclamo", "soporte_comercial", "solicitud_administrativa", "otro"]
        if not clasificacion:
            logger.error(f"ERROR: El modelo no devolvió clasificación. No se usará 'otro' por defecto. Contenido: {content[:1000]}")
            clasificacion = None
        elif clasificacion not in categorias_validas:
            logger.error(f"ERROR: Clasificación inválida recibida: '{clasificacion}'. No se usará 'otro' por defecto. Contenido: {content[:1000]}")
            clasificacion = None
        
        if not clasificacion:
            # Si no hay clasificación válida, retornar error en lugar de "otro"
            return {
                "clasificacion_general": None,
                "category": None,
                "error": "El modelo no devolvió una clasificación válida"
            }
        
        tokens_used = cb.total_tokens
        cost = (tokens_used / 1000) * 0.0015
        log_usage(db, "classification_only", settings.CHAT_MODEL, tokens_used, cost)
        
        logger.info(f"Categoría clasificada: {clasificacion}")
        
        return {
            "clasificacion_general": clasificacion,
            "category": clasificacion,
        }


def extract_theme_and_keywords(cleaned_text: str, clasificacion_general: str, db: Session) -> Dict[str, Any]:
    """
    Paso 2: usando el texto limpio + la clasificación, extrae:
    - tema_principal
    - palabras_clave
    """
    import json
    
    if not cleaned_text or not cleaned_text.strip():
        return {"tema_principal": "", "palabras_clave": []}
    
    if isinstance(cleaned_text, bytes):
        cleaned_text = cleaned_text.decode('utf-8')
    
    text_to_analyze = cleaned_text[:15000] if len(cleaned_text) > 15000 else cleaned_text
    
    system_prompt = """Eres un asistente que analiza transcripciones de llamadas de telecomunicaciones.

Analiza la transcripción completa y extrae el tema principal y palabras clave.

La llamada fue clasificada como: {categoria}.

Responde SOLO con JSON:
{
  "tema_principal": "",
  "palabras_clave": []
}

Instrucciones:
- "tema_principal": Una frase corta de 3 a 5 palabras máximo que resuma el motivo principal que el CLIENTE menciona. Debe ser específico y basado SOLO en lo que dice el texto. NO incluyas tags como <PERSON>, <LOCATION>, <NUM>, etc. Solo texto normal.
- "palabras_clave": Entre 3 y 8 palabras o frases cortas (1-3 palabras) en minúsculas que aparezcan LITERALMENTE en el texto y sean relevantes al motivo de la llamada.

REGLAS CRÍTICAS:
- Lee TODO el texto completo antes de responder
- El tema principal debe reflejar el problema o motivo REAL que el CLIENTE menciona
- El tema principal debe tener entre 3 y 5 palabras máximo
- El tema principal NO debe contener tags como <PERSON>, <LOCATION>, <NUM>, <DATE>, etc. Solo texto normal sin símbolos < >
- Las palabras clave DEBEN aparecer LITERALMENTE en el texto (busca palabras exactas que veas en el texto)
- NO inventes palabras que no estén en el texto
- NO uses nombres propios, números, correos, teléfonos, direcciones
- NO uses artículos, preposiciones, pronombres, saludos genéricos
- NO uses tags como <PERSON>, <LOCATION>, <NUM>, etc. en el tema principal ni en palabras clave
- Extrae SOLO palabras que realmente aparezcan en el texto y tengan significado contextual relacionado con el motivo"""

    # Construir el mensaje humano con el texto y categoría directamente
    human_message_content = f"Transcripción de la llamada:\n\n{text_to_analyze}\n\nLa llamada fue clasificada como: {clasificacion_general}."
    
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_message_content)
    ])
    
    chain = prompt | chat_model
    
    with get_openai_callback() as cb:
        response = chain.invoke({})
        content = response.content.strip()
        
        # Log la respuesta cruda antes de limpiar
        logger.debug(f"Respuesta cruda del modelo (extracción): {content[:1000]}")
        
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        
        try:
            result = json.loads(content)
        except Exception as e:
            logger.error(f"Error parseando JSON de extracción: {e}")
            logger.error(f"Contenido recibido (primeros 500 chars): {content[:500]}")
            result = {"tema_principal": "", "palabras_clave": []}
        
        tema_principal = (result.get("tema_principal") or "").strip()
        palabras_clave = result.get("palabras_clave") or []
        
        # Limpiar tema principal: eliminar tags < > y validar longitud
        if tema_principal:
            # Eliminar cualquier contenido entre < >
            tema_principal = re.sub(r'<[^>]+>', '', tema_principal).strip()
            # Validar que tenga entre 3 y 5 palabras
            tema_words = tema_principal.split()
            if len(tema_words) > 5:
                # Truncar a 5 palabras
                tema_principal = ' '.join(tema_words[:5])
                logger.warning(f"Tema principal truncado a 5 palabras: {tema_principal}")
            elif len(tema_words) < 3 and len(tema_words) > 0:
                logger.warning(f"Tema principal tiene menos de 3 palabras: {tema_principal}")
        
        # Limpiar palabras clave: eliminar tags < >
        palabras_clave_limpias = []
        for kw in palabras_clave:
            if kw:
                kw_limpio = re.sub(r'<[^>]+>', '', str(kw)).strip()
                if kw_limpio and kw_limpio not in palabras_clave_limpias:
                    palabras_clave_limpias.append(kw_limpio)
        palabras_clave = palabras_clave_limpias
        
        if not tema_principal and not palabras_clave:
            logger.warning(f"Tema y palabras clave vacíos. Respuesta completa: {content}")
            logger.warning(f"Resultado parseado: {result}")
        
        tokens_used = cb.total_tokens
        cost = (tokens_used / 1000) * 0.0015
        log_usage(db, "theme_keywords", settings.CHAT_MODEL, tokens_used, cost)
        
        logger.info(f"Tema extraído: {tema_principal[:50] if tema_principal else 'N/A'}, Palabras clave: {palabras_clave[:3] if palabras_clave else 'N/A'}")
        
        return {
            "tema_principal": tema_principal,
            "palabras_clave": palabras_clave,
        }


def analyze_call(cleaned_text: str, db: Session) -> Dict[str, Any]:
    """
    Analiza una llamada usando 2 prompts separados:
    Paso 1: Clasificación
    Paso 2: Tema principal + palabras clave
    """
    # Paso 1: clasificación
    cls = classify_conversation(cleaned_text, db)
    
    # Si hay error en la clasificación, retornar error
    if cls.get("error") or not cls.get("clasificacion_general"):
        logger.error(f"Error en clasificación: {cls.get('error', 'Clasificación vacía')}")
        return {
            "category": None,
            "clasificacion_general": None,
            "tema_principal": "",
            "palabras_clave": [],
            "error": cls.get("error", "Clasificación no disponible")
        }
    
    clasificacion_general = cls["clasificacion_general"]
    category = cls["category"]
    
    # Paso 2: tema + keywords
    tk = extract_theme_and_keywords(cleaned_text, clasificacion_general, db)
    
    # Validación simplificada: solo verificar que las palabras clave aparezcan en el texto
    text_lower = cleaned_text.lower() if cleaned_text else ""
    palabras_clave_validas = []
    
    for kw in tk["palabras_clave"]:
        kw_lower = kw.lower().strip()
        # Verificar que aparezca en el texto (palabra completa o palabras individuales)
        kw_words = kw_lower.split()
        if len(kw_words) == 1:
            # Palabra única: debe aparecer en el texto
            if kw_lower in text_lower:
                palabras_clave_validas.append(kw)
            else:
                logger.warning(f"Palabra clave '{kw}' no encontrada en el texto, se omite")
        else:
            # Frase: verificar que aparezca completa o que todas las palabras importantes aparezcan
            if kw_lower in text_lower:
                palabras_clave_validas.append(kw)
            elif all(word in text_lower for word in kw_words if len(word) > 2):
                palabras_clave_validas.append(kw)
            else:
                logger.warning(f"Frase clave '{kw}' no encontrada en el texto, se omite")
    
    # Si quedan menos de 3, usar las que vienen del prompt (el prompt ya las valida)
    if len(palabras_clave_validas) < 3:
        logger.warning(f"Solo {len(palabras_clave_validas)} palabras clave válidas, usando las del prompt")
        palabras_clave_validas = tk["palabras_clave"][:8]
    
    return {
        "category": category,
        "clasificacion_general": clasificacion_general,
        "tema_principal": tk["tema_principal"],
        "palabras_clave": palabras_clave_validas,
    }


def classify_text(cleaned_text: str, db: Session) -> Dict[str, Any]:
    """
    Wrapper para mantener compatibilidad con código existente
    Usa analyze_call internamente
    """
    if not cleaned_text or not cleaned_text.strip():
        logger.warning("Texto vacío para clasificar")
        return {
            "category": "otro",
            "tema_principal": "",
            "palabras_clave": [],
        }
    
    if isinstance(cleaned_text, bytes):
        cleaned_text = cleaned_text.decode('utf-8')
    
    text_to_analyze = cleaned_text[:15000] if len(cleaned_text) > 15000 else cleaned_text
    logger.info(f"Analizando transcripción (longitud: {len(text_to_analyze)}, primeros 200 chars: {text_to_analyze[:200]}...)")
    
    try:
        result = analyze_call(text_to_analyze, db)
        logger.info(f"Clasificación final - Categoría: {result['category']}, Tema: {result['tema_principal'][:50] if result['tema_principal'] else 'N/A'}, Palabras clave: {result['palabras_clave'][:3] if result['palabras_clave'] else 'N/A'}")
        return result
    except Exception as e:
        logger.error(f"Error en análisis de llamada: {e}", exc_info=True)
        return {
            "category": "otro",
            "tema_principal": "",
            "palabras_clave": [],
        }
