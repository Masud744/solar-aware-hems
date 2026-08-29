# Decision Engine — implements PROJECT_MASTER_CONTEXT §8.1, §8.2
#
# Formulas:
#   Safe Solar     = max(0, Predicted Solar - k × σ_solar_bucket)
#   Conservative Load = Predicted Load + k × σ_load_bucket
#   Safe Surplus   = Safe Solar - Conservative Load
#
# §8.1 Instantaneous:  Safe Surplus >= Device Power → ALLOW, else DENY
# §8.2 Duration-aware: min(Safe Surplus over all sub-intervals) >= Device Power → ALLOW
#
# Bucketed sigma (Phase 4):
#   Solar: Clear (0-20% cloud) = 0.0851, Partly Cloudy (21-60%) = 0.1317, Overcast (61-100%) = 0.1386
#   Load:  Night (0-5) = 0.2662, Morning (6-11) = 0.4800, Afternoon (12-17) = 0.5114, Evening (18-23) = 0.6075

from dataclasses import dataclass
from app.config import settings


@dataclass
class DecisionResult:
    """Result of a single-timestep device check."""
    safe_solar: float
    conservative_load: float
    safe_surplus: float
    decision: str  # "ALLOW" or "DENY"
    reason: str


def solar_sigma_bucket(cloud_cover: float) -> tuple[float, str]:
    """Return (sigma_kw, bucket_name) for a given cloud cover percentage.

    Phase 4 bucket definitions:
      Clear:         0–20%  → σ = 0.0851 kW
      Partly Cloudy: 21–60% → σ = 0.1317 kW
      Overcast:      61–100% → σ = 0.1386 kW
    """
    if cloud_cover <= 20:
        return settings.SOLAR_SIGMA_CLEAR, "Clear (0-20%)"
    elif cloud_cover <= 60:
        return settings.SOLAR_SIGMA_PARTLY_CLOUDY, "Partly Cloudy (21-60%)"
    else:
        return settings.SOLAR_SIGMA_OVERCAST, "Overcast (61-100%)"


def load_sigma_bucket(hour: int) -> tuple[float, str]:
    """Return (sigma_kw, bucket_name) for a given hour of day.

    Phase 4 bucket definitions:
      Night:     0–5   → σ = 0.2662 kW
      Morning:   6–11  → σ = 0.4800 kW
      Afternoon: 12–17 → σ = 0.5114 kW
      Evening:   18–23 → σ = 0.6075 kW
    """
    if hour <= 5:
        return settings.LOAD_SIGMA_NIGHT, "Night (0-5)"
    elif hour <= 11:
        return settings.LOAD_SIGMA_MORNING, "Morning (6-11)"
    elif hour <= 17:
        return settings.LOAD_SIGMA_AFTERNOON, "Afternoon (12-17)"
    else:
        return settings.LOAD_SIGMA_EVENING, "Evening (18-23)"


def compute_decision(
    predicted_solar_kw: float,
    sigma_solar: float,
    predicted_load_kw: float,
    sigma_load: float,
    device_power_kw: float,
    k: float,
) -> DecisionResult:
    """Compute ALLOW/DENY decision per §8.1 (instantaneous check).

    Args:
        predicted_solar_kw: Predicted solar generation (kW)
        sigma_solar: Solar forecast uncertainty (kW) — from bucketed sigma
        predicted_load_kw: Predicted household load (kW)
        sigma_load: Load forecast uncertainty (kW) — from bucketed sigma
        device_power_kw: Rated power of the requested device (kW)
        k: Safety multiplier (default 1.0 from Phase 4)

    Returns:
        DecisionResult with intermediate values and decision
    """
    safe_solar = max(0.0, predicted_solar_kw - k * sigma_solar)
    conservative_load = predicted_load_kw + k * sigma_load
    safe_surplus = safe_solar - conservative_load

    # §8.1: Safe Surplus >= Device Power → ALLOW (note: >= not >)
    if safe_surplus >= device_power_kw:
        decision = "ALLOW"
        reason = (
            f"Safe surplus ({safe_surplus:.3f} kW) >= device power "
            f"({device_power_kw:.3f} kW). Solar generation provides "
            f"sufficient margin after safety deductions."
        )
    else:
        decision = "DENY"
        deficit = device_power_kw - safe_surplus
        reason = (
            f"Safe surplus ({safe_surplus:.3f} kW) < device power "
            f"({device_power_kw:.3f} kW). Deficit: {deficit:.3f} kW. "
            f"Insufficient safe solar surplus to power device."
        )

    return DecisionResult(
        safe_solar=safe_solar,
        conservative_load=conservative_load,
        safe_surplus=safe_surplus,
        decision=decision,
        reason=reason,
    )


def compute_duration_aware_decision(
    hourly_results: list[DecisionResult],
    device_power_kw: float,
) -> tuple[str, str, float]:
    """§8.2 Duration-aware check: min(Safe Surplus over all hours) >= Device Power.

    Args:
        hourly_results: List of DecisionResult for each hour in the duration
        device_power_kw: Rated power of the device

    Returns:
        (decision, reason, min_surplus)
    """
    if not hourly_results:
        return "DENY", "No hourly results to evaluate", 0.0

    min_surplus = min(r.safe_surplus for r in hourly_results)
    min_hour_idx = next(
        i for i, r in enumerate(hourly_results)
        if r.safe_surplus == min_surplus
    )

    if min_surplus >= device_power_kw:
        decision = "ALLOW"
        reason = (
            f"Duration-aware check passed. Minimum safe surplus across "
            f"{len(hourly_results)} hour(s) is {min_surplus:.3f} kW "
            f"(at hour +{min_hour_idx}) >= device power {device_power_kw:.3f} kW."
        )
    else:
        decision = "DENY"
        deficit = device_power_kw - min_surplus
        reason = (
            f"Duration-aware check failed. Minimum safe surplus across "
            f"{len(hourly_results)} hour(s) is {min_surplus:.3f} kW "
            f"(at hour +{min_hour_idx}) < device power {device_power_kw:.3f} kW. "
            f"Deficit: {deficit:.3f} kW. Safe surplus dips below device power "
            f"during the run."
        )

    return decision, reason, min_surplus
