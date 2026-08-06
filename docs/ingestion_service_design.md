# Ingestion Service — Design

## Purpose

The ingestion service resolves raw train positions into topology (line/segment/
direction) and publishes them to Kafka — it's a translator, not a physics
engine. Producing those raw positions is a separate concern: today a **sim
engine** component fabricates them by simulating trip movement; later, a real
ATS feed would produce them from track-circuit occupancy. Both hand ingestion
a raw position through the same inbound port, so ingestion's core doesn't
change when the producer does — that's the swappable-producer guarantee
described in `PROJECT_CONTEXT.md` ("the ingestion service resolves raw
position into topology... a raw coordinate or track-circuit ID means nothing
on its own").

This corresponds to build-order steps 3 ("Simulation engine") and 4 ("Kafka
pipeline") from `CLAUDE.md` / `PROJECT_CONTEXT.md`, but not as a single fused
core. The sim engine and the ingestion resolver are two components, currently
in **one deployable** (same process, same codebase), each with a distinct
job:

- **Sim engine** — decides which trips are running right now and advances
  their position every tick. This is simulator-only logic: a real feed
  wouldn't need it, because a real train already knows where it is; the sim
  engine's job is to *fabricate* a raw position the same way a real ATS would
  report one.
- **Ingestion (`TripService`)** — takes whatever raw position it's handed,
  resolves it into topology terms, persists it, and publishes it. Producer-
  agnostic by construction.

## Scope

**In scope:**
- Sim engine: finding currently-active trips (time-window filter over
  `trips`), advancing each one's raw position every tick via a speed profile
  (see below).
- Trip materialization (`TripService.generateTrips`): turning
  `timetable_entries` into concrete `trips` rows, on its own independent
  trigger — decoupled from the position tick.
- Position resolution (`TripService.updateTrainPosition`): raw position ->
  segment/direction/interpolated point, persisted and published.
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
The `ForUpdatingTimetable` port below is named but deliberately not designed
yet — placeholder only.

## Components and ports

Three inbound ports were designed to feed two domain services (`TripService`,
`TimetableService`). As implemented: one is fully wired, one is wired but
incomplete, and one doesn't exist in the codebase at all.

**1. `Simulator.run()` -> `ForUpdatingTrainPosition` -> `TripService.update`
-> `ForUpdatingTrip` (persist only — `ForPublishingTrainPosition` is never called)**

`Simulator` (`adapters/driving/forUpdatingTrainPosition/simulator.py`) queries
the `Trips` table directly via raw SQLAlchemy inside itself — not through a
`TripRepo`/port — to find currently-active trips, computes a new raw position
per trip per tick using the speed model below, and calls
`ForUpdatingTrainPosition.update()` once per active trip inside a
`try/except` (added after an early version let one bad trip — e.g. a
`.one()` join in the position calculator finding no matching row — kill the
whole loop; now it logs `[error] ...` and moves on to the next trip).
Per-trip granularity, matching the shape a real ATS feed would use (one
occupancy report per train).

`TripService.update` resolves segment rollover via `ForLookingUpStation`
(renamed from the originally-designed `ForLookingUpNextSegment` — it grew
two more methods, `get_station_by_id` and `get_start_station`, so the
narrower name no longer fit) and persists via `ForUpdatingTrip`. As of this
round it **does** interpolate `current_position`: a new port,
`ForCalculatingCurrentTrainPosition` (adapter `TrainPositionCalculator`),
projects the trip onto its line geometry with PostGIS
(`ST_LineLocatePoint`/`ST_LineInterpolatePoint` between the current and next
station) while mid-segment, and `ForLookingUpStation.get_station_by_id`
snaps the position exactly onto the station's own point on segment-advance
and on finish. Still **not** implemented: recomputing `estimated_arrival_time`
or deriving `trip_status` — still a `# TODO` pass-through of the old values.
`ForPublishingTrainPosition` is still never called — that port exists but has
no adapter, so no Kafka publish happens yet.

A write-throttle guards `ForUpdatingTrip.update()`: if
`new_progress - old.progress_pct < settings.MIN_PROGRESS_THRESHOLD`, `update`
returns `False` without touching Postgres — except when the trip has reached
a segment/trip boundary (`new_progress >= 100`), which always writes
regardless of delta size. That exemption exists because without it, a trip
whose last *persisted* checkpoint landed within one threshold-unit of 100%
could stall forever: raw progress asymptotically caps at exactly `100.0` once
elapsed time exceeds the segment's trapezoidal travel time and never grows
past it, so a delta that's permanently just under the threshold would never
resolve on its own. `new_progress` is also rounded to 2 decimal places before
this comparison (and before persisting), to match `trips.progress_pct`'s
`NUMERIC(5,2)` column precision — without the rounding, comparing a
full-precision Python float against a value Postgres already rounded to 2
places on the previous write produces small (`< 0.005`) negative deltas that
are harmless (still `< threshold`, still a no-op) but read as alarming in the
logs.

**2. UI -> `ForUpdatingTimetable` -> `TimeTableService.update` ->
`ForStoringTimetable`**

Matches the original design's intent (named `ForPersistingTimetable` there;
it ended up as `ForStoringTimetable`). No validation/conflict logic designed
yet, still not in current build scope.

**3. `TripGenerator.run()` -> `ForGeneratingTrip` -> `TripService.generate` ->
`ForStoringTrip` (implemented and working)**

The port that was reported deleted in an earlier revision of this doc is
back: `for_generating_trip.py` exists, `TripService.generate()` implements
it, and it runs as its own process (`generator_main.py`, a third entrypoint
alongside `main.py` and `simulator_main.py`) via a polling adapter
(`adapters/driving/forGeneratingTrips/trip_generator.py`,
`TripGenerator.run()`) on an independent `settings.GENERATOR_SLEEP_TIME_S`
cadence (default 6h — matches the originally-designed ~6h trigger).
`TripService.generate()` looks one calendar day ahead
(`tomorrow = now + 1 day`), diffs `timetable_entries` against the `trips`
already stored for that date, and calls `ForStoringTrip.store()` for any
entry that doesn't have a matching trip yet, seeding each new trip's starting
segment via `ForLookingUpStation.get_start_station()`.

`python -m src.generator_main` (`make generate`) previously crashed
immediately on import — `trip_generator.py` imported `from settings import
settings` instead of `from src.settings import settings`, and since the
process runs as `python -m src.generator_main`, `services/ingestion/` (not
`services/ingestion/src/`) is on `sys.path`, so there was no top-level
`settings` module to find. Fixed: verified `make generate` now runs cleanly
(`[info] Generator started...` -> finds timetable entries and existing
trips -> sleeps for `GENERATOR_SLEEP_TIME_S`).

There's no single shared `TripRepo`. Reads and writes are separate
`TripRepository` classes (same class name, different modules) —
`adapters/driven/forLookingUpTrip/trip_repository.py` implements
`ForLookingUpTrip`, `adapters/driven/forUpdatingTrip/trip_repository.py`
implements `ForUpdatingTrip`, and `adapters/driven/forStoringTrip/trip_repository.py`
implements `ForStoringTrip` for trip generation — three classes, same name,
three modules. `Simulator` additionally reads `Trips`, `Lines`, and
`LineStations` directly, bypassing all of them, and the new
`TrainPositionCalculator` does the same for `Lines`/`LineStations`/`Stations`
geometry — see `TopologyRepository abstraction` under Open questions.

## Sim engine: speed model

**Decided: trapezoidal speed profile** (accelerate -> cruise at max speed ->
decelerate), computed **statelessly** — speed is never persisted as a field
on `trips`, only derived each tick from elapsed time since departure (or
arc-length already covered) within the current segment. This matches the
domain's existing pattern of not storing state that's cheaply derivable
(trip-active status is a time-range comparison, not a stored flag; same idea
here).

- Each segment (`line_stations` edge) accelerates from 0 up to a max speed,
  cruises, then decelerates to ~0 at the next station — standard kinematics
  (`v = u + at`, `d = ut + ½at²`) per phase.
- **Constants are per-line**: `max_speed_mps` and `max_acceleration_mps2` live
  as columns on `lines` (migration 00003, applied) rather than a single
  network-wide constant, a separate lookup table, or a code constant.
- **Short segments** (shorter than the combined accel+decel distance, which
  needs a triangular profile instead of trapezoidal) are handled —
  `Simulator._apply_trapezoidal_velocity` falls back to
  `v_top = sqrt(distance * a)` when the trapezoidal `d_cruise` would go
  negative — though the `d_acc` offset used afterward isn't recalculated for
  the smaller triangular `v_top`, so double-check the numbers before trusting
  it fully.
- Considered and rejected for now:
  - Persisting a `current_speed_mps` field — real ATS telemetry would
    include it, but nothing downstream needs speed as its own queryable
    datum yet.
  - Constant speed per segment — looks robotic (instant snap to full speed,
    dead stop at stations).
  - S-curve (jerk-limited) profiles — more realistic, not worth the
    complexity at demo scale.
  - Random jitter on top of the base profile — still open, could layer on
    later for visual "aliveness."

## Tick flow

Two independent flows, decoupled by cadence:

**Position update (sim engine's own loop, `settings.SIMULATOR_SLEEP_TIME_S`,
default 0.2s — configurable, was a hardcoded 1s originally):**
1. Sim engine tick fires.
2. `Simulator._get_active_trips()` queries `Trips` directly via raw
   SQLAlchemy (not through a repository/port) for rows where
   `departure_time < now()` and `is_finished = false`. Not an
   `[departure_time, estimated_arrival_time)` window check as originally
   planned — the upper bound relies on the `is_finished` flag instead.
3. For each active trip, `Simulator` computes the new raw position via the
   trapezoidal speed profile, using elapsed time since the trip *entered its
   current segment* (`current_segment_time`, added in migration 00005) —
   not elapsed time since trip departure, which was tried first and doesn't
   work once a trip has moved past its first segment. This whole per-trip
   step is wrapped in `try/except` so one trip's failure (e.g. a segment
   with no matching row for the position calculator's join) doesn't take
   down the rest of the batch.
4. `Simulator` calls `ForUpdatingTrainPosition` once per active trip with the
   raw position.
5. `TripService.update` resolves segment rollover via `ForLookingUpStation`
   (advances `current_segment_id`, resets `current_segment_time`), computes
   `current_position` via `ForCalculatingCurrentTrainPosition` (PostGIS
   interpolation mid-segment; exact station coordinates via
   `get_station_by_id` on segment-advance/finish), and persists via
   `ForUpdatingTrip` — subject to the write-throttle described above. **Not
   yet implemented**: recomputing `estimated_arrival_time`, deriving
   `trip_status` — still a `# TODO` in `trip_service.py`.
6. **Not yet implemented**: publishing a `train.positions` event.
   `ForPublishingTrainPosition` is defined but has no adapter and is never
   called. The threshold-based publish design described here is still the
   plan, not the current behavior.
7. Commit — to Postgres only, no Kafka in this loop yet.

**Trip generation (independent loop, `settings.GENERATOR_SLEEP_TIME_S`,
default 6h):** implemented and running — see "Components and ports" above.

**Timetable edit (placeholder, not designed):**
`UI -> ForUpdatingTimetable -> TimetableService.updateTimetable ->
ForPersistingTimetable -> TimetableRepo`.

## Directory structure

What actually got built, under `services/ingestion/src/` — hexagonal, with
ports named `ForXxx` and adapters split into `driving/` (callers of core) and
`driven/` (core's dependencies), not the `domain/`/`sim_engine/`/
`application/` split originally sketched:

```
services/ingestion/src/
  core/
    common/
      models/            # Trip, Position, Timetable — shared domain models
      exceptions.py
    ports/
      driving/           # ForUpdatingTrainPosition, ForUpdatingTimetable,
                         # ForGeneratingTrip
      driven/            # ForLookingUpTrip, ForUpdatingTrip, ForStoringTrip,
                         # ForLookingUpStation, ForCalculatingCurrentTrainPosition,
                         # ForStoringTimetable, ForLookingUpTimetable,
                         # ForPublishingTrainPosition
    trip_service.py       # TripService(ForUpdatingTrainPosition, ForGeneratingTrip)
    timetable_service.py  # TimeTableService(ForUpdatingTimetable)
  adapters/
    driving/
      forUpdatingTrainPosition/simulator.py  # Simulator — the sim engine
      forUpdatingTimetable/timetable_update_router.py  # FastAPI router
      forGeneratingTrips/trip_generator.py   # TripGenerator — polling loop
    driven/
      forLookingUpTrip/, forUpdatingTrip/, forStoringTrip/  # three separate
                                             # TripRepository classes — not
                                             # one shared repo
      forLookingUpStation/line_stations_repository.py  # renamed from
                                             # forLookingUpNextSegment; also
                                             # covers get_station_by_id,
                                             # get_start_station
      forCalculatingCurrentTrainPosition/train_position_calculator.py  # new —
                                             # PostGIS interpolation
      forLookingUpTimetable/, forStoringTimetable/
      common/            # database_session.py, unit_of_work.py,
                         # models.py (sqlacodegen-generated, not hand-written)
  main.py                # FastAPI app: timetable HTTP routes only
  simulator_main.py       # entrypoint/process: builds its own Dishka
                         # container, runs Simulator.run()
  generator_main.py       # entrypoint/process: builds its own Dishka
                         # container, runs TripGenerator.run()
  settings.py
```

No `container.py` — `main.py`, `simulator_main.py`, and `generator_main.py`
each build their own `Provider` inline rather than sharing one. No `kafka/`
adapter directory — `ForPublishingTrainPosition` has no implementation yet.
No `TopologyRepository`: `ForCalculatingCurrentTrainPosition` now owns the
one topology query that actually needed to be behind a port (line/station
geometry for interpolation), but `Simulator._get_segment_length`/
`_get_train_speed` (segment length, per-line `max_speed_mps`/
`max_acceleration_mps2`) still query `LineStations`/`Lines` directly via raw
SQLAlchemy against `IDatabaseSession` rather than through any port — still
the place this service breaks its own ports-and-adapters convention, just a
smaller one than before.

`simulator_main.py` and `generator_main.py` both register `IDatabaseSession`
and `IUnitOfWork` at `Scope.APP` — one `AsyncSession` shared for every read
and a separate one shared for every write, for the whole process lifetime,
rather than a fresh session per unit of work. Every repo method wraps its
query in `async with self._database_session:`, and `AsyncSession.close()` on
exit does clear SQLAlchemy's identity map, which is likely why this hasn't
caused visible staleness — but it's a fragile pattern for a long-running
loop and worth revisiting before adding real concurrency (see Open
questions).

Running as three processes (`main.py` via `fastapi dev`, `simulator_main.py`
and `generator_main.py` via `python -m src.<name>`) rather than one
deployable with an internal loop, which is a change from this doc's original
framing of "sim engine and ingestion resolver, same process."

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

- ~~Train completion state~~ — partially revised: `is_finished` was added as
  a stored flag on `trips` (migration 00004) and `Simulator._get_active_trips`
  filters on it directly, alongside `departure_time < now()`. Not a pure
  time-range comparison against `estimated_arrival_time` as originally
  planned.
- ~~Headway vs. single departure~~ — resolved: `timetable_entries` is the
  recurring template, `trips` is one row per actual calendar occurrence.
- ~~Double-booking~~ — resolved at the DB level via the `EXCLUDE` constraint
  on `trips` (`train_id` + overlapping `tstzrange`), migration 00002. Not
  visible in `adapters/common/models.py` — sqlacodegen doesn't reflect
  `EXCLUDE` constraints — but it's live in the schema.

Still open:

- **Kafka publish.** `ForPublishingTrainPosition` is defined but has no
  adapter and no caller. The threshold-based publish design below is still
  the plan, not implemented, and Kafka isn't in `infra/docker-compose.yaml`
  yet either.
- **ETA/status derivation.** `TripService.update` still has a
  `# TODO calc new eta, trip status` — those two fields are still a
  pass-through of the old values every tick.
- **`TopologyRepository` abstraction.** Still never built as a single port.
  `ForCalculatingCurrentTrainPosition` now covers position interpolation
  specifically, but `Simulator._get_segment_length`/`_get_train_speed` still
  query `LineStations`/`Lines` directly — see Directory structure above.
- **Shared long-lived DB session.** `IDatabaseSession`/`IUnitOfWork` are
  `Scope.APP` singletons in both `simulator_main.py` and `generator_main.py`
  — one session reused for every read (a separate one for every write) over
  the whole process lifetime instead of per unit of work. Works today
  because `AsyncSession.close()` (called at the end of every `async with
  self._database_session:` block) clears the identity map each time, but
  it's not a pattern that's safe to build real concurrency on top of.

Resolved this round:

- **Trip generation.** Implemented and working — `ForGeneratingTrip`/
  `TripService.generate()`, driven by `TripGenerator` on a
  `settings.GENERATOR_SLEEP_TIME_S` (default 6h) loop via the new
  `generator_main.py` entrypoint. Its broken import (see below) is fixed;
  `make generate` runs cleanly.
- **Generator's broken import.** `trip_generator.py` was importing
  `from settings import settings` instead of `from src.settings import
  settings`, which crashed `python -m src.generator_main` with
  `ModuleNotFoundError` before `TripGenerator.run()` ever started (running
  as a `-m` module puts `services/ingestion/`, not `services/ingestion/src/`,
  on `sys.path`). Fixed.
- **Position interpolation.** Implemented — `ForCalculatingCurrentTrainPosition`
  (`TrainPositionCalculator`) interpolates `current_position` along the
  line's PostGIS geometry between the current and next station while
  mid-segment; `ForLookingUpStation.get_station_by_id` snaps to the exact
  station point on segment-advance and on finish.
- **Per-tick error isolation.** `Simulator.run()`'s per-trip loop is now
  wrapped in `try/except`; one trip failing no longer takes down the whole
  tick.
- **"Stuck forever" write-throttle failure mode.** `MIN_PROGRESS_THRESHOLD`
  now exempts boundary crossings (`new_progress >= 100`) from the
  too-small-delta check, and `new_progress` is rounded to 2 decimals before
  comparison/persist to match the `NUMERIC(5,2)` column — closes the gap
  where a trip's last-persisted checkpoint landing within one threshold-unit
  of 100% could never resolve, since raw progress caps at exactly `100.0`
  and stops growing.

Resolved by the sim engine / ingestion split:

- **Real-feed inbound port** — mostly resolved by construction: a real ATS
  feed adapter would simply replace the sim engine as producer, calling the
  same `ForUpdatingTrainPosition` port; ingestion's resolver logic doesn't
  change. Still genuinely open: what shape the real raw signal takes
  (track-circuit ID vs. coordinate) and whether it maps onto arc-length/
  fraction the same way the sim engine's raw position does. Revisit once the
  real data format is known.

Resolved previously:

- ~~Turnaround~~ — confirmed: each train gets separate `FORWARD` and
  `BACKWARD` `timetable_entries` rows; turnaround needs no domain logic,
  only correctly authored seed data.
- ~~Speed profile parameters~~ — resolved **and implemented**: per-line
  constants `max_speed_mps`, `max_acceleration_mps2` on `lines`, migration
  00003, applied.
- ~~Short-segment clamp~~ — this doc previously said "not implemented," but
  `Simulator._apply_trapezoidal_velocity` does fall back to a triangular
  profile (`v_top = sqrt(distance * a)`) when `d_cruise < 0`. Worth a closer
  look before calling it fully correct — the `d_acc` offset used in the
  post-peak branches isn't recalculated for the smaller triangular `v_top`,
  so it may still be off — but the "not implemented" framing here is stale.
- ~~Publish granularity~~ — design unchanged (publish on every tick,
  downsampled by a fraction of segment length, no dwell heartbeat), but
  **not implemented** — see Kafka publish above.
- ~~Shared `TripRepo`~~ — **incorrect as originally written.** There is no
  shared `TripRepo`. `ForLookingUpTrip` and `ForUpdatingTrip` were two
  separate repository classes (now three, with `ForStoringTrip` — see
  Components and ports), and `Simulator` additionally queries `Trips`,
  `Lines`, and `LineStations` directly, bypassing all of them.

## Current status

Three processes now exist and all three run: `main.py` (timetable HTTP API),
`simulator_main.py` (position updates), and `generator_main.py` (trip
generation — its startup crash is fixed).

The position-update flow (`Simulator.run()` -> `ForUpdatingTrainPosition` ->
`TripService.update` -> `ForUpdatingTrip`) is implemented, per-trip
error-isolated, and includes real position interpolation via
`ForCalculatingCurrentTrainPosition`. The trip-generation flow
(`TripGenerator.run()` -> `ForGeneratingTrip` -> `TripService.generate` ->
`ForStoringTrip`) is implemented and running. The concrete gaps left before
this matches the original end-to-end design: ETA/status derivation and
Kafka publish (`ForPublishingTrainPosition` still has no adapter) — see
"Still open" above. The `Scope.APP`-singleton DB session pattern shared by
both long-running entrypoints is also worth revisiting before this goes
further.
