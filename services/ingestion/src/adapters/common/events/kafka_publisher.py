from faststream.exceptions import FastStreamException
from faststream.kafka import KafkaBroker

from src.adapters.common.events.event import Event
from src.adapters.common.events.event_publisher import IEventPublisher
from src.core.common.exceptions import BrokerException, ErrorCodeEnum


class KafkaEventPublisher(IEventPublisher):
    def __init__(self, broker: KafkaBroker) -> None:
        self._broker = broker

    async def publish(self, event: Event) -> None:
        payload = {
            "event_pk": str(event.event_pk),
            "event_type": event.get_event_type(),
            "event_version": event.event_version,
            "emitted_at": str(event.emitted_at),
            "event_data": event.event_data.model_dump(mode="json"),
        }

        try:
            await self._broker.publish(
                message=payload,
                topic=str(event.get_event_topic()),
                headers=event.get_headers(),
            )
        except FastStreamException as exc:
            raise BrokerException(
                error_code=ErrorCodeEnum.BROKER_NOT_PUBLISHED_EVENT,
                data={
                    "topic": event.get_event_topic(),
                    "event_type": event.get_event_type(),
                    "event_pk": str(event.event_pk),
                    "cause": str(exc),
                },
            ) from exc
