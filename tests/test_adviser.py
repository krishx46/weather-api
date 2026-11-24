import pytest
from hypothesis import given, strategies as st

from weather_api.adviser import assess
from weather_api.models import RiskLevel, WeatherSnapshot


def _snapshot(**overrides: float | int) -> WeatherSnapshot:
    values: dict[str, float | int] = {
        "temperature_c": 20,
        "wind_speed_kmh": 10,
        "wind_gust_kmh": 10,
        "precipitation_mm": 0,
        "weather_code": 3,
    }
    values.update(overrides)
    return WeatherSnapshot(**values)


@pytest.mark.parametrize(
    ("gust", "risk"),
    [
        (39.9, RiskLevel.LOW),
        (40, RiskLevel.MEDIUM),
        (59.9, RiskLevel.MEDIUM),
        (60, RiskLevel.HIGH),
    ],
)
def test_assess_gust_boundaries(gust: float, risk: RiskLevel) -> None:
    assert assess("Dubai", _snapshot(wind_gust_kmh=gust)).risk is risk


@pytest.mark.parametrize(
    ("precipitation", "risk"),
    [
        (0.9, RiskLevel.LOW),
        (1, RiskLevel.MEDIUM),
        (4.9, RiskLevel.MEDIUM),
        (5, RiskLevel.HIGH),
    ],
)
def test_assess_precipitation_boundaries(precipitation: float, risk: RiskLevel) -> None:
    assert assess("Dubai", _snapshot(precipitation_mm=precipitation)).risk is risk


@pytest.mark.parametrize("weather_code", [95, 96, 99])
def test_assess_thunderstorms_are_high_risk(weather_code: int) -> None:
    assert assess("Dubai", _snapshot(weather_code=weather_code)).risk is RiskLevel.HIGH


def test_assess_calm_weather_is_low_risk() -> None:
    advisory = assess("Dubai", _snapshot(weather_code=3))

    assert advisory.risk is RiskLevel.LOW
    assert advisory.reasons == []


@pytest.mark.parametrize(
    ("overrides", "risk", "reasons"),
    [
        ({"wind_gust_kmh": 40}, RiskLevel.MEDIUM, ["Wind gusts: 40 km/h"]),
        ({"wind_gust_kmh": 39.9}, RiskLevel.LOW, []),
        (
            {"precipitation_mm": 1},
            RiskLevel.MEDIUM,
            ["Precipitation: 1 mm"],
        ),
        ({"precipitation_mm": 0.9}, RiskLevel.LOW, []),
        (
            {"weather_code": 95},
            RiskLevel.HIGH,
            ["Thunderstorm weather code: 95"],
        ),
    ],
)
def test_assess_reasons_at_thresholds(
    overrides: dict[str, float | int], risk: RiskLevel, reasons: list[str]
) -> None:
    advisory = assess("Dubai", _snapshot(**overrides))

    assert advisory.risk is risk
    assert advisory.reasons == reasons


@given(
    temperature_c=st.floats(allow_nan=False, allow_infinity=False),
    wind_speed_kmh=st.floats(min_value=0, allow_nan=False, allow_infinity=False),
    wind_gust_kmh=st.floats(min_value=0, allow_nan=False, allow_infinity=False),
    precipitation_mm=st.floats(min_value=0, allow_nan=False, allow_infinity=False),
    weather_code=st.integers(),
)
def test_assess_handles_every_valid_snapshot(
    temperature_c: float,
    wind_speed_kmh: float,
    wind_gust_kmh: float,
    precipitation_mm: float,
    weather_code: int,
) -> None:
    snapshot = WeatherSnapshot(
        temperature_c=temperature_c,
        wind_speed_kmh=wind_speed_kmh,
        wind_gust_kmh=wind_gust_kmh,
        precipitation_mm=precipitation_mm,
        weather_code=weather_code,
    )

    advisory = assess("Dubai", snapshot)

    assert advisory.risk in RiskLevel
    assert (advisory.reasons == []) is (advisory.risk is RiskLevel.LOW)
