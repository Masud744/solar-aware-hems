# Risk margin router — /risk/margin
from fastapi import APIRouter
from app.models.schemas import RiskMarginResponse
from app.config import settings

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/margin", response_model=RiskMarginResponse)
async def get_risk_margin():
    """Return current sigma values, k, and calibration disclosure."""
    return RiskMarginResponse(
        k=settings.SAFETY_K,
        sigma_method="bucketed",
        solar_sigma_buckets={
            "Clear (0-20%)": settings.SOLAR_SIGMA_CLEAR,
            "Partly Cloudy (21-60%)": settings.SOLAR_SIGMA_PARTLY_CLOUDY,
            "Overcast (61-100%)": settings.SOLAR_SIGMA_OVERCAST,
        },
        load_sigma_buckets={
            "Night (0-5)": settings.LOAD_SIGMA_NIGHT,
            "Morning (6-11)": settings.LOAD_SIGMA_MORNING,
            "Afternoon (12-17)": settings.LOAD_SIGMA_AFTERNOON,
            "Evening (18-23)": settings.LOAD_SIGMA_EVENING,
        },
        calibration_disclosure=(
            "Coverage metrics are measured on the same held-out backtest "
            "residual set used to estimate sigma. This is NOT an independent "
            "out-of-sample calibration result."
        ),
        k_selection_rationale=(
            "k=1.0 is the selected operating point based on the observed "
            "empirical coverage-utilization trade-off in the current backtest. "
            "It is not described as mathematically optimal, statistically optimal, "
            "or as having a textbook confidence interpretation."
        ),
    )
