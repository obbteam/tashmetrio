from dishka_faststream import FromDishka
from src.adapters.common.events.dependencies import broker
from src.adapters.driving.forConsumingTrainUpdates.models.train_position_changed_event import (
    TrainPositionChangedEvent,
)
from src.core.common.exceptions import BrokerException, ErrorCodeEnum
from src.core.ports.driving.forProcessingTrainUpdates.for_processing_train_updates import (
    ForProcessingTrainUpdates,
)
from src.core.ports.driving.forProcessingTrainUpdates.models.train_position import (
    TrainPosition,
)
from src.settings import BrokerTopic


@broker.subscriber(BrokerTopic.TRAINS_POSITIONS, group_id="gateway-trains-consumer", auto_offset_reset="latest")
async def handler(
    event: TrainPositionChangedEvent,
    for_processing_train_updates: FromDishka[ForProcessingTrainUpdates],
) -> None:
    try:
        await for_processing_train_updates.process(
            train_position=TrainPosition(
                trip_id=event.event_data.trip_id,
                train_id=event.event_data.train_id,
                line_id=event.event_data.line_id,
                current_segment_id=event.event_data.current_segment_id,
                progress_pct=event.event_data.progress_pct,
                position=event.event_data.position,
                trip_status=event.event_data.trip_status,
                is_finished=event.event_data.is_finished,
                emitted_at=event.emitted_at,
            )
        )
    except BrokerException as exc:
        raise BrokerException(
            error_code=ErrorCodeEnum.BROKER_NOT_PROCESSED_EVENT,
            data={
                "topic": event.get_event_topic(),
                "event_type": event.get_event_type(),
                "event_pk": str(event.event_pk),
                "cause": str(exc),
            },
        ) from exc
