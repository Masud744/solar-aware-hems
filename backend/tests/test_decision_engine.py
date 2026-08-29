# Tests for the decision engine — §8.3 worked example + edge cases
#
# These tests call the decision engine function DIRECTLY, bypassing
# HTTP endpoints and Supabase. This verifies the pure arithmetic.
#
# The §8.3 test uses k=1.5 (the worked example value), not the
# production default k=1.0. This is why k is a parameter on the
# internal function but NOT exposed on public endpoints.

import os
import sys
from pytest import approx

# Ensure the app package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Mock the config to avoid requiring Supabase credentials for unit tests
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-key-for-unit-tests")

from app.services.decision_engine import (
    compute_decision,
    compute_duration_aware_decision,
    solar_sigma_bucket,
    load_sigma_bucket,
)


class TestSection83WorkedExample:
    """Reproduce §8.3 worked example EXACTLY.

    Scenario: 11:00 AM, Washing Machine (1.2 kW, 1 hour).

    The §8.3 document specifies these EXACT intermediate values:
      Safe Solar        = 2.10 − 0.525 = 1.575 kW
      Conservative Load = 0.65 + 0.15  = 0.80 kW
      Safe Surplus      = 1.575 − 0.80 = 0.775 kW
      Decision: DENY (0.775 < 1.2)

    NOTE: §8.3 computes Conservative Load = Predicted + σ_load (without k multiplier),
    while applying k only to the solar safety margin (Safety Margin = k × σ_solar = 1.5 × 0.35).
    Our decision engine formula applies k symmetrically to both sides:
      Safe Solar = Predicted - k × σ_solar
      Conservative Load = Predicted + k × σ_load

    To reproduce the EXACT §8.3 numbers through the symmetric formula, we pass
    the pre-multiplied safety margin as σ_solar (0.525) and σ_load (0.15) with k=1.0.
    This makes the decision engine compute:
      Safe Solar = 2.10 - 1.0 × 0.525 = 1.575 ✓
      Conservative Load = 0.65 + 1.0 × 0.15 = 0.80 ✓
      Safe Surplus = 0.775 ✓
    """

    def test_exact_intermediate_values(self):
        """Verify §8.3 exact numbers: 1.575, 0.80, 0.775."""
        result = compute_decision(
            predicted_solar_kw=2.10,
            sigma_solar=0.525,   # pre-multiplied: k(1.5) × σ(0.35) = 0.525
            predicted_load_kw=0.65,
            sigma_load=0.15,     # as stated in §8.3
            device_power_kw=1.2,
            k=1.0,              # k=1.0 since margins are pre-multiplied
        )

        assert result.safe_solar == approx(1.575, abs=1e-9)
        assert result.conservative_load == approx(0.80, abs=1e-9)
        assert result.safe_surplus == approx(0.775, abs=1e-9)

    def test_decision_is_deny(self):
        result = compute_decision(
            predicted_solar_kw=2.10,
            sigma_solar=0.525,
            predicted_load_kw=0.65,
            sigma_load=0.15,
            device_power_kw=1.2,
            k=1.0,
        )
        assert result.decision == "DENY"

    def test_reason_contains_surplus_value(self):
        result = compute_decision(
            predicted_solar_kw=2.10,
            sigma_solar=0.525,
            predicted_load_kw=0.65,
            sigma_load=0.15,
            device_power_kw=1.2,
            k=1.0,
        )
        assert "0.775" in result.reason
        assert "1.2" in result.reason or "1.200" in result.reason

    def test_symmetric_formula_with_raw_k(self):
        """Verify the symmetric formula produces the correct values when k
        is applied to both sides (this is how the deployed engine works).

        With k=1.5, σ_solar=0.35, σ_load=0.15:
          Safe Solar = 2.10 - 1.5×0.35 = 1.575
          Conservative Load = 0.65 + 1.5×0.15 = 0.875
          Safe Surplus = 1.575 - 0.875 = 0.700
          Decision: DENY (0.700 < 1.2)
        """
        result = compute_decision(
            predicted_solar_kw=2.10,
            sigma_solar=0.35,
            predicted_load_kw=0.65,
            sigma_load=0.15,
            device_power_kw=1.2,
            k=1.5,
        )
        assert result.safe_solar == approx(1.575, abs=1e-9)
        assert result.conservative_load == approx(0.875, abs=1e-9)
        assert result.safe_surplus == approx(0.700, abs=1e-9)
        assert result.decision == "DENY"


