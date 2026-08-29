# XAI router — /xai/explanation
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import XAIRequest, XAIResponse
from app.services import ml_models, weather, features, decision_engine
from app.database import get_supabase

router = APIRouter(prefix="/xai", tags=["explainability"])


async def _handle_explanation(prediction_type: str, target_time: datetime) -> XAIResponse:
    """Internal handler for SHAP + rule-based explanation."""
    if prediction_type not in ("solar", "load"):
        raise HTTPException(
            status_code=422,
            detail="prediction_type must be 'solar' or 'load'",
        )

    target_hour = target_time.replace(minute=0, second=0, microsecond=0)

    try:
        wx = await weather.get_forecast_at(target_hour)
    except weather.ForecastHorizonError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except weather.WeatherForecastError as e:
        raise HTTPException(status_code=503, detail=str(e))

    if prediction_type == "solar":
        feature_dict = {
            "cloud_cover": wx["cloud_cover"],
            "temperature": wx["temperature"],
            "relative_humidity": wx["relative_humidity"],
            "wind_speed": wx["wind_speed"],
            "hour": target_hour.hour,
            "month": target_hour.month,
            "day_of_year": target_hour.timetuple().tm_yday,
        }
        predicted_kw = ml_models.predict_solar(feature_dict)
        contributions = ml_models.get_solar_shap_values(feature_dict)
        base_val = ml_models.get_solar_base_value()

        # Rule-based explanation
        sigma, bucket = decision_engine.solar_sigma_bucket(wx["cloud_cover"])
        rule_explanation = (
            f"Solar prediction: {predicted_kw:.3f} kW at {target_hour.hour}:00. "
            f"Cloud cover: {wx['cloud_cover']}% ({bucket}), "
            f"σ_solar = {sigma:.4f} kW. "
            f"Top contributor: {contributions[0]['feature_name']} "
            f"(SHAP={contributions[0]['shap_value']:+.4f} kW)."
        )
    else:
        try:
            feature_dict, provenance = features.build_load_features(
                target_hour, t2m=wx["T2M"]
            )
        except features.InsufficientHistoryError as e:
            raise HTTPException(status_code=422, detail=str(e))

        predicted_kw = ml_models.predict_load(feature_dict)
        contributions = ml_models.get_load_shap_values(feature_dict)
        base_val = ml_models.get_load_base_value()

        sigma, bucket = decision_engine.load_sigma_bucket(target_hour.hour)
        rule_explanation = (
            f"Load prediction: {predicted_kw:.3f} kW at {target_hour.hour}:00. "
            f"Hour bucket: {bucket}, σ_load = {sigma:.4f} kW. "
            f"Top contributor: {contributions[0]['feature_name']} "
            f"(SHAP={contributions[0]['shap_value']:+.4f} kW)."
        )

    # Save SHAP explanations to Supabase
    sb = get_supabase()
    pred_table = "solar_predictions" if prediction_type == "solar" else "load_predictions"
    latest = (
        sb.table(pred_table)
        .select("id")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    prediction_id = latest.data[0]["id"] if latest.data else 0

    for contrib in contributions:
        sb.table("shap_explanations").insert({
            "prediction_id": prediction_id,
            "prediction_type": prediction_type,
            "feature_name": contrib["feature_name"],
            "contribution_value": round(contrib["shap_value"], 6),
        }).execute()

    return XAIResponse(
        prediction_type=prediction_type,
        target_time=target_hour,
        predicted_kw=round(predicted_kw, 6),
        base_value_kw=round(base_val, 6),
        feature_contributions=contributions,
        rule_based_explanation=rule_explanation,
    )


@router.get("/explanation", response_model=XAIResponse)
async def get_explanation_get(
    prediction_type: str = Query(..., description="'solar' or 'load'"),
    target_time: datetime = Query(..., description="Target timestamp"),
):
    """GET endpoint: Get SHAP feature contributions + rule-based explanation."""
    return await _handle_explanation(prediction_type, target_time)


@router.post("/explanation", response_model=XAIResponse)
async def get_explanation_post(req: XAIRequest):
    """POST endpoint: Get SHAP feature contributions + rule-based explanation."""
    return await _handle_explanation(req.prediction_type, req.target_time)
