
from src.adapters.common.events.event import Event


class IEventPublisher:
    async def publish(self, event: Event) -> None:
        raise NotImplementedError()
