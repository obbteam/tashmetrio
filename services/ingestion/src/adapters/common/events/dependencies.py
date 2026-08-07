from faststream import FastStream
from faststream.kafka import KafkaBroker

from src.adapters.common.events.event_publisher import IEventPublisher
from src.adapters.common.events.kafka_publisher import KafkaEventPublisher
from src.settings import settings

broker = KafkaBroker(bootstrap_servers=settings.KAFKA.BOOTSTRAP_SERVERS)
app = FastStream(broker)


def get_broker_producer() -> KafkaBroker:
    return broker


def get_kafka_event_publisher() -> IEventPublisher:
    return KafkaEventPublisher(broker=get_broker_producer())
