import asyncio
from dataclasses import dataclass

import httpx

from weather_api.adviser import assess
from weather_api.client import WeatherClientError, fetch_weather, geocode
from weather_api.models import Advisory

CITY_WIDTH = 20
RISK_WIDTH = 8


@dataclass(frozen=True)
class CityResult:
    city: str
    advisory: Advisory | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        if (self.advisory is None) == (self.error is None):
            raise ValueError("Exactly one of advisory or error must be set")


async def advise_city(client: httpx.AsyncClient, city: str) -> CityResult:
    try:
        coordinates = await geocode(client, city)
        snapshot = await fetch_weather(client, coordinates)
        return CityResult(city=city, advisory=assess(city, snapshot))
    except WeatherClientError as error:
        return CityResult(city=city, error=str(error))


async def advise_cities(
    client: httpx.AsyncClient, cities: list[str]
) -> list[CityResult]:
    return list(await asyncio.gather(*(advise_city(client, city) for city in cities)))


def format_report(results: list[CityResult]) -> str:
    rows = [f"{'CITY':<{CITY_WIDTH}} {'RISK':<{RISK_WIDTH}} DETAILS"]
    for result in results:
        if result.advisory is None:
            details = f"ERROR: {result.error}"
            risk = "-"
        else:
            details = "; ".join(result.advisory.reasons) or "-"
            risk = result.advisory.risk.value
        rows.append(f"{result.city:<{CITY_WIDTH}} {risk:<{RISK_WIDTH}} {details}")
    return "\n".join(rows)
