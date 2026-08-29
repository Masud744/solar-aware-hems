# Config — all settings from environment variables
import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Supabase — required, no fallback
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Safety multiplier — default k=1.0 (Phase 4 selected operating point)
    SAFETY_K: float

    # Open-Meteo — Kaliakair, Bangladesh
    LATITUDE: float = 24.07
    LONGITUDE: float = 90.22
    TIMEZONE: str = "Asia/Dhaka"
    FORECAST_DAYS: int = 7  # Up to 16 supported by Open-Meteo free tier

    # ML model paths (relative to project root)
    SOLAR_MODEL_PATH: str
    LOAD_MODEL_PATH: str

    # Bucketed sigma values from Phase 4
    SOLAR_SIGMA_CLEAR: float = 0.0851
    SOLAR_SIGMA_PARTLY_CLOUDY: float = 0.1317
    SOLAR_SIGMA_OVERCAST: float = 0.1386

    LOAD_SIGMA_NIGHT: float = 0.2662
    LOAD_SIGMA_MORNING: float = 0.4800
    LOAD_SIGMA_AFTERNOON: float = 0.5114
    LOAD_SIGMA_EVENING: float = 0.6075

    def __init__(self):
        # Supabase credentials — fail loudly if missing
        self.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
        self.SUPABASE_SERVICE_ROLE_KEY = os.environ.get(
            "SUPABASE_SERVICE_ROLE_KEY", ""
        )
        if not self.SUPABASE_URL or not self.SUPABASE_SERVICE_ROLE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in "
                "environment or .env file. No fallback database is configured."
            )

        # Safety k — default 1.0
        self.SAFETY_K = float(os.environ.get("SAFETY_K", "1.0"))

        # ML model paths
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        self.SOLAR_MODEL_PATH = os.environ.get(
            "SOLAR_MODEL_PATH",
            os.path.join(project_root, "ml", "solar", "models", "rf_corrected.joblib"),
        )
        self.LOAD_MODEL_PATH = os.environ.get(
            "LOAD_MODEL_PATH",
            os.path.join(project_root, "ml", "load", "models", "rf_corrected.joblib"),
        )
        self.GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
        self.GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")


settings = Settings()
