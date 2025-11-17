"""
Rate limiter para OpenAI API
Maneja límites de tokens por segundo y requests por minuto
"""
import time
import asyncio
from collections import deque
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter para OpenAI API
    
    Límites de OpenAI:
    - Tier 1: 500 tokens/minuto, 3 requests/minuto
    - Tier 2: 5,000 tokens/minuto, 60 requests/minuto
    - Tier 3: 40,000 tokens/minuto, 3,500 requests/minuto
    
    Usamos valores conservadores para evitar errores 429
    """
    
    def __init__(
        self,
        tokens_per_minute: int = 1000000,  # Aumentado: límite real de OpenAI para embeddings (1M tokens/min)
        requests_per_minute: int = 3000,   # Aumentado: límite real de OpenAI
        tokens_per_second: Optional[int] = None  # Calculado automáticamente
    ):
        self.tokens_per_minute = tokens_per_minute
        self.requests_per_minute = requests_per_minute
        
        # Tokens por segundo (80% del límite para seguridad)
        if tokens_per_second is None:
            self.tokens_per_second = int((tokens_per_minute * 0.8) / 60)
        else:
            self.tokens_per_second = tokens_per_second
        
        # Tracking de tokens usados
        self.token_history = deque()  # (timestamp, tokens)
        self.request_history = deque()  # (timestamp,)
        
        # Lock para thread safety (usar threading para compatibilidad síncrona)
        import threading
        self._thread_lock = threading.Lock()
        self._lock_initialized = True
    
    async def wait_for_capacity(self, estimated_tokens: int = 100):
        """
        Espera hasta que haya capacidad para procesar los tokens estimados
        """
        # Asegurar que el lock esté inicializado
        import threading
        if not hasattr(self, '_thread_lock') or not getattr(self, '_lock_initialized', False):
            self._thread_lock = threading.Lock()
            self._lock_initialized = True
        
        # Usar threading lock para sincronización
        with self._thread_lock:
            current_time = time.time()
            
        # Limpiar historial antiguo (> 1 minuto)
        minute_ago = current_time - 60
        while self.token_history and self.token_history[0][0] < minute_ago:
            self.token_history.popleft()
        while self.request_history and self.request_history[0] < minute_ago:
            self.request_history.popleft()
        
        # Verificar límite de requests por minuto
        if len(self.request_history) >= self.requests_per_minute:
            # Esperar hasta que expire el request más antiguo
            oldest_request = self.request_history[0]
            wait_time = 60 - (current_time - oldest_request) + 0.1
            if wait_time > 0:
                logger.info(f"Rate limit: Esperando {wait_time:.2f}s por límite de requests")
                await asyncio.sleep(wait_time)
                current_time = time.time()
                # Limpiar de nuevo
                while self.request_history and self.request_history[0] < current_time - 60:
                    self.request_history.popleft()
        
        # Verificar límite de tokens por minuto
        total_tokens_last_minute = sum(tokens for _, tokens in self.token_history)
        if total_tokens_last_minute + estimated_tokens > self.tokens_per_minute:
            # Esperar hasta que haya espacio
            if self.token_history:
                oldest_token_time = self.token_history[0][0]
                wait_time = 60 - (current_time - oldest_token_time) + 0.1
                if wait_time > 0:
                    # Limitar espera máxima a 5 segundos para no bloquear demasiado
                    wait_time = min(wait_time, 5.0)
                    if wait_time > 1.0:  # Solo loggear si espera más de 1 segundo
                        logger.info(f"Rate limit: Esperando {wait_time:.2f}s por límite de tokens (límite: {self.tokens_per_minute} tokens/min)")
                    await asyncio.sleep(wait_time)
        
        # Verificar límite de tokens por segundo
        second_ago = current_time - 1
        tokens_last_second = sum(
            tokens for ts, tokens in self.token_history
            if ts >= second_ago
        )
        
        if tokens_last_second + estimated_tokens > self.tokens_per_second:
            # Esperar hasta el próximo segundo
            wait_time = 1.1 - (current_time - int(current_time))
            if wait_time > 0:
                logger.debug(f"Rate limit: Esperando {wait_time:.2f}s por límite de tokens/segundo")
                await asyncio.sleep(wait_time)
        
        # Registrar uso
        current_time = time.time()
        self.token_history.append((current_time, estimated_tokens))
        self.request_history.append(current_time)
    
    def record_usage(self, tokens_used: int):
        """Registra tokens usados (para ajuste dinámico)"""
        current_time = time.time()
        # Thread-safe usando lock síncrono
        import threading
        if not hasattr(self, '_thread_lock') or not self._lock_initialized:
            self._thread_lock = threading.Lock()
            self._lock_initialized = True
        with self._thread_lock:
            self.token_history.append((current_time, tokens_used))


# Instancia global del rate limiter
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Obtiene la instancia global del rate limiter"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

