# import os
# import logging
# from contextlib import asynccontextmanager
# from fastapi import FastAPI, Request
# from fastapi.staticfiles import StaticFiles
# from fastapi.templating import Jinja2Templates
# from fastapi.middleware.cors import CORSMiddleware
# from sqlalchemy import text

# from app.core.config import settings
# from app.core.database import engine, SessionLocal
# from app.core.logging_config import setup_logging
# from app.routers import auth, admin, candidate, api
# from app.services.admin_setup import create_admin_user


# # Setup logging
# setup_logging()
# logger = logging.getLogger(__name__)

# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     """Startup and shutdown events"""
#     logger.info("Starting up Mercer HR Assessment Platform...")
    
#     # Create uploads directory
#     os.makedirs("uploads", exist_ok=True)
#     os.makedirs("app/static/uploads", exist_ok=True)
    
#     # Test database connection
#     try:
#         with SessionLocal() as db:
#             db.execute(text("SELECT 1"))
#         logger.info("Database connection successful")
#     except Exception as e:
#         logger.error(f"Database connection failed: {e}")
    
#     # Create admin user
#     await create_admin_user()
    
#     logger.info("Startup complete!")
#     yield
#     logger.info("Shutting down...")

# app = FastAPI(
#     title="Mercer HR Assessment Platform",
#     description="A comprehensive coding assessment platform for technical interviews",
#     version="1.0.0",
#     lifespan=lifespan
# )

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Mount static files
# app.mount("/static", StaticFiles(directory="app/static"), name="static")

# # Include routers
# app.include_router(auth.router, prefix="/auth", tags=["auth"])
# app.include_router(admin.router, prefix="/admin", tags=["admin"])
# app.include_router(candidate.router, prefix="/candidate", tags=["candidate"])
# app.include_router(api.router, prefix="/api", tags=["api"])

# # Templates
# templates = Jinja2Templates(directory="app/templates")

# @app.get("/")
# async def home(request: Request):
#     return templates.TemplateResponse("home.html", {"request": request})

# @app.get("/health")
# async def health_check():
#     return {"status": "healthy", "version": "1.0.0"}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine, SessionLocal, Base
from app.core.logging_config import setup_logging
from app.routers import auth, admin, candidate, api
from app.services.admin_setup import create_admin_user

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("Starting up Mercer HR Assessment Platform...")
    
    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("app/static/uploads", exist_ok=True)
    
    # ✅ Ensure tables exist
    try:
        import app.models  # make sure all models (User, Candidate, etc.) are imported
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables ensured")
    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
    
    # Test database connection
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection successful")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
    
    # Create admin user
    await create_admin_user()
    
    logger.info("Startup complete!")
    yield
    logger.info("Shutting down...")

app = FastAPI(
    title="Mercer HR Assessment Platform",
    description="A comprehensive coding assessment platform for technical interviews",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(candidate.router, prefix="/candidate", tags=["candidate"])
app.include_router(api.router, prefix="/api", tags=["api"])

# Templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
