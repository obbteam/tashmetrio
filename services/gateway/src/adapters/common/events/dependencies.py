from faststream.kafka import KafkaBroker

from src.settings import settings

broker = KafkaBroker(bootstrap_servers=settings.KAFKA.BOOTSTRAP_SERVERS)


def get_broker() -> KafkaBroker:
    return broker
