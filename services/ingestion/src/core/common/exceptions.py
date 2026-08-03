from enum import StrEnum, unique
from typing import Any


@unique
class ErrorCodeEnum(StrEnum):
    TIMETABLE_NOT_FOUND = "TIMETABLE_NOT_FOUND"
    TIMETABLE_NOT_UPDATED = "TIMETABLE_NOT_UPDATED"
    
    DATABASE_INTEGRITY_FAILED = "DATABASE_INTEGRITY_FAILED"
    DATABASE_UNKNOWN_ERROR = "DATABASE_UNKNOWN_ERROR"


class LogicalException(Exception):
    def __init__(
        self,
        http_code: int,
        error_code: ErrorCodeEnum,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.http_code = http_code
        self.error_code = error_code
        self.data = data
        self.message = error_code.value

    def __str__(self) -> str:
        return f"{self.http_code}: {self.error_code}"

    def get_debug_data(self) -> dict[str, Any]:
        return {}
