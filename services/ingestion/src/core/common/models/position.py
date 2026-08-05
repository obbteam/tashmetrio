from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from pydantic import model_validator

from src.core.common.models.base import BaseModel


class Position(BaseModel):
    latitude: float
    longitude: float

    @model_validator(mode="before")
    @classmethod
    def parse_geom(cls, value):
        if isinstance(value, WKBElement):
            point = to_shape(value)  # shapely Point
            return {"latitude": point.y, "longitude": point.x}
        return value
    
    @property
    def to_ewkt(self) -> str:
        return str(f"SRID=4326;POINT({self.longitude} {self.latitude})")
