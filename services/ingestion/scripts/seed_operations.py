#!/usr/bin/env python3
"""
SKETCH -- seed `trains` and `timetable_entries` from the hand-authored fleet
/ schedule config below (LINE_SCHEDULE). Unlike seed_topology.py, there's no
OSM source for any of this at all -- fleet size, headway, and service
window are operator knowledge that has to be filled in by hand.

Must run AFTER seed_topology.py: lines are looked up by the CLEAN name
seed_topology.py wrote to the `lines` table (LINE_PERFORMANCE's keys
there), and this fails loudly if a line isn't found rather than creating
one.

Idempotent via deterministic ids: unlike stations (osm_id) and lines
(name), `trains` and `timetable_entries` have no natural unique constraint
in the schema to upsert against. So each row's primary key is derived with
uuid5(SEED_NAMESPACE, <natural key>) and upserted on that id instead --
re-running this script with the same LINE_SCHEDULE always touches the same
rows rather than duplicating them.

Each train's departures are generated sequentially, alternating direction:
depart, run for DEFAULT_ETA_MINUTES, sit for
DEFAULT_TURNAROUND_BUFFER_MINUTES at whichever terminus it just reached,
then depart the other way -- so a train is never scheduled to leave before
it could plausibly have finished its current run and turned around, and it
never departs FORWARD twice in a row from the same end. Trains on a line
are staggered by headway_minutes at service_start so departures from a
given terminus are still roughly headway apart across the fleet.

Known simplification: DEFAULT_ETA_MINUTES is a flat per-trip constant, not
derived from real line length/speed (same assumption TripService.generate()
already makes -- see trip_service.py). So "leaves enough time" here is only
as accurate as that constant is for a given line; a follow-up can replace
it with a real topology-derived ETA per line. If two generated trips for
the same train still end up overlapping, the `trips` table's EXCLUDE
constraint will reject the second one at trip-generation time (see
TripService.generate() / trip_generator.py) -- that's your signal the
buffer/ETA assumption doesn't hold for that line.

Usage (from services/ingestion, with that service's venv active):
    python scripts/seed_operations.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, time, timedelta
from pathlib import Path

# Make `src` importable regardless of the CWD this is invoked from.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.common.database_session import session_maker
from src.adapters.common.models import DirectionType, Lines, TimetableEntries, Trains
from src.settings import settings

# Arbitrary but fixed -- re-runs must derive the same ids from the same
# natural keys, so this must never change once seeded data exists.
SEED_NAMESPACE = uuid.UUID("a3f1c8e0-6b2d-4e11-9f3a-2c7d8e9b1a00")


class LineSchedule:
    def __init__(
        self,
        train_count: int,
        headway_minutes: int,
        service_start: str,
        service_end: str,
    ):
        self.train_count = train_count
        self.headway_minutes = headway_minutes
        self.service_start = time.fromisoformat(service_start)
        self.service_end = time.fromisoformat(service_end)


# Keyed by the CLEAN line name seed_topology.py writes to the `lines` table.
# TODO: fill in from operator conversations -- fleet size per line, headway,
# first/last departure.
LINE_SCHEDULE: dict[str, LineSchedule] = {
    "Chilanzor line": LineSchedule(
        train_count=2,
        headway_minutes=10,
        service_start="06:00",
        service_end="23:00",
    ),
    "Oʻzbekiston line": LineSchedule(
        train_count=2,
        headway_minutes=10,
        service_start="06:00",
        service_end="23:00",
    ),
    "Yunusobod line": LineSchedule(
        train_count=2,
        headway_minutes=10,
        service_start="06:00",
        service_end="23:00",
    ),
    "Circle line": LineSchedule(
        train_count=2,
        headway_minutes=10,
        service_start="06:00",
        service_end="23:00",
    ),
}


def train_id_for(line_name: str, index: int) -> uuid.UUID:
    return uuid.uuid5(SEED_NAMESPACE, f"train:{line_name}:{index}")


def train_name_for(line_name: str, index: int) -> str:
    return f"{line_name} Train {index + 1}"


def timetable_entry_id_for(
    train_id: uuid.UUID, direction: DirectionType, departure_time: time
) -> uuid.UUID:
    return uuid.uuid5(
        SEED_NAMESPACE,
        f"timetable:{train_id}:{direction.value}:{departure_time.isoformat()}",
    )


def generate_train_legs(
    schedule: LineSchedule, start_offset: timedelta, leg_duration: timedelta
) -> list[tuple[time, DirectionType]]:
    """One train's alternating FORWARD/BACKWARD legs for the day, staggered by
    start_offset off service_start. Each leg is leg_duration long (trip ETA +
    turnaround buffer), so the next departure is never scheduled before the
    train could plausibly have finished its current run and turned around at
    whichever end it's now sitting at."""
    t = datetime.combine(datetime.min, schedule.service_start) + start_offset
    end = datetime.combine(datetime.min, schedule.service_end)

    legs = []
    direction = DirectionType.FORWARD
    while t < end:
        legs.append((t.time(), direction))
        t += leg_duration
        direction = (
            DirectionType.BACKWARD
            if direction is DirectionType.FORWARD
            else DirectionType.FORWARD
        )
    return legs