class TestEdgeCases:
    """Three edge cases beyond the happy path."""

    def test_boundary_safe_surplus_equals_device_power(self):
        """Safe Surplus exactly equal to device power → ALLOW per >= in §8.1."""
        result = compute_decision(
            predicted_solar_kw=2.0,
            sigma_solar=0.0,
            predicted_load_kw=0.0,
            sigma_load=0.0,
            device_power_kw=2.0,
            k=1.0,
        )
        assert result.safe_surplus == approx(2.0, abs=1e-9)
        assert result.decision == "ALLOW"

    def test_negative_safe_surplus_no_crash(self):
        """Negative Safe Surplus → DENY, no crash."""
        result = compute_decision(
            predicted_solar_kw=0.1,
            sigma_solar=0.3,  # k*sigma > predicted → safe_solar clamps to 0
            predicted_load_kw=0.5,
            sigma_load=0.2,
            device_power_kw=0.3,
            k=1.0,
        )
        # safe_solar = max(0, 0.1 - 1.0*0.3) = max(0, -0.2) = 0.0
        # conservative_load = 0.5 + 1.0*0.2 = 0.7
        # safe_surplus = 0.0 - 0.7 = -0.7
        assert result.safe_solar == approx(0.0, abs=1e-9)
        assert result.safe_surplus == approx(-0.7, abs=1e-9)
        assert result.decision == "DENY"

    def test_duration_aware_mid_run_dip(self):
        """§8.2: Safe surplus dips mid-run → DENY even if start looks fine.

        Device runs 2 hours. At t=0, surplus = 2.0 kW (fine).
        At t=1, surplus drops to 0.3 kW. Device power = 0.5 kW.
        min(2.0, 0.3) = 0.3 < 0.5 → DENY.
        """
        # Hour 0: surplus is 2.0 kW
        result_0 = compute_decision(
            predicted_solar_kw=3.0,
            sigma_solar=0.0,
            predicted_load_kw=1.0,
            sigma_load=0.0,
            device_power_kw=0.5,
            k=1.0,
        )
        assert result_0.safe_surplus == approx(2.0, abs=1e-9)
        assert result_0.decision == "ALLOW"  # Hour 0 alone would ALLOW

        # Hour 1: surplus drops to 0.3 kW
        result_1 = compute_decision(
            predicted_solar_kw=1.0,
            sigma_solar=0.0,
            predicted_load_kw=0.7,
            sigma_load=0.0,
            device_power_kw=0.5,
            k=1.0,
        )
        assert result_1.safe_surplus == approx(0.3, abs=1e-9)

        # Duration-aware: min(2.0, 0.3) = 0.3 < 0.5 → DENY
        decision, reason, min_surplus = compute_duration_aware_decision(
            [result_0, result_1], device_power_kw=0.5
        )
        assert min_surplus == approx(0.3, abs=1e-9)
        assert decision == "DENY"


class TestSigmaBuckets:
    """Verify sigma bucket boundary conditions."""

    def test_solar_clear_boundary(self):
        sigma, name = solar_sigma_bucket(20)
        assert sigma == approx(0.0851, abs=1e-4)
        assert "Clear" in name

    def test_solar_partly_cloudy_boundary(self):
        sigma, name = solar_sigma_bucket(21)
        assert sigma == approx(0.1317, abs=1e-4)
        assert "Partly" in name

    def test_solar_overcast_boundary(self):
        sigma, name = solar_sigma_bucket(61)
        assert sigma == approx(0.1386, abs=1e-4)
        assert "Overcast" in name

    def test_load_night_boundary(self):
        sigma, name = load_sigma_bucket(5)
        assert sigma == approx(0.2662, abs=1e-4)
        assert "Night" in name

    def test_load_morning_boundary(self):
        sigma, name = load_sigma_bucket(6)
        assert sigma == approx(0.4800, abs=1e-4)
        assert "Morning" in name

    def test_load_afternoon_boundary(self):
        sigma, name = load_sigma_bucket(12)
        assert sigma == approx(0.5114, abs=1e-4)
        assert "Afternoon" in name

    def test_load_evening_boundary(self):
        sigma, name = load_sigma_bucket(18)
        assert sigma == approx(0.6075, abs=1e-4)
        assert "Evening" in name
