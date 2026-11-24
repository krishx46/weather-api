import asyncio

import httpx
import pytest

from weather_api.models import Advisory, RiskLevel
from weather_api.service import CityResult, advise_cities, format_report, has_errors


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
    assert results[0].city == "Dubai"
    assert results[0].advisory.risk is RiskLevel.LOW
    assert results[1].error == "City not found: Missing"
    assert results[2].error == "Weather service request failed"


def test_city_result_requires_exactly_one_outcome() -> None:
    advisory = Advisory(city="Dubai", risk=RiskLevel.LOW, reasons=[])

    with pytest.raises(
        ValueError, match=r"^Exactly one of advisory or error must be set$"
    ):
        CityResult(city="Dubai")
    with pytest.raises(
        ValueError, match=r"^Exactly one of advisory or error must be set$"
    ):
        CityResult(city="Dubai", advisory=advisory, error="Unavailable")

    assert CityResult(city="Dubai", advisory=advisory).advisory is advisory
    assert CityResult(city="Dubai", error="Unavailable").error == "Unavailable"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["status", "timeout", "missing_current"])
async def test_forecast_failures_do_not_stop_other_cities(failure: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "geocoding-api.open-meteo.com":
            city = request.url.params["name"]
            latitude = 1 if city == "Failing" else 2
            return httpx.Response(
                200,
                json={
                    "results": [{"name": city, "latitude": latitude, "longitude": 1}]
                },
            )
        if (
            request.url.host == "api.open-meteo.com"
            and request.url.params["latitude"] == "1.0"
        ):
            if failure == "status":
                return httpx.Response(500, request=request)
            if failure == "timeout":
                raise httpx.ConnectTimeout("Timed out", request=request)
            return httpx.Response(200, json={})
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
        results = await advise_cities(client, ["Failing", "Working"])

    assert results[0].advisory is None
    assert results[0].error is not None
    assert results[1].advisory is not None
    assert results[1].error is None


@pytest.mark.asyncio
async def test_advise_cities_does_not_swallow_unexpected_exceptions() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("Unexpected failure")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match="Unexpected failure"):
            await advise_cities(client, ["Dubai"])


@pytest.mark.asyncio
async def test_not_found_city_keeps_its_name_and_formats_an_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        results = await advise_cities(client, ["Missing"])

    assert results[0].city == "Missing"
    assert format_report(results) == (
        "CITY                 RISK     DETAILS\n"
        "Missing              -        ERROR: City not found: Missing"
    )


@pytest.mark.asyncio
async def test_advise_cities_preserves_order_despite_different_completion_times() -> (
    None
):
    async def handler(request: httpx.Request) -> httpx.Response:
        if (
            request.url.host == "geocoding-api.open-meteo.com"
            and request.url.params["name"] == "First"
        ):
            await asyncio.sleep(0.05)
        if request.url.host == "geocoding-api.open-meteo.com":
            city = request.url.params["name"]
            latitude = 1 if city == "First" else 2
            return httpx.Response(
                200,
                json={
                    "results": [{"name": city, "latitude": latitude, "longitude": 1}]
                },
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
        results = await advise_cities(client, ["First", "Second"])

    assert [result.city for result in results] == ["First", "Second"]


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


def test_format_report_for_no_results_has_only_a_header() -> None:
    assert format_report([]) == "CITY                 RISK     DETAILS"


def test_format_report_keeps_long_city_names_in_full() -> None:
    report = format_report(
        [
            CityResult(
                city="VeryLongCityNameBeyondTwenty",
                advisory=Advisory(
                    city="VeryLongCityNameBeyondTwenty",
                    risk=RiskLevel.LOW,
                    reasons=[],
                ),
            )
        ]
    )

    assert report == (
        "CITY                 RISK     DETAILS\nVeryLongCityNameBeyondTwenty LOW      -"
    )


def test_has_errors_returns_false_for_an_empty_list() -> None:
    assert has_errors([]) is False


def test_has_errors_returns_false_for_successful_results() -> None:
    results = [
        CityResult(
            city="Dubai",
            advisory=Advisory(city="Dubai", risk=RiskLevel.LOW, reasons=[]),
        )
    ]

    assert has_errors(results) is False


def test_has_errors_returns_true_for_a_single_error() -> None:
    assert (
        has_errors([CityResult(city="Missing", error="City not found: Missing")])
        is True
    )


def test_has_errors_returns_true_for_mixed_results() -> None:
    results = [
        CityResult(
            city="Dubai",
            advisory=Advisory(city="Dubai", risk=RiskLevel.LOW, reasons=[]),
        ),
        CityResult(city="Missing", error="City not found: Missing"),
    ]

    assert has_errors(results) is True
