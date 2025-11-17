"""
Utilidades para limpieza y procesamiento de texto
Incluye sanitización de PII (datos personales)
"""
import re
from typing import List, Tuple, Dict

# Patrones para datos sensibles
RUT_REGEXES = [
    r"\b\d{1,3}\.\d{3}\.\d{3}-[\dkK]\b",
    r"\b\d{1,2}\.\d{3}\.\d{3}-[\dkK]\b",
    r"\b\d{1,3}-\d{3}-\d{3}-\d\b",
]

EMAIL_REGEX = r"\b[\w\.-]+@[\w\.-]+\.\w+\b"
PHONE_REGEX = r"\b(?:\+?\d[\d\s\-]{7,}\d)\b"
ADDRESS_REGEX = r"\b(?:(calle|avenida|av\.?|pasaje|pje\.?)\s+[^\n,]+)"

# Fechas tipo "15 de marzo de 1986" o "01/05/2024"
DATE_REGEXES = [
    r"\b\d{1,2}\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+\d{4}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
]

# Números genéricos (precios, cantidades, etc.)
NUMBER_REGEX = r"\b\d+(?:[\.\,]\d+)*\b"

# Patrones para nombres
NAME_PATTERNS = [
    r"\bsoy\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*",
    r"\bmi nombre es\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*",
    r"\ble atiende\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+",
    r"\bsaluda\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+",
    r"\ble habla\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+",
    r"\bhabla\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+",
    r"\bme llamo\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*",
]


def _replace_names(text: str) -> str:
    """Reemplaza nombres propios por <PERSON> manteniendo la frase."""
    for patt in NAME_PATTERNS:
        text = re.sub(
            patt,
            lambda m: re.sub(
                r"[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)*",
                "<PERSON>",
                m.group(0)
            ),
            text,
            flags=re.IGNORECASE
        )
    return text


def _replace_dates_and_numbers(text: str) -> str:
    """Reemplaza fechas por <DATE> y números genéricos por <NUM>."""
    # Fechas
    for patt in DATE_REGEXES:
        text = re.sub(patt, "<DATE>", text, flags=re.IGNORECASE)
    # Números genéricos (después de RUT/teléfono para no pisarlos)
    text = re.sub(NUMBER_REGEX, "<NUM>", text)
    return text


def _sanitize_pii(text: str) -> str:
    """Reemplaza PII con tokens y nombres por <PERSON>, fechas y números."""
    # RUT
    for rut_pattern in RUT_REGEXES:
        text = re.sub(rut_pattern, "<<RUT>>", text, flags=re.IGNORECASE)
    # Email, teléfono, dirección
    text = re.sub(EMAIL_REGEX, "<<EMAIL>>", text)
    text = re.sub(PHONE_REGEX, "<<TELEFONO>>", text)
    text = re.sub(ADDRESS_REGEX, "<<DIRECCION>>", text, flags=re.IGNORECASE)
    # Nombres
    text = _replace_names(text)
    # Fechas y números (después de haber reemplazado RUT/teléfono)
    text = _replace_dates_and_numbers(text)
    return text


def clean_transcript(raw_text: str) -> str:
    """
    Limpia una transcripción de llamada:
    - Elimina líneas de SISTEMA / FIN DE LLAMADA
    - Reemplaza PII (RUT, email, teléfono, dirección)
    - Reemplaza nombres → <PERSON>
    - Reemplaza fechas → <DATE>
    - Reemplaza números → <NUM>
    - Retorna solo plain_text (sin timestamps)
    
    NOTA: original_sanitized (con timestamps) está comentado pero disponible
    por si se necesita calcular tiempos de espera en el futuro.
    """
    if not raw_text:
        return ""
    
    raw_text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Comentado: original_sanitized mantiene timestamps para cálculo de tiempos
    # sanitized_lines = []
    plain_lines = []
    
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        
        # Eliminar SISTEMA o FIN DE LA LLAMADA
        if "SISTEMA:" in line or "[FIN DE LA LLAMADA]" in line.upper():
            continue
        
        # Separar timestamp y resto de la línea para no alterar el tiempo
        m_ts = re.match(r"(\[\d{2}:\d{2}:\d{2}\])\s*(.*)", line)
        if m_ts:
            ts, content = m_ts.groups()
            content_sanitized = _sanitize_pii(content)
            # Comentado: mantener versión con timestamp para cálculo de tiempos
            # line_sanitized = f"{ts} {content_sanitized}"
            # sanitized_lines.append(line_sanitized)
        else:
            # Sin timestamp, sanitizamos todo
            content_sanitized = _sanitize_pii(line)
        
        # Versión sin timestamp, solo speaker + contenido
        m_speaker = re.match(r"\[\d{2}:\d{2}:\d{2}\]\s*(AGENTE|CLIENTE):\s*(.*)", line, flags=re.IGNORECASE)
        if m_speaker:
            speaker, content = m_speaker.groups()
            content_sanitized = _sanitize_pii(content)
            plain_lines.append(f"{speaker.upper()}: {content_sanitized.strip()}")
        else:
            # Si no tiene formato estándar, sanitizar toda la línea
            plain_lines.append(_sanitize_pii(line))
    
    # Retornar solo plain_text (sin timestamps)
    # Comentado: original_sanitized disponible si se necesita calcular tiempos
    # return {
    #     "original_sanitized": "\n".join(sanitized_lines),
    #     "plain_text": "\n".join(plain_lines),
    # }
    return "\n".join(plain_lines)


def parse_transcript(content: str) -> List[Tuple[str, str, str]]:
    """
    Parsea una transcripción y retorna lista de (timestamp, speaker, text)
    """
    lines = content.strip().split('\n')
    parsed = []
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Patrón: [timestamp] SPEAKER: text
        match = re.match(r'\[(\d{2}:\d{2}:\d{2})\]\s*(AGENTE|CLIENTE|SISTEMA):\s*(.*)', line)
        if match:
            timestamp, speaker, text = match.groups()
            parsed.append((timestamp, speaker, text.strip()))
    
    return parsed


def get_snippet(text: str, query: str, context_chars: int = 100) -> str:
    """
    Extrae un snippet del texto alrededor de la query
    """
    text_lower = text.lower()
    query_lower = query.lower()
    
    # Buscar posición de la query
    pos = text_lower.find(query_lower)
    
    if pos == -1:
        # Si no encuentra exacto, buscar palabras individuales
        words = query_lower.split()
        for word in words:
            pos = text_lower.find(word)
            if pos != -1:
                break
    
    if pos == -1:
        # Si no encuentra nada, retornar inicio
        return text[:context_chars * 2] + "..."
    
    # Extraer contexto alrededor
    start = max(0, pos - context_chars)
    end = min(len(text), pos + len(query) + context_chars)
    
    snippet = text[start:end]
    
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    
    return snippet

