import argparse
import asyncio

import httpx

from weather_api.service import CityResult, advise_cities, format_report, has_errors


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Get flight risk advisories for one or more cities."
    )
    parser.add_argument("cities", nargs="+", help="City names to assess")
    return parser.parse_args()


async def _advise(cities: list[str]) -> list[CityResult]:
    async with httpx.AsyncClient() as client:
        return await advise_cities(client, cities)


def main() -> int:
    arguments = _parse_args()
    results = asyncio.run(_advise(arguments.cities))
    print(format_report(results))
    return 1 if has_errors(results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
