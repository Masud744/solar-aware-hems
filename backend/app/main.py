# FastAPI main application
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.services.ml_models import load_models
from app.routers import predict, risk, device, xai, action, ingest, energy, chat, auth, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models at startup."""
    print("Loading ML models...")
    load_models()
    print("Models loaded successfully.")
    yield
    print("Shutting down.")


app = FastAPI(
    title="Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management Under Forecast Uncertainty: An IoT-Enabled Framework — Backend API",
    description=(
        "Backend API for the official research project: "
        "'Risk-Aware and Explainable AI for Solar-Integrated Residential Energy Management "
        "Under Forecast Uncertainty: An IoT-Enabled Framework'. "
        "Implements telemetry ingestion, prediction, risk assessment, device scheduling, and XAI endpoints."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for development and deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(predict.router)
app.include_router(risk.router)
app.include_router(device.router)
app.include_router(xai.router)
app.include_router(action.router)
app.include_router(ingest.router)
app.include_router(energy.router)
app.include_router(chat.router)
app.include_router(auth.router)
app.include_router(admin.router)


@app.get("/", tags=["health"])
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "HEMS Backend",
        "version": "0.1.2",
    }
