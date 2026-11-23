from weather_api.models import Advisory, RiskLevel, WeatherSnapshot

THUNDERSTORM_CODES = frozenset({95, 96, 99})
HIGH_RISK_GUST_KMH = 60
MEDIUM_RISK_GUST_KMH = 40
HIGH_RISK_PRECIPITATION_MM = 5
MEDIUM_RISK_PRECIPITATION_MM = 1


def assess(city: str, snapshot: WeatherSnapshot) -> Advisory:
    return Advisory(city=city, risk=_risk(snapshot), reasons=_reasons(snapshot))


def _risk(snapshot: WeatherSnapshot) -> RiskLevel:
    if (
        snapshot.wind_gust_kmh >= HIGH_RISK_GUST_KMH
        or snapshot.precipitation_mm >= HIGH_RISK_PRECIPITATION_MM
        or snapshot.weather_code in THUNDERSTORM_CODES
    ):
        return RiskLevel.HIGH
    if (
        snapshot.wind_gust_kmh >= MEDIUM_RISK_GUST_KMH
        or snapshot.precipitation_mm >= MEDIUM_RISK_PRECIPITATION_MM
    ):
        return RiskLevel.MEDIUM
    return RiskLevel.LOW


def _reasons(snapshot: WeatherSnapshot) -> list[str]:
    reasons: list[str] = []
    if snapshot.wind_gust_kmh >= MEDIUM_RISK_GUST_KMH:
        reasons.append(f"Wind gusts: {snapshot.wind_gust_kmh:g} km/h")
    if snapshot.precipitation_mm >= MEDIUM_RISK_PRECIPITATION_MM:
        reasons.append(f"Precipitation: {snapshot.precipitation_mm:g} mm")
    if snapshot.weather_code in THUNDERSTORM_CODES:
        reasons.append(f"Thunderstorm weather code: {snapshot.weather_code}")
    return reasons