async def get_line_ids(
    session: AsyncSession, line_names: list[str]
) -> dict[str, uuid.UUID]:
    rows = await session.execute(
        select(Lines.id, Lines.name).where(Lines.name.in_(line_names))
    )
    name_to_id = {name: id_ for id_, name in rows.all()}

    missing = set(line_names) - name_to_id.keys()
    if missing:
        raise RuntimeError(
            f"Line(s) {sorted(missing)} not found in `lines` table -- run "
            "seed_topology.py first (and make sure LINE_PERFORMANCE there "
            "covers them, or they'll have been skipped during seeding)."
        )
    return name_to_id


async def upsert_trains(
    session: AsyncSession, line_name: str, line_id: uuid.UUID, count: int
) -> list[uuid.UUID]:
    train_ids = []
    for i in range(count):
        train_id = train_id_for(line_name, i)
        name = train_name_for(line_name, i)
        stmt = (
            pg_insert(Trains)
            .values(id=train_id, name=name, line_id=line_id)
            .on_conflict_do_update(
                index_elements=[Trains.id],
                set_={"name": name, "line_id": line_id},
            )
        )
        await session.execute(stmt)
        train_ids.append(train_id)
    return train_ids


async def upsert_timetable_entries(
    session: AsyncSession,
    line_id: uuid.UUID,
    train_ids: list[uuid.UUID],
    schedule: LineSchedule,
) -> int:
    if not train_ids:
        return 0

    leg_duration = timedelta(minutes=settings.DEFAULT_ETA_MINUTES) + timedelta(
        minutes=settings.DEFAULT_TURNAROUND_BUFFER_MINUTES
    )

    count = 0
    for i, train_id in enumerate(train_ids):
        start_offset = timedelta(minutes=i * schedule.headway_minutes)
        for departure_time, direction in generate_train_legs(
            schedule, start_offset, leg_duration
        ):
            entry_id = timetable_entry_id_for(train_id, direction, departure_time)

            stmt = (
                pg_insert(TimetableEntries)
                .values(
                    id=entry_id,
                    train_id=train_id,
                    line_id=line_id,
                    direction=direction,
                    departure_time=departure_time,
                )
                .on_conflict_do_update(
                    index_elements=[TimetableEntries.id],
                    set_={
                        "direction": direction,
                        "departure_time": departure_time,
                    },
                )
            )
            await session.execute(stmt)
            count += 1

    return count


async def main() -> None:
    if not LINE_SCHEDULE:
        print(
            "[error] LINE_SCHEDULE is empty -- fill in fleet size / headway / "
            "service window per line before running this",
            file=sys.stderr,
        )
        sys.exit(1)

    async with session_maker() as session:
        line_ids = await get_line_ids(session, list(LINE_SCHEDULE.keys()))

        total_trains = 0
        total_entries = 0
        for line_name, schedule in LINE_SCHEDULE.items():
            line_id = line_ids[line_name]
            train_ids = await upsert_trains(
                session, line_name, line_id, schedule.train_count
            )
            total_entries += await upsert_timetable_entries(
                session, line_id, train_ids, schedule
            )
            total_trains += len(train_ids)

        await session.commit()

    print(
        f"[info] seeded {total_trains} trains, {total_entries} timetable "
        f"entries across {len(LINE_SCHEDULE)} line(s)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    asyncio.run(main())
