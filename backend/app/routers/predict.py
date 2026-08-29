# Prediction routers — /predict/solar, /predict/load
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import (
    SolarPredictionRequest, SolarPredictionResponse,
    LoadPredictionRequest, LoadPredictionResponse,
)
from app.services import ml_models, weather, decision_engine, features
from app.config import settings
from app.database import get_supabase

router = APIRouter(prefix="/predict", tags=["predictions"])


async def _handle_solar_prediction(target_time: datetime) -> SolarPredictionResponse:
    """Internal handler for solar prediction."""
    try:
        wx = await weather.get_forecast_at(target_time)
    except weather.ForecastHorizonError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except weather.WeatherForecastError as e:
        raise HTTPException(status_code=503, detail=str(e))

    target_hour = target_time.replace(minute=0, second=0, microsecond=0)
    solar_features = {
        "cloud_cover": wx["cloud_cover"],
        "temperature": wx["temperature"],
        "relative_humidity": wx["relative_humidity"],
        "wind_speed": wx["wind_speed"],
        "hour": target_hour.hour,
        "month": target_hour.month,
        "day_of_year": target_hour.timetuple().tm_yday,
    }

    predicted_kw = ml_models.predict_solar(solar_features)
    sigma_kw, sigma_bucket = decision_engine.solar_sigma_bucket(wx["cloud_cover"])
    safe_kw = max(0.0, predicted_kw - settings.SAFETY_K * sigma_kw)

    solar_version = ml_models.get_solar_model_version()

    # Save to Supabase
    sb = get_supabase()
    sb.table("solar_predictions").insert({
        "ts": target_hour.isoformat(),
        "predicted_kw": round(predicted_kw, 6),
        "safe_kw": round(safe_kw, 6),
        "sigma": round(sigma_kw, 6),
        "model_version": solar_version,
    }).execute()

    return SolarPredictionResponse(
        target_time=target_hour,
        predicted_kw=round(predicted_kw, 6),
        safe_kw=round(safe_kw, 6),
        sigma_kw=round(sigma_kw, 6),
        sigma_bucket=sigma_bucket,
        k=settings.SAFETY_K,
        cloud_cover=wx["cloud_cover"],
        temperature=wx["temperature"],
        relative_humidity=wx["relative_humidity"],
        wind_speed=wx["wind_speed"],
        model_version=solar_version,
        is_stale=wx.get("is_stale", False),
        cached_at=wx.get("cached_at"),
    )


async def _handle_load_prediction(target_time: datetime, temperature_c: Optional[float] = None) -> LoadPredictionResponse:
    """Internal handler for load prediction."""
    target_hour = target_time.replace(minute=0, second=0, microsecond=0)

    is_stale = False
    cached_at = None

    if temperature_c is not None:
        t2m = temperature_c
    else:
        try:
            wx = await weather.get_forecast_at(target_time)
            t2m = wx["T2M"]
            is_stale = wx.get("is_stale", False)
            cached_at = wx.get("cached_at")
        except weather.ForecastHorizonError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except weather.WeatherForecastError as e:
            raise HTTPException(status_code=503, detail=str(e))

    try:
        load_features, provenance = features.build_load_features(target_hour, t2m=t2m)
    except features.InsufficientHistoryError as e:
        raise HTTPException(status_code=422, detail=str(e))

    predicted_kw = ml_models.predict_load(load_features)
    sigma_kw, sigma_bucket = decision_engine.load_sigma_bucket(target_hour.hour)
    conservative_kw = predicted_kw + settings.SAFETY_K * sigma_kw
    load_version = ml_models.get_load_model_version()

    # Save to Supabase
    sb = get_supabase()
    sb.table("load_predictions").insert({
        "ts": target_hour.isoformat(),
        "predicted_kw": round(predicted_kw, 6),
        "conservative_kw": round(conservative_kw, 6),
        "sigma": round(sigma_kw, 6),
        "model_version": load_version,
    }).execute()

    return LoadPredictionResponse(
        target_time=target_hour,
        predicted_kw=round(predicted_kw, 6),
        conservative_kw=round(conservative_kw, 6),
        sigma_kw=round(sigma_kw, 6),
        sigma_bucket=sigma_bucket,
        k=settings.SAFETY_K,
        t2m_value=t2m,
        model_version=load_version,
        history_mode=provenance["mode"],
        feature_provenance=provenance,
        t2m_disclosure=weather.get_t2m_disclosure(),
        is_stale=is_stale,
        cached_at=cached_at,
    )


@router.get("/solar", response_model=SolarPredictionResponse)
async def get_predict_solar(target_time: datetime = Query(..., description="Target time for solar prediction")):
    """GET endpoint: Predict solar generation for a future time."""
    return await _handle_solar_prediction(target_time)


@router.post("/solar", response_model=SolarPredictionResponse)
async def post_predict_solar(req: SolarPredictionRequest):
    """POST endpoint: Predict solar generation for a future time."""
    return await _handle_solar_prediction(req.target_time)


@router.get("/load", response_model=LoadPredictionResponse)
async def get_predict_load(
    target_time: datetime = Query(..., description="Target time for load prediction"),
    temperature_c: Optional[float] = Query(None, description="Optional temperature (°C)"),
):
    """GET endpoint: Predict household load for a future time."""
    return await _handle_load_prediction(target_time, temperature_c)


@router.post("/load", response_model=LoadPredictionResponse)
async def post_predict_load(req: LoadPredictionRequest):
    """POST endpoint: Predict household load for a future time."""
    return await _handle_load_prediction(req.target_time, req.temperature_c)
