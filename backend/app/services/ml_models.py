# ML model loading and prediction service
#
# Models verified from actual .joblib files:
#   Solar RF: 7 features in order:
#     [cloud_cover, temperature, relative_humidity, wind_speed, hour, month, day_of_year]
#   Load RF: 16 features in order:
#     [power_lag_1, power_lag_2, power_lag_3, power_lag_12, power_lag_24,
#      power_lag_48, power_lag_168, rolling_mean_3h, rolling_mean_24h,
#      rolling_std_24h, rolling_mean_168h, hour, day_of_week, month,
#      is_weekend, T2M]

import os
import joblib
import numpy as np
import pandas as pd
from app.config import settings

# Exact feature order verified from model.feature_names_in_
SOLAR_FEATURES = [
    "cloud_cover", "temperature", "relative_humidity", "wind_speed",
    "hour", "month", "day_of_year",
]

LOAD_FEATURES = [
    "power_lag_1", "power_lag_2", "power_lag_3", "power_lag_12",
    "power_lag_24", "power_lag_48", "power_lag_168",
    "rolling_mean_3h", "rolling_mean_24h", "rolling_std_24h",
    "rolling_mean_168h",
    "hour", "day_of_week", "month", "is_weekend", "T2M",
]

# Global model references (loaded at startup)
_solar_model = None
_load_model = None


def load_models():
    """Load ML models from disk. Called once at app startup."""
    global _solar_model, _load_model
    _solar_model = joblib.load(settings.SOLAR_MODEL_PATH)
    _load_model = joblib.load(settings.LOAD_MODEL_PATH)

    # Verify feature names match expectations
    actual_solar = _solar_model.feature_names_in_.tolist()
    actual_load = _load_model.feature_names_in_.tolist()

    if actual_solar != SOLAR_FEATURES:
        raise RuntimeError(
            f"Solar model feature mismatch! "
            f"Expected: {SOLAR_FEATURES}, Got: {actual_solar}"
        )
    if actual_load != LOAD_FEATURES:
        raise RuntimeError(
            f"Load model feature mismatch! "
            f"Expected: {LOAD_FEATURES}, Got: {actual_load}"
        )


def predict_solar(features: dict) -> float:
    """Predict solar generation (kW) from weather + calendar features.

    Args:
        features: dict with keys matching SOLAR_FEATURES

    Returns:
        Predicted solar generation in kW (clamped to >= 0)
    """
    global _solar_model
    if _solar_model is None:
        load_models()

    # Build DataFrame with exact feature order
    df = pd.DataFrame([{f: features[f] for f in SOLAR_FEATURES}])
    pred = _solar_model.predict(df)[0]
    return max(0.0, float(pred))


def predict_load(features: dict) -> float:
    """Predict household load (kW) from lag/rolling/calendar/weather features.

    Args:
        features: dict with keys matching LOAD_FEATURES

    Returns:
        Predicted load in kW (clamped to >= 0)
    """
    global _load_model
    if _load_model is None:
        load_models()

    # Build DataFrame with exact feature order
    df = pd.DataFrame([{f: features[f] for f in LOAD_FEATURES}])
    pred = _load_model.predict(df)[0]
    return max(0.0, float(pred))


def get_solar_shap_values(features: dict) -> list[dict]:
    """Compute per-feature SHAP values for a single solar prediction.

    Returns list of {feature_name, feature_value, shap_value} dicts,
    sorted by absolute SHAP value descending.
    """
    if _solar_model is None:
        raise RuntimeError("Models not loaded.")

    import shap
    df = pd.DataFrame([{f: features[f] for f in SOLAR_FEATURES}])
    explainer = shap.TreeExplainer(_solar_model)
    shap_values = explainer.shap_values(df)[0]

    contributions = []
    for i, fname in enumerate(SOLAR_FEATURES):
        contributions.append({
            "feature_name": fname,
            "feature_value": float(features[fname]),
            "shap_value": float(shap_values[i]),
        })

    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return contributions


def get_load_shap_values(features: dict) -> list[dict]:
    """Compute per-feature SHAP values for a single load prediction.

    Returns list of {feature_name, feature_value, shap_value} dicts,
    sorted by absolute SHAP value descending.
    """
    if _load_model is None:
        raise RuntimeError("Models not loaded.")

    import shap
    df = pd.DataFrame([{f: features[f] for f in LOAD_FEATURES}])
    explainer = shap.TreeExplainer(_load_model)
    shap_values = explainer.shap_values(df)[0]

    contributions = []
    for i, fname in enumerate(LOAD_FEATURES):
        contributions.append({
            "feature_name": fname,
            "feature_value": float(features[fname]),
            "shap_value": float(shap_values[i]),
        })

    contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
    return contributions


def get_solar_base_value() -> float:
    """Return the expected base value E[f(x)] for the solar model."""
    if _solar_model is None:
        raise RuntimeError("Models not loaded.")
    import shap
    explainer = shap.TreeExplainer(_solar_model)
    val = explainer.expected_value
    if isinstance(val, (list, tuple, np.ndarray)):
        return float(val[0])
    return float(val)


def get_load_base_value() -> float:
    """Return the expected base value E[f(x)] for the load model."""
    if _load_model is None:
        raise RuntimeError("Models not loaded.")
    import shap
    explainer = shap.TreeExplainer(_load_model)
    val = explainer.expected_value
    if isinstance(val, (list, tuple, np.ndarray)):
        return float(val[0])
    return float(val)


def get_solar_model_version() -> str:
    """Return the filename/version identifier of the active solar model."""
    return os.path.basename(settings.SOLAR_MODEL_PATH).replace(".joblib", "")


def get_load_model_version() -> str:
    """Return the filename/version identifier of the active load model."""
    return os.path.basename(settings.LOAD_MODEL_PATH).replace(".joblib", "")
