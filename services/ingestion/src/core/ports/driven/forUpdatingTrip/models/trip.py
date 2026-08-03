from uuid import UUID

from pydantic import Base


class Trip(Base):
    trip_id: UUID
