#!/usr/bin/env python3
"""Mathematical verification of ESP32 electrical measurement algorithms (§6.1).

Scope & Evidence Classification:
  [PARTIALLY VERIFIED] — Mathematical simulation verifying the true-RMS, synchronized
  instantaneous power, power factor, sampling window sample counts, and ACS712 voltage
  divider scaling algorithms matching `electricity_meter.cpp`.

Tests:
1. Pure resistive load (PF = 1.0) -> True Real Power == Apparent Power
2. Inductive load (60° phase lag, PF = 0.5) -> True Real Power == 0.5 * Apparent Power
3. ACS712 10k/15k resistor divider scaling (0.600 ratio) voltage ceiling safety
4. Sampling burst sample count verification (200ms window across 1.5 kHz and 2.0 kHz)
"""

import numpy as np
import pytest

def simulate_ac_burst(
    freq_hz=50.0,
    v_rms_true=220.0,
    i_rms_true=5.0,
    phase_deg=0.0,
    sampling_rate_hz=2000.0,
    window_ms=200.0,
    divider_ratio=0.600,
    noise_std=0.0
):
    """Simulate ADC samples and compute power per firmware algorithms matching electricity_meter.cpp."""
    duration_s = window_ms / 1000.0
    n_samples = int(duration_s * sampling_rate_hz)
    t = np.linspace(0, duration_s, n_samples, endpoint=False)

    # True waveforms
    v_peak = v_rms_true * np.sqrt(2)
    i_peak = i_rms_true * np.sqrt(2)
    phase_rad = np.radians(phase_deg)

    v_true = v_peak * np.sin(2 * np.pi * freq_hz * t)
    i_true = i_peak * np.sin(2 * np.pi * freq_hz * t - phase_rad)

    # Simulated ADC with zero-offsets
    v_cal_factor = 0.1785
    sensitivity = 0.100  # 100 mV/A (ACS712-20A)
    adc_to_volts = 3.30 / 4095.0
    current_scale = adc_to_volts / (divider_ratio * sensitivity)

    # Raw ADC simulated counts
    v_zero = 2539.65
    i_zero = 2537.18
    raw_v = (v_true / v_cal_factor) + v_zero + np.random.normal(0, noise_std, n_samples)
    raw_i = (i_true / current_scale) + i_zero + np.random.normal(0, noise_std, n_samples)

    # Firmware reconstruction:
    v_inst = (raw_v - v_zero) * v_cal_factor
    i_inst = (raw_i - i_zero) * current_scale

    # Algorithms:
    v_rms_calc = np.sqrt(np.mean(v_inst ** 2))
    i_rms_calc = np.sqrt(np.mean(i_inst ** 2))
    p_real_calc = np.mean(v_inst * i_inst)
    s_apparent_calc = v_rms_calc * i_rms_calc
    pf_calc = p_real_calc / s_apparent_calc if s_apparent_calc > 0 else 1.0

    return {
        "v_rms": v_rms_calc,
        "i_rms": i_rms_calc,
        "p_real": p_real_calc,
        "s_apparent": s_apparent_calc,
        "power_factor": pf_calc,
        "samples": n_samples,
    }


def test_pure_resistive_load():
    """Resistive load (PF=1.0, 220V, 5A -> 1100W)."""
    res = simulate_ac_burst(v_rms_true=220.0, i_rms_true=5.0, phase_deg=0.0)
    assert pytest.approx(220.0, rel=1e-3) == res["v_rms"]
    assert pytest.approx(5.0, rel=1e-3) == res["i_rms"]
    assert pytest.approx(1100.0, rel=1e-3) == res["p_real"]
    assert pytest.approx(1100.0, rel=1e-3) == res["s_apparent"]
    assert pytest.approx(1.0, rel=1e-3) == res["power_factor"]


def test_inductive_load_phase_lag():
    """Inductive load (60 deg lag -> PF=cos(60)=0.5, Real=550W, Apparent=1100VA)."""
    res = simulate_ac_burst(v_rms_true=220.0, i_rms_true=5.0, phase_deg=60.0)
    assert pytest.approx(220.0, rel=1e-3) == res["v_rms"]
    assert pytest.approx(5.0, rel=1e-3) == res["i_rms"]
    assert pytest.approx(550.0, rel=1e-2) == res["p_real"]
    assert pytest.approx(1100.0, rel=1e-2) == res["s_apparent"]
    assert pytest.approx(0.5, rel=1e-2) == res["power_factor"]


def test_acs712_resistor_divider_voltage_safety():
    """Verify that 10k/15k divider limits maximum 5.0V ACS712 output to <= 3.0V at ESP32 ADC pin."""
    r1_series = 10000.0  # 10k
    r2_gnd = 15000.0     # 15k
    divider_ratio = r2_gnd / (r1_series + r2_gnd)
    assert pytest.approx(0.600, rel=1e-5) == divider_ratio

    v_sensor_max = 5.00  # Max possible saturation output of 5V ACS712
    v_adc_pin_max = v_sensor_max * divider_ratio
    assert v_adc_pin_max == 3.00
    assert v_adc_pin_max < 3.30, "ADC pin voltage must not exceed 3.3V logic level"


def test_sampling_rate_and_sample_count():
    """Verify sample counts across 200ms burst window for both 1.5 kHz and 2.0 kHz achieved rates."""
    res_2khz = simulate_ac_burst(window_ms=200.0, sampling_rate_hz=2000.0)
    assert res_2khz["samples"] == 400

    res_1_5khz = simulate_ac_burst(window_ms=200.0, sampling_rate_hz=1500.0)
    assert res_1_5khz["samples"] == 300


if __name__ == "__main__":
    print("Running firmware mathematical simulation tests...")
    test_pure_resistive_load()
    print("  ✓ Pure resistive load (PF=1.0, 1100W) passed.")
    test_inductive_load_phase_lag()
    print("  ✓ Inductive load (PF=0.5, 550W / 1100VA) passed.")
    test_acs712_resistor_divider_voltage_safety()
    print("  ✓ ACS712 10k/15k resistor divider safety (max 3.0V <= 3.3V) passed.")
    test_sampling_rate_and_sample_count()
    print("  ✓ Sampling burst rates (300 @ 1.5kHz, 400 @ 2.0kHz across 200ms) passed.")
    print("All firmware mathematical verification tests passed successfully!")
