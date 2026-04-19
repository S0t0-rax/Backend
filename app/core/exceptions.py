"""
Excepciones HTTP personalizadas + handlers globales FastAPI.
"""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = "APP_ERROR"):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


class NotFoundException(AppException):
    def __init__(self, resource: str = "Recurso"):
        super().__init__(404, f"{resource} no encontrado.", "NOT_FOUND")


class UnauthorizedException(AppException):
    def __init__(self, detail: str = "No autenticado."):
        super().__init__(401, detail, "UNAUTHORIZED")


class ForbiddenException(AppException):
    def __init__(self, detail: str = "Sin permisos."):
        super().__init__(403, detail, "FORBIDDEN")


class ConflictException(AppException):
    def __init__(self, detail: str = "Conflicto."):
        super().__init__(409, detail, "CONFLICT")


class BadRequestException(AppException):
    def __init__(self, detail: str = "Solicitud inválida."):
        super().__init__(400, detail, "BAD_REQUEST")


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exc_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.error_code, "message": exc.detail, "path": str(request.url)},
        )
