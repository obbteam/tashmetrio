import asyncio
import logging

from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError

from src.settings import BrokerTopic

logging.basicConfig(level=logging.INFO, format="[%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)


BOOTSTRAP_SERVERS = "localhost:9094"
HOUR_MS = 3_600_000

TOPICS = [
    NewTopic(
        name=BrokerTopic.TRAINS_POSITIONS,
        num_partitions=3,
        replication_factor=1,
        topic_configs={"retention.ms": str(1 * HOUR_MS)},
    ),
    NewTopic(
        name=BrokerTopic.NETWORK_ALERTS,
        num_partitions=1,
        replication_factor=1,
        topic_configs={"retention.ms": str(24 * HOUR_MS)},
    ),
]


async def create_topics() -> None:
    admin = AIOKafkaAdminClient(bootstrap_servers=BOOTSTRAP_SERVERS)
    await admin.start()
    try:
        existing = await admin.list_topics()
        to_create = [t for t in TOPICS if t.name not in existing]
        already_present = [t.name for t in TOPICS if t.name in existing]

        for name in already_present:
            logger.info(
                "Skipping %s — already exists (no config reconciliation performed)",
                name,
            )

        if not to_create:
            logger.info("Nothing to create.")
            return

        try:
            await admin.create_topics(to_create)
        except TopicAlreadyExistsError:
            pass

        for t in to_create:
            retention_h = int(t.topic_configs["retention.ms"]) // HOUR_MS
            logger.info(
                "Created %s (partitions=%d, replication=%d, retention=%dh)",
                t.name,
                t.num_partitions,
                t.replication_factor,
                retention_h,
            )

    finally:
        await admin.close()


if __name__ == "__main__":
    asyncio.run(main=create_topics())
