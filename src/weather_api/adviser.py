from weather_api.models import Advisory, RiskLevel, WeatherSnapshot

THUNDERSTORM_CODES = frozenset({95, 96, 99})


def assess(city: str, snapshot: WeatherSnapshot) -> Advisory:
    return Advisory(city=city, risk=_risk(snapshot), reasons=_reasons(snapshot))


def _risk(snapshot: WeatherSnapshot) -> RiskLevel:
    if (
        snapshot.wind_gust_kmh >= 60
        or snapshot.precipitation_mm >= 5
        or snapshot.weather_code in THUNDERSTORM_CODES
    ):
        return RiskLevel.HIGH
    if snapshot.wind_gust_kmh >= 40 or snapshot.precipitation_mm >= 1:
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _reasons(snapshot: WeatherSnapshot) -> list[str]:
    reasons: list[str] = []
    if snapshot.wind_gust_kmh >= 40:
        reasons.append(f"Wind gusts: {snapshot.wind_gust_kmh:g} km/h")
    if snapshot.precipitation_mm >= 1:
        reasons.append(f"Precipitation: {snapshot.precipitation_mm:g} mm")
    if snapshot.weather_code in THUNDERSTORM_CODES:
        reasons.append(f"Thunderstorm weather code: {snapshot.weather_code}")
    return reasons
