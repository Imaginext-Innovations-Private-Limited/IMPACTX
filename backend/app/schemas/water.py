
from pydantic import BaseModel, Field
from typing import Optional


class WaterQualityReading(BaseModel):
    lake_name: str = Field(min_length=2, max_length=150)
    ph: float = Field(ge=0, le=14)
    turbidity: float = Field(ge=0)
    dissolved_oxygen: float = Field(ge=0)
    temperature: float = Field(ge=-10, le=100)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
