import time
import uuid
import json
import logging
from typing import Callable

from fastapi import FastAPI, Request, Response, Depends, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

app = FastAPI(title="NexusAPI")

logger = logging.getLogger("nexusapi")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    logger.addHandler(handler)

# Disable default uvicorn access logger to ensure ONLY structured JSON logs are emitted
uvicorn_access_logger = logging.getLogger("uvicorn.access")
uvicorn_access_logger.disabled = True

@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next: Callable) -> Response:
    start_time = time.time()
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        user_id = getattr(request.state, "user_id", None)
        org_id = getattr(request.state, "organisation_id", None)
        
        log_data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "method": request.method,
            "path": request.url.path,
            "organisation_id": org_id,
            "user_id": user_id,
            "response_status": status_code,
            "duration_ms": duration_ms,
            "request_id": request_id
        }
        logger.info(json.dumps(log_data))
        
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred.",
            "request_id": request_id
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    error_code = getattr(exc, "error_code", "http_error")
    # If it's the standard auth error etc., detail might just be a string.
    # In some routes we might raise HTTPException and we want a specific "error" code.
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": error_code if error_code != "http_error" else f"error_{exc.status_code}",
            "message": str(exc.detail),
            "request_id": request_id
        },
        headers=headers
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Invalid request parameters.",
            "request_id": request_id
        }
    )

from src.routes import auth, users, credits, api
from src.database import get_db

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(credits.router)
app.include_router(api.router)

@app.get("/")
async def root():
    return {"message": "NexusAPI is running", "status": "healthy"}

@app.get("/health")
async def health_check(request: Request, db: AsyncSession = Depends(get_db)):
    """Health check. Returns 200 if healthy, 503 if database unreachable."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "error": "service_unavailable",
                "message": "Database unreachable.",
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        )
    return {"status": "healthy"}
