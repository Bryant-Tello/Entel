"""
Middleware para logging y manejo de errores
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para logging de requests"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(
            f"{request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            response = await call_next(request)
            
            # Calcular tiempo de procesamiento
            process_time = time.time() - start_time
            
            # Agregar header con tiempo de procesamiento
            response.headers["X-Process-Time"] = str(round(process_time, 4))
            
            # Log response
            logger.info(
                f"{request.method} {request.url.path} - "
                f"Status: {response.status_code} - "
                f"Time: {process_time:.4f}s"
            )
            
            return response
        
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error en {request.method} {request.url.path}: {e} - "
                f"Time: {process_time:.4f}s",
                exc_info=True
            )
            raise
