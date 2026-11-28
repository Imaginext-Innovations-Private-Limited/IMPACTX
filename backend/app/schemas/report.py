
from pydantic import BaseModel, Field
from typing import Optional


class PollutionReport(BaseModel):

    lake_name: str = Field(
        min_length=2,
        max_length=150
    )

    description: str = Field(
        min_length=5,
        max_length=1000
    )

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    pollution_type: Optional[str] = None

    photo_url: Optional[str] = None

    # Link to the MongoDB AI detection record
    detection_id: Optional[str] = None
