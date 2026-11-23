import httpx
import pytest

from weather_api.client import (
    BadResponseError,
    CityNotFoundError,
    NetworkError,
    fetch_weather,
    geocode,
)
from weather_api.models import Coordinates


@pytest.mark.asyncio
async def test_geocode_returns_coordinates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["name"] == "Dubai"
        assert request.url.params["count"] == "1"
        return httpx.Response(
            200,
            json={
                "results": [
                    {"name": "Dubai", "latitude": 25.2048, "longitude": 55.2708}
                ]
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await geocode(client, "Dubai") == Coordinates(
            latitude=25.2048, longitude=55.2708
        )


@pytest.mark.asyncio
async def test_fetch_weather_returns_snapshot() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["current"] == (
            "temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation,weather_code"
        )
        return httpx.Response(
            200,
            json={
                "current": {
                    "temperature_2m": 30.5,
                    "wind_speed_10m": 15,
                    "wind_gusts_10m": 25,
                    "precipitation": 0,
                    "weather_code": 3,
                }
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        snapshot = await fetch_weather(client, Coordinates(latitude=25, longitude=55))

    assert snapshot.temperature_c == 30.5
    assert snapshot.wind_speed_kmh == 15
    assert snapshot.wind_gust_kmh == 25
    assert snapshot.precipitation_mm == 0
    assert snapshot.weather_code == 3


@pytest.mark.asyncio
async def test_geocode_raises_for_missing_city() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(CityNotFoundError):
            await geocode(client, "Nowhere")


@pytest.mark.asyncio
async def test_client_converts_timeout_to_network_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Timed out", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(NetworkError):
            await geocode(client, "Dubai")


@pytest.mark.asyncio
async def test_client_converts_error_status_to_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BadResponseError):
            await geocode(client, "Dubai")


@pytest.mark.asyncio
async def test_client_converts_malformed_json_to_bad_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(BadResponseError):
            await geocode(client, "Dubai")
