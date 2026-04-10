# app/api/middleware.py
# ============================================================
# FastAPI middleware -- runs on every HTTP request
# 1. RequestTimingMiddleware: logs how long each request takes
# 2. AdminAuthMiddleware: protects /api/upload routes with password
# ============================================================
import time
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
import os


class RequestTimingMiddleware(BaseHTTPMiddleware):
    '''
    Logs the HTTP method, path, status code, and response time
    for every request. Useful for spotting slow endpoints.
    Example log: POST /api/chat/ask 200 3241ms
    '''
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()  # High-resolution timer

        # Pass request to the actual route handler
        response = await call_next(request)

        # Calculate elapsed time in milliseconds
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            f'{request.method} {request.url.path} '
            f'{response.status_code} {elapsed_ms:.0f}ms'
        )

        # Add timing header so the UI can also read it
        response.headers['X-Process-Time-Ms'] = str(round(elapsed_ms))

        return response


class AdminAuthMiddleware(BaseHTTPMiddleware):
    '''
    Protects admin-only routes (/api/upload) with a simple password header.
    The admin password is set in .env as ADMIN_PASSWORD.
    The PyQt6 admin panel sends the password in the X-Admin-Token header.

    NOTE: This is a simple local auth -- not intended for internet-facing servers.
    For an offline desktop app, this level of security is appropriate.
    '''
    PROTECTED_PREFIXES = ['/api/upload']  # Paths that require admin auth

    async def dispatch(self, request: Request, call_next):
        # Check if this request targets a protected route
        is_protected = any(
            request.url.path.startswith(prefix)
            for prefix in self.PROTECTED_PREFIXES
        )

        if is_protected:
            token = request.headers.get('X-Admin-Token', '')
            expected = os.getenv('ADMIN_PASSWORD', 'vidya123')

            if token != expected:
                logger.warning(f'Unauthorized admin access attempt: {request.url.path}')
                return JSONResponse(
                    status_code=401,
                    content={'detail': 'Invalid admin credentials'}
                )

        return await call_next(request)  # Proceed to route handler


# ---- Register middleware in app/api/main.py ----
# Add these lines after creating the FastAPI() instance:
#
# from app.api.middleware import RequestTimingMiddleware, AdminAuthMiddleware
# app.add_middleware(RequestTimingMiddleware)
# app.add_middleware(AdminAuthMiddleware)