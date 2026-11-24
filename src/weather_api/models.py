from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class Coordinates(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class WeatherSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    temperature_c: float
    wind_speed_kmh: float = Field(ge=0)
    wind_gust_kmh: float = Field(ge=0)
    precipitation_mm: float = Field(ge=0)
    weather_code: int


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class Advisory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    city: str
    risk: RiskLevel
    reasons: list[str]
x = 1  # noqa
