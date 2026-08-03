from abc import ABC, abstractmethod
from types import TracebackType
from typing import Optional

from src.adapters.common.database_session import (
    IDatabaseSession,
    get_database_session,
)


class IUnitOfWork(ABC):
    @abstractmethod
    async def __aenter__(self) -> "IUnitOfWork": ...

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None: ...

    @abstractmethod
    async def commit(self) -> None: ...

    @abstractmethod
    async def rollback(self) -> None: ...

    @abstractmethod
    def get_session(self) -> IDatabaseSession: ...


class UnitOfWork(IUnitOfWork):
    def __init__(self, session: IDatabaseSession) -> None:
        self._session = session

    async def __aenter__(self) -> "UnitOfWork":
        await self._session.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        if exc_type is not None:
            await self._session.rollback()
        await self._session.__aexit__(exc_type, exc_val, exc_tb)

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    def get_session(self) -> IDatabaseSession:
        return self._session


def get_unit_of_work() -> IUnitOfWork:
    return UnitOfWork(session=get_database_session())


__all__ = [
    "IUnitOfWork",
    "UnitOfWork",
    "get_unit_of_work",
]
