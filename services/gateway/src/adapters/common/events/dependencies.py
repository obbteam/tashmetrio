from faststream import FastStream
from faststream.kafka import KafkaBroker

from src.settings import settings

broker = KafkaBroker(bootstrap_servers=settings.KAFKA.BOOTSTRAP_SERVERS)
app = FastStream(broker)


def get_broker() -> KafkaBroker:
    return broker
