import json
from typing import Callable

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware

from app.db.session import AsyncSessionLocal
from app.models.audit_log import AuditLog
from app.core.security import decode_token


class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware que captura automáticamente peticiones POST, PUT y DELETE
    y registra un AuditLog en la base de datos si modifican estado.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Solo registrar métodos que mutan estado o login
        method = request.method
        path = request.url.path
        
        # Continuar con el request normalmente
        response = await call_next(request)

        if method in ("POST", "PUT", "DELETE") or "/login" in path:
            # Detectar usuario desde el request (si existe el JWT en Authorization header)
            user_id = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                payload = decode_token(token)
                if payload and "sub" in payload:
                    user_id = int(payload["sub"])
            
            # Si fue login exitoso y obtuvimos el sub en la respuesta, pero eso requiere leer el body.
            # Por simplicidad, registramos la llamada. 
            
            action = f"{method} {path}"
            
            # Evitar registrar requests que fallaron por validación pre via
            if response.status_code >= 400:
                action = f"[FAILED {response.status_code}] " + action

            entity = path.split("/")[3] if len(path.split("/")) > 3 else "system"
            
            # Insertar en base de datos en un entorno asíncrono
            async with AsyncSessionLocal() as db:
                audit = AuditLog(
                    user_id=user_id,
                    action=action,
                    entity=entity,
                    ip_address=request.client.host if request.client else None,
                    # details = {"status_code": response.status_code}
                )
                db.add(audit)
                await db.commit()
                
        return response
