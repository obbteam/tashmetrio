from abc import abstractmethod
from types import TracebackType
from typing import Any, Optional

from sqlalchemy import Result
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.sql import Executable

from src.core.common.exceptions import ErrorCodeEnum, LogicalException
from src.settings import settings


class IDatabaseSession:
    @abstractmethod
    def add(self, instance: Any) -> None: ...

    @abstractmethod
    def add_all(self, instances: list[Any]) -> None: ...

    @abstractmethod
    async def delete(self, instance: Any) -> None: ...

    @abstractmethod
    async def execute(
        self,
        statement: Executable,
        params: dict[str, Any] | None = None,
    ) -> Result: ...

    @abstractmethod
    async def scalar(self, statement: Executable) -> Any: ...

    @abstractmethod
    async def flush(self) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    async def refresh(self, instance: Any) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    async def __aenter__(self) -> "IDatabaseSession": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...


class SQLAlchemyDatabaseSession(AsyncSession, IDatabaseSession):
    async def execute(self, *args: Any, **kwargs: Any) -> Result[Any]:
        try:
            return await super().execute(*args, **kwargs)
        except IntegrityError:
            raise LogicalException(
                http_code=409, error_code=ErrorCodeEnum.DATABASE_INTEGRITY_FAILED
            )
        except DatabaseError:
            raise LogicalException(
                http_code=409, error_code=ErrorCodeEnum.DATABASE_UNKNOWN_ERROR
            )

    async def commit(self) -> None:
        try:
            await super().commit()
        except IntegrityError:
            await self.rollback()
            raise LogicalException(
                http_code=409, error_code=ErrorCodeEnum.DATABASE_INTEGRITY_FAILED
            )
        except DatabaseError:
            await self.rollback()
            raise LogicalException(
                http_code=409, error_code=ErrorCodeEnum.DATABASE_UNKNOWN_ERROR
            )


engine: AsyncEngine = create_async_engine(url=settings.DATABASE_URL)

session_maker = async_sessionmaker(
    bind=engine,
    autocommit=False,
    expire_on_commit=False,
    autoflush=True,
    class_=SQLAlchemyDatabaseSession,
)


def get_database_session() -> IDatabaseSession:
    return session_maker()


__all__ = [
    "get_database_session",
    "IDatabaseSession",
    "SQLAlchemyDatabaseSession",
]
