from collections.abc import Mapping

import httpx
from pydantic import ValidationError

from weather_api.models import Coordinates, WeatherSnapshot

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT_SECONDS = 10.0


class WeatherClientError(Exception):
    """Base exception for weather service failures."""


class CityNotFoundError(WeatherClientError):
    """Raised when the geocoding service cannot find a city."""


class NetworkError(WeatherClientError):
    """Raised when a request to the weather service fails."""


class BadResponseError(WeatherClientError):
    """Raised when the weather service returns an unusable response."""


async def geocode(client: httpx.AsyncClient, city: str) -> Coordinates:
    payload = await _get_json(client, GEOCODING_URL, {"name": city, "count": 1})
    response_data = _mapping(payload)
    results = response_data.get("results")
    if not isinstance(results, list) or not results:
        raise CityNotFoundError(f"City not found: {city}")

    result = _mapping(results[0])
    try:
        return Coordinates.model_validate(
            {
                "latitude": _required(result, "latitude"),
                "longitude": _required(result, "longitude"),
            }
        )
    except ValidationError as error:
        raise BadResponseError("Invalid geocoding response") from error


async def fetch_weather(
    client: httpx.AsyncClient, coords: Coordinates
) -> WeatherSnapshot:
    payload = await _get_json(
        client,
        FORECAST_URL,
        {
            "latitude": coords.latitude,
            "longitude": coords.longitude,
            "current": (
                "temperature_2m,wind_speed_10m,wind_gusts_10m,"
                "precipitation,weather_code"
            ),
        },
    )
    response_data = _mapping(payload)
    current = _mapping(_required(response_data, "current"))
    try:
        return WeatherSnapshot.model_validate(
            {
                "temperature_c": _required(current, "temperature_2m"),
                "wind_speed_kmh": _required(current, "wind_speed_10m"),
                "wind_gust_kmh": _required(current, "wind_gusts_10m"),
                "precipitation_mm": _required(current, "precipitation"),
                "weather_code": _required(current, "weather_code"),
            }
        )
    except ValidationError as error:
        raise BadResponseError("Invalid forecast response") from error


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: Mapping[str, str | int | float | bool | None],
) -> object:
    try:
        response = await client.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as error:
        raise BadResponseError("Weather service returned an error status") from error
    except httpx.HTTPError as error:
        raise NetworkError("Weather service request failed") from error
    except ValueError as error:
        raise BadResponseError("Weather service returned invalid JSON") from error


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise BadResponseError("Weather service returned an invalid JSON structure")
    return value


def _required(data: Mapping[str, object], key: str) -> object:
    try:
        return data[key]
    except KeyError as error:
        raise BadResponseError(f"Weather service response is missing {key}") from error
