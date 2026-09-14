import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.logging_config import logger
from app.browser.playwright_manager import playwright_manager
from app.api.routes import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle: boots Playwright on startup, cleans up on shutdown."""
    logger.info("Starting AI Web Research & Intelligence Agent service...")
    try:
        await playwright_manager.initialize()
    except Exception as e:
        logger.error(f"Playwright auto-initialization failed on startup: {e}")

    yield

    logger.info("Shutting down AI Web Research service...")
    await playwright_manager.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Autonomous AI Web Research & Intelligence Agent powered by Playwright and Qwen LLM with Zero Search APIs.",
    lifespan=lifespan,
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)
app.include_router(api_router, prefix="/api/v1")

# Static assets and UI dashboard
possible_frontend_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "static")),
    os.path.abspath(os.path.join(os.getcwd(), "..", "frontend")),
    os.path.abspath(os.path.join(os.getcwd(), "frontend")),
]
frontend_dir = next((d for d in possible_frontend_dirs if os.path.isdir(d)), "")

if frontend_dir:
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    app.mount("/frontend", StaticFiles(directory=frontend_dir), name="frontend")


@app.get("/", include_in_schema=False)
async def serve_dashboard():
    """Serves the frontend Cyber-Intelligence Research Dashboard."""
    if frontend_dir:
        index_path = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
    return {"message": "AI-Powered Web Research Agent is running. Visit /docs for Swagger UI."}


@app.get("/styles.css", include_in_schema=False)
async def serve_styles():
    if frontend_dir:
        p = os.path.join(frontend_dir, "styles.css")
        if os.path.exists(p):
            return FileResponse(p, media_type="text/css")
    return FileResponse(status_code=404)


@app.get("/app.js", include_in_schema=False)
async def serve_script():
    if frontend_dir:
        p = os.path.join(frontend_dir, "app.js")
        if os.path.exists(p):
            return FileResponse(p, media_type="application/javascript")
    return FileResponse(status_code=404)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
