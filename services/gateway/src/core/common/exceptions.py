from enum import StrEnum, unique
from typing import Any


@unique
class ErrorCodeEnum(StrEnum):
    DATABASE_INTEGRITY_FAILED = "DATABASE_INTEGRITY_FAILED"
    DATABASE_UNKNOWN_ERROR = "DATABASE_UNKNOWN_ERROR"

    TRIP_NOT_FOUND = "TRIP_NOT_FOUND"

    BROKER_NOT_PROCESSED_EVENT = "BROKER_NOT_PROCESSED_EVENT"
    
    REDIS_UNKNOWN_ERROR = "REDIS_UNKNOWN_ERROR"


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
        return f"{self.http_code}: {self.error_code}. {self.data}"

    def get_debug_data(self) -> dict[str, Any]:
        return self.data or {}


class BrokerException(LogicalException):
    def __init__(
        self,
        error_code: ErrorCodeEnum = ErrorCodeEnum.BROKER_NOT_PROCESSED_EVENT,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.data = data
        
        super().__init__(
            http_code=503, error_code=error_code, data=data
        )


class RedisException(LogicalException):
    def __init__(
        self,
        error_code: ErrorCodeEnum = ErrorCodeEnum.REDIS_UNKNOWN_ERROR,
        data: dict[str, Any] | None = None,
    ) -> None:
        self.data = data
        
        super().__init__(
            http_code=503, error_code=error_code, data=data
        )
