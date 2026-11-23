import httpx
import pytest

from weather_api.models import Advisory, RiskLevel
from weather_api.service import CityResult, advise_cities, format_report


@pytest.mark.asyncio
async def test_advise_cities_returns_successes_in_input_order() -> None:
    cities = {
        "Dubai": (25.2, 55.3, 3),
        "London": (51.5, -0.1, 95),
        "Tokyo": (35.7, 139.7, 3),
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geocoding-api.open-meteo.com":
            city = request.url.params["name"]
            latitude, longitude, _ = cities[city]
            return httpx.Response(
                200,
                json={
                    "results": [
                        {"name": city, "latitude": latitude, "longitude": longitude}
                    ]
                },
            )
        weather_code = next(
            code
            for latitude, _, code in cities.values()
            if str(latitude) == request.url.params["latitude"]
        )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 20,
                    "wind_speed_10m": 10,
                    "wind_gusts_10m": 10,
                    "precipitation": 0,
                    "weather_code": weather_code,
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await advise_cities(client, ["Tokyo", "Dubai", "London"])

    assert [result.city for result in results] == ["Tokyo", "Dubai", "London"]
    assert [result.advisory.risk for result in results if result.advisory] == [
        RiskLevel.LOW,
        RiskLevel.LOW,
        RiskLevel.HIGH,
    ]


@pytest.mark.asyncio
async def test_advise_cities_keeps_successes_when_some_cities_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("name") == "Missing":
            return httpx.Response(200, json={"results": []})
        if request.url.params.get("name") == "Offline":
            raise httpx.ConnectError("Unavailable", request=request)
        if request.url.host == "geocoding-api.open-meteo.com":
            return httpx.Response(
                200,
                json={"results": [{"name": "Dubai", "latitude": 25, "longitude": 55}]},
            )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 20,
                    "wind_speed_10m": 10,
                    "wind_gusts_10m": 10,
                    "precipitation": 0,
                    "weather_code": 3,
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await advise_cities(client, ["Dubai", "Missing", "Offline"])

    assert results[0].advisory is not None
    assert results[1].error == "City not found: Missing"
    assert results[2].error == "Weather service request failed"


def test_format_report_for_low_risk_city() -> None:
    report = format_report(
        [
            CityResult(
                city="Dubai",
                advisory=Advisory(city="Dubai", risk=RiskLevel.LOW, reasons=[]),
            )
        ]
    )

    assert (
        report
        == "CITY                 RISK     DETAILS\nDubai                LOW      -"
    )


def test_format_report_for_high_risk_city_with_multiple_reasons() -> None:
    report = format_report(
        [
            CityResult(
                city="London",
                advisory=Advisory(
                    city="London",
                    risk=RiskLevel.HIGH,
                    reasons=["Wind gusts: 60 km/h", "Precipitation: 5 mm"],
                ),
            )
        ]
    )

    assert report == (
        "CITY                 RISK     DETAILS\n"
        "London               HIGH     Wind gusts: 60 km/h; Precipitation: 5 mm"
    )


def test_format_report_for_error_row() -> None:
    report = format_report(
        [CityResult(city="Missing", error="City not found: Missing")]
    )

    assert report == (
        "CITY                 RISK     DETAILS\n"
        "Missing              -        ERROR: City not found: Missing"
    )


def test_format_report_for_mixed_results() -> None:
    report = format_report(
        [
            CityResult(
                city="Dubai",
                advisory=Advisory(city="Dubai", risk=RiskLevel.LOW, reasons=[]),
            ),
            CityResult(city="Offline", error="Weather service request failed"),
        ]
    )

    assert report == (
        "CITY                 RISK     DETAILS\n"
        "Dubai                LOW      -\n"
        "Offline              -        ERROR: Weather service request failed"
    )
