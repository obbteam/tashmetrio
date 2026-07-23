# Ingestion Service — Design

## Purpose

The ingestion service is the domain core of the simulated railway: it decides
which trips are running right now, advances their position every tick, and
publishes those positions to Kafka. It corresponds to build-order steps 3
("Simulation engine") and 4 ("Kafka pipeline") from `CLAUDE.md` /
`PROJECT_CONTEXT.md` combined — those two steps aren't separate services in
the hexagonal layout described in `PROJECT_CONTEXT.md`; the simulator is just
the inbound adapter that drives this service's core, and the Kafka producer
is one of its outbound adapters. There is no standalone "simulation engine"
sitting apart from ingestion.

## Scope

**In scope:**
- Materializing `trips` from `timetable_entries` (turning the recurring daily
  plan into concrete, individually-trackable runs for a given day).
- Per-tick position advancement for every currently active trip.
- Publishing `train.positions` events to Kafka.
- Adding a Kafka broker to local infra.

**Out of scope (later steps or different concerns):** the HTTP read API, the
Kafka consumer that writes to the Redis state cache, the WebSocket gateway,
`network.alerts` (depends on incidents, not designed here). A real ATS/CBTC
feed adapter is speculative until operator conversations happen (per
`PROJECT_CONTEXT.md`) and isn't designed here either — see Open Questions.
`transfers` (station-to-station walking edges at interchanges) is also out of
scope here — a physical train never "transfers" lines mid-trip, so that table
belongs to a future passenger trip-planning capability, not to this service.

## Hexagonal structure

```
 SimulationClock (inbound adapter, in-process tick loop)
        │  calls
        ▼
 AdvanceSimulationTick (inbound port / use case)
        │
        ▼
 Domain core: TripGenerator + Dispatcher + PositionAdvancer
        │                                        │
        ▼ (outbound ports)                       ▼
 TopologyRepository, TimetableRepository,   EventPublisher
 TripRepository
        │                                        │
        ▼ (outbound adapters)                    ▼
 Postgres (SQLAlchemy async)               Kafka producer (FastStream)
```

### Inbound

- **Adapter**: `SimulationClock` — an async loop (or APScheduler) that fires
  every 1–2s and calls the inbound port directly as a function call. No
  network hop, no queue between "simulator" and "ingestion" — they are the
  same process; the simulator *is* this service's tick source.
- **Port**: `AdvanceSimulationTick.tick(now: datetime) -> None` — the single
  entrypoint the domain core exposes to any tick source.

### Domain core

Entities reflected in the schema (`00002_topology_and_domain_tables.sql`):

- `Line`, `Station`, `LineStation` — topology, read-mostly.
- `Train` — the fleet roster (`name`, a dedicated `line_pk`). Rarely changes;
  this service never creates or retires a `Train` row.
- `TimetableEntry` — the recurring daily plan (`train_pk`, `direction`,
  `departure_time` as a bare `TIME`). Edited independently of anything live —
  changing tomorrow's headways never touches a row something else is
  actively writing to.
- `Trip` — one concrete calendar occurrence of a `TimetableEntry`
  (`departure_time`/`estimated_arrival_time` as real `TIMESTAMPTZ`s, plus the
  live fields: `trip_status`, `current_segment_pk`, `progress_pct`,
  `current_position`). This is the row this service actually mutates every
  tick.

Three domain services, all invoked from the same `AdvanceSimulationTick` use
case (one core, several internal roles — no separate deployable):

- **TripGenerator** — reads `timetable_entries` and, for any entry that
  doesn't yet have a `trips` row for the relevant day, creates one:
  `estimated_arrival_time` is computed from `departure_time` + (line length ÷
  commercial speed, from `line_stations`/`lines`) and stored directly on the
  new row. Doesn't need to run every tick the way the other two do — see Open
  Questions. The DB-level `EXCLUDE` constraint on `trips` (`train_pk` +
  time-range overlap) is a backstop against a bug here, not something this
  logic needs to check itself; a coherent timetable should never trigger it.
- **Dispatcher** — per tick, finds `trips` whose `[departure_time,
  estimated_arrival_time)` window currently contains `now()`. This used to
  mean *creating and deleting* rows (spawn/retire a live `Train`); now it's a
  pure filter over rows that already exist, because `TripGenerator` creates
  them ahead of time. Trips outside their window are simply skipped, not
  touched.
- **PositionAdvancer** — for every trip `Dispatcher` hands it, computes
  `delta_arc_length = elapsed_time × segment_speed`, advances
  `progress_pct`/`current_segment_pk` (crossing into the next `line_station`
  when progress reaches 100%), and asks `TopologyRepository` for the
  interpolated point at the resulting fraction.

### Outbound ports

- **`TopologyRepository`** — read `lines`/`stations`/`line_stations`
  (ordered per line, with distances); interpolate a point at a given fraction
  along a line's geometry.
- **`TimetableRepository`** — read `timetable_entries` (the recurring plan).
  Used only by `TripGenerator`.
