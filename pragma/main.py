import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from pragma.config import get_settings
from pragma.routers.api import api_router as v1
from pragma.utils.logging import logger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Load settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    logger.info("Starting Pragma API FastAPI application")
    yield
    logger.info("Shutting down Pragma API FastAPI application")


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Pragma Interactive API",
    description="FastAPI application for interacting with Pragma API",
    version="1.0.0",
    lifespan=lifespan,
)

# # Setup telemetry first
# setup_telemetry(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


# Root level routes
@app.get("/", tags=["root"], response_class=RedirectResponse, status_code=301)
async def root():
    """Redirect root to health check endpoint."""
    return RedirectResponse(url="/health")


@app.get("/health", tags=["health"])
async def health():
    """Health check endpoint."""
    return {"status": "server is running", "timestamp": datetime.now(UTC).isoformat(), "version": "1.0.0"}


# Include the v1 router with prefix "/node" and tags "node"
app.include_router(v1, prefix="/node")


# Add exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for HTTP exceptions."""
    logger.error(f"HTTP exception: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Custom exception handler for general exceptions."""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"},
    )
