# Energy Router — /energy (Daily, Monthly, User Solar Estimates & Cost Tracking)
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.models.schemas import (
    SolarEstimateRequest,
    SolarEstimateResponse,
    DailyEnergyResponse,
    MonthlyEnergyResponse,
    EnergySummaryResponse,
)
from app.services import energy_accounting

router = APIRouter(prefix="/energy", tags=["energy"])


@router.get("/summary", response_model=EnergySummaryResponse)
async def get_energy_summary(
    month: Optional[str] = Query(None, description="Month in 'YYYY-MM' format"),
    date: Optional[str] = Query(None, description="Date in 'YYYY-MM-DD' format"),
    tariff_rate: float = Query(7.50, ge=0.0),
):
    """Return consolidated daily + monthly persistent energy accounting and savings.
    
    If month is omitted and the current month has 0 recorded days, automatically
    provides the latest active billing month to prevent blank/zero views on month rollover.
    """
    dhaka_now = energy_accounting.get_dhaka_now()
    current_month_str = dhaka_now.strftime("%Y-%m")
    current_today_str = dhaka_now.strftime("%Y-%m-%d")

    available_months = energy_accounting.get_available_accounting_months()
    if not available_months:
        available_months = [current_month_str]

    is_fallback = False
    if month:
        target_month_str = month
        month_data = energy_accounting.get_monthly_energy_accounting(target_month_str, tariff_rate=tariff_rate)
    else:
        # Check if current month has any recorded packets or estimates
        current_month_data = energy_accounting.get_monthly_energy_accounting(current_month_str, tariff_rate=tariff_rate)
        if current_month_data["days_recorded"] > 0:
            target_month_str = current_month_str
            month_data = current_month_data
        else:
            # Fallback to the latest month with telemetry/estimates
            latest_with_data = next((m for m in available_months if m != current_month_str), None)
            if latest_with_data:
                target_month_str = latest_with_data
                is_fallback = True
                month_data = energy_accounting.get_monthly_energy_accounting(target_month_str, tariff_rate=tariff_rate)
            else:
                target_month_str = current_month_str
                month_data = current_month_data

    # Determine which date to show in the daily breakdown card:
    if date:
        target_date_str = date
    elif target_month_str == current_month_str:
        target_date_str = current_today_str
    else:
        # When viewing a historical month, default to the latest recorded day in that month
        if month_data["daily_records"]:
            target_date_str = month_data["daily_records"][0]["date"]
        else:
            target_date_str = f"{target_month_str}-01"

    today_data = next((r for r in month_data["daily_records"] if r["date"] == target_date_str), None)
    if not today_data:
        today_data = {
            "date": target_date_str,
            "timezone": month_data["timezone"],
            "total_energy_kwh": 0.0,
            "user_solar_kwh": 0.0,
            "solar_utilized_kwh": 0.0,
            "has_user_solar_estimate": False,
            "estimated_savings_bdt": 0.0,
            "estimated_remaining_kwh": 0.0,
            "excess_solar_kwh": 0.0,
            "tariff_rate": tariff_rate,
            "reading_count": 0,
            "first_packet_ts": None,
            "last_packet_ts": None,
            "notes": "",
        }

    return EnergySummaryResponse(
        date=target_date_str,
        month=target_month_str,
        timezone=today_data["timezone"],
        today=DailyEnergyResponse(**today_data),
        this_month=MonthlyEnergyResponse(**month_data),
        tariff_rate=tariff_rate,
        tariff_currency="BDT",
        available_months=available_months,
        is_latest_active_month=is_fallback,
    )



@router.get("/daily", response_model=DailyEnergyResponse)
async def get_daily_energy(
    date: Optional[str] = Query(None, description="Date in 'YYYY-MM-DD' format"),
    tariff_rate: float = Query(7.50, ge=0.0),
):
    """Return persistent energy accounting for a specific calendar date in Asia/Dhaka."""
    try:
        data = energy_accounting.get_daily_energy_accounting(date, tariff_rate=tariff_rate)
        return DailyEnergyResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/monthly", response_model=MonthlyEnergyResponse)
async def get_monthly_energy(
    month: Optional[str] = Query(None, description="Month in 'YYYY-MM' format"),
    tariff_rate: float = Query(7.50, ge=0.0),
):
    """Return aggregated energy accounting and daily breakdown for a month."""
    try:
        data = energy_accounting.get_monthly_energy_accounting(month, tariff_rate=tariff_rate)
        return MonthlyEnergyResponse(**data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/solar-estimate", response_model=SolarEstimateResponse)
async def set_user_solar_estimate(req: SolarEstimateRequest):
    """Save or update user-entered solar contribution estimate for a calendar date."""
    try:
        res = energy_accounting.save_user_solar_estimate(
            date_str=req.date,
            estimated_solar_kwh=req.estimated_solar_kwh,
            notes=req.notes or "",
        )
        return SolarEstimateResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to persist estimate: {str(e)}")