- **`TripRepository`** — create `trips` rows (`TripGenerator`); read/update
  currently active trips (`Dispatcher`, `PositionAdvancer`).
- **`EventPublisher`** — publish `train.positions` (and, later,
  `network.alerts`) using the existing `Event[T]` envelope mentioned in
  `PROJECT_CONTEXT.md`.

### Outbound adapters

- **Postgres adapter** (SQLAlchemy async + asyncpg) implementing all three
  repositories. Position interpolation is delegated to PostGIS —
  `ST_LineInterpolatePoint(line.geom, fraction)` — so the domain core only
  ever computes a plain 0–1 fraction (`arc_length / line_length`) and never
  touches geometry directly. This keeps the domain geometry-agnostic and
  avoids maintaining a second interpolation implementation that has to stay
  bit-for-bit consistent with what's stored in `lines.geom` /
  `line_stations.distance_to_next_m`.
- **Kafka producer adapter** (FastStream) implementing `EventPublisher`.
- Dishka binds all adapters to their ports at startup.

## Tick flow

1. `SimulationClock` fires with the current time.
2. `AdvanceSimulationTick.tick(now)` runs.
3. **TripGenerator**: ensures every `timetable_entries` row has a
   corresponding `trips` row for the relevant day (see Open Questions on how
   often this step actually needs to do real work).
4. **Dispatcher**: query `trips` whose time window contains `now`.
5. **PositionAdvancer**: for each, compute new segment/progress/fraction,
   call `TopologyRepository` to interpolate the point, update and persist
   the `Trip`.
6. Publish a `train.positions` event per trip that changed this tick.
7. Commit.

## Directory structure (self-contained, no shared package yet)

```
services/ingestion/
  domain/              # Train, TimetableEntry, Trip, Line, Station,
                        # LineStation entities + TripGenerator, Dispatcher,
                        # PositionAdvancer
  application/         # inbound port + AdvanceSimulationTick use case
  adapters/
    inbound/           # SimulationClock
    outbound/
      postgres/        # TopologyRepository, TimetableRepository,
                        # TripRepository impls, SQLAlchemy models/mappers
                        # for the existing schema
      kafka/           # EventPublisher impl (FastStream), Event[T] envelope
  container.py         # Dishka providers wiring ports -> adapters
  main.py              # entrypoint: start clock + FastStream app
```

Deliberately not sharing code with the future consumer/WebSocket service
(step 5) yet — extract a shared package if and when that service actually
needs the same domain entities, per the project's no-premature-abstraction
default.

## Infra changes

- Add **Apache Kafka in KRaft mode** (no separate Zookeeper container) to
  `infra/docker-compose.yaml`.
- New topic: `train.positions`, partition key `train_id`. Keying by the
  fleet-stable `train_id` rather than the ephemeral `trip_id` matters here:
  it keeps one continuous stream per physical vehicle across trip
  boundaries, which is what the frontend needs for a marker to animate
  smoothly across an entire day rather than resetting every time a train
  starts a new trip. `network.alerts` deferred until incidents are in scope.

## Open questions

Resolved by the `Train` / `TimetableEntry` / `Trip` split:

- ~~Train completion state~~ — no longer applicable. `trips` are time-bounded
  by `estimated_arrival_time`; "is this trip active" is a time comparison,
  not a stored lifecycle status.
- ~~Headway vs. single departure~~ — resolved: `timetable_entries` is the
  recurring template, `trips` is one row per actual calendar occurrence.
- ~~Double-booking~~ — resolved at the DB level via the `EXCLUDE` constraint
  on `trips` (`train_pk` + overlapping time range).

Still open:

- **Turnaround**: mostly resolved by construction, assuming a train's
  turnaround is just its next `timetable_entries` row happening to have the
  opposite `direction` — no domain logic needed, only correct seed data.
  Worth confirming that's actually how you intend to author the timetable
  before writing seed data (each train having separate `FORWARD` and
  `BACKWARD` entries).
- **`TripGenerator` scheduling**: does it run on the same 1–2s clock as the
  other two roles (cheap no-op most ticks, since it only needs to act once a
  day), or does it deserve its own independent trigger (daily cron, or an
  on-startup catch-up pass) so a slower generation query never competes with
  the per-tick position-advancement path? Not decided.
- **Real-feed inbound port**: still open — a real ATS pushes discrete
  track-circuit occupancy events, not a fixed clock tick to interpolate
  between, and doesn't obviously map onto `Trip`/`TimetableEntry` either,
  since a real feed wouldn't need a "recurring plan" table the same way a
  simulator does. Revisit once the real data format is known.
- **Publish granularity**: does every active trip get a `train.positions`
  event every tick, or only ones whose segment/status actually changed?
- **Segment speed source**: now blocks two things instead of one — both
  `PositionAdvancer`'s per-tick math and `TripGenerator`'s
  `estimated_arrival_time` computation need underground-vs-elevated speed,
  and the source (a column, a lookup table, a constant per line) still isn't
  decided. This graduated from "affects live ticks" to "blocks trip
  generation outright" — worth resolving sooner rather than later.
