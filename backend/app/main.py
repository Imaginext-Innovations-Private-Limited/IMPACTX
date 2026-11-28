
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import check_database, create_collections, db

# Import API routers
from app.routers.auth import router as auth_router
from app.routers.ai_routes import router as ai_router
from app.routers.reports import router as reports_router
from app.routers.water import router as water_router
from app.routers.admin import router as admin_router
from app.routers.map_routes import router as map_router


# -----------------------------------------
# FASTAPI APPLICATION
# -----------------------------------------

app = FastAPI(
    title="AquaWatch API",
    description="AI-Powered Lake and Water Quality Monitoring Platform",
    version="1.0.0"
)


# -----------------------------------------
# CORS CONFIGURATION
# -----------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# -----------------------------------------
# UPLOAD DIRECTORY
# -----------------------------------------

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# -----------------------------------------
# SERVE UPLOADED IMAGES
# -----------------------------------------

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads"
)


# -----------------------------------------
# DATABASE INITIALIZATION
# -----------------------------------------

@app.on_event("startup")
def startup_event():

    if check_database():
        create_collections()


# -----------------------------------------
# REGISTER API ROUTERS
# -----------------------------------------

app.include_router(auth_router)

app.include_router(reports_router)

app.include_router(ai_router)

app.include_router(water_router)

app.include_router(admin_router)

# New citizen and admin map endpoint
app.include_router(map_router)


# -----------------------------------------
# HOME ROUTE
# -----------------------------------------

@app.get("/")
def home():

    return {
        "message": "Welcome to AquaWatch!",
        "status": "Backend is running successfully"
    }


# -----------------------------------------
# HEALTH CHECK
# -----------------------------------------

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "project": "AquaWatch"
    }


# -----------------------------------------
# DATABASE STATUS
# -----------------------------------------

@app.get("/api/database-status")
def database_status():

    return {
        "database": "MongoDB",
        "connected": check_database()
    }


# -----------------------------------------
# MONGODB COLLECTIONS
# -----------------------------------------

@app.get("/api/collections")
def get_collections():

    return {
        "collections": sorted(
            db.list_collection_names()
        )
    }
