from enum import StrEnum


class TripStatus(StrEnum):
    ON_TIME = "ON TIME"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
