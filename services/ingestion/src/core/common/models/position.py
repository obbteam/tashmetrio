from pydantic import BaseModel


class Position(BaseModel):
    latitude: float
    longitude: float

    @property
    def to_ewkt(self) -> str:
        return str(f"SRID=4326;POINT({self.longitude} {self.latitude})")
