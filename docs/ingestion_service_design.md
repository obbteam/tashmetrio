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
`ForUpdatingTrainPosition.update()` once per active trip. Per-trip
granularity, matching the shape a real ATS feed would use (one occupancy
report per train). `TripService.update` resolves segment rollover via
`ForLookingUpNextSegment` and persists via `ForUpdatingTrip`. It does **not**
yet interpolate `current_position`, recompute `estimated_arrival_time`, or
derive `trip_status` — still a `# TODO` pass-through of the old values — and
it never calls `ForPublishingTrainPosition`. That port exists but has no
adapter and no caller, so no Kafka publish happens yet.

**2. UI -> `ForUpdatingTimetable` -> `TimeTableService.update` ->
`ForStoringTimetable`**

Matches the original design's intent (named `ForPersistingTimetable` there;
it ended up as `ForStoringTimetable`). No validation/conflict logic designed
yet, still not in current build scope.

**3. Trip generation — not implemented.**

The original design called for `ForGeneratingTrips` / `TripService.generateTrips`
on an independent ~6h trigger, turning `timetable_entries` rows into `trips`
rows. That port (`for_generating_trip.py`) existed at one point and has since
been deleted from the codebase — nothing currently creates `trips` rows from
`timetable_entries`. `trips` rows need to be inserted by hand for `Simulator`
to have anything to move. This is an open question again, not a resolved one
(see Open questions below).

There's no single shared `TripRepo`. Reads and writes are two separate
`TripRepository` classes (same class name, different modules) —
`adapters/driven/forLookingUpTrip/trip_repository.py` implements
`ForLookingUpTrip`, `adapters/driven/forUpdatingTrip/trip_repository.py`
implements `ForUpdatingTrip` — and `Simulator` additionally reads `Trips`,
`Lines`, and `LineStations` directly, bypassing both.

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

**Position update (sim engine's own loop, 1–2s):**
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
   work once a trip has moved past its first segment.
4. `Simulator` calls `ForUpdatingTrainPosition` once per active trip with the
   raw position.
5. `TripService.update` resolves segment rollover via
   `ForLookingUpNextSegment` (advances `current_segment_id`, resets
   `current_segment_time`) and persists via `ForUpdatingTrip`. **Not yet
   implemented**: interpolating the actual lat/lng (`current_position`),
   recomputing `estimated_arrival_time`, deriving `trip_status` — still a
   `# TODO` in `trip_service.py`. No `TopologyRepository`/PostGIS
   interpolation step exists.
6. **Not yet implemented**: publishing a `train.positions` event.
   `ForPublishingTrainPosition` is defined but has no adapter and is never
   called. The threshold-based publish design described here is still the
   plan, not the current behavior.
7. Commit — to Postgres only, no Kafka in this loop yet.

**Trip generation — not implemented.** See "Components and ports" above: no
async-loop adapter, no `ForGeneratingTrips` port, no `generateTrips` method
exist in the current codebase. `trips` rows must be inserted manually for
now.

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
      driving/           # ForUpdatingTrainPosition, ForUpdatingTimetable
      driven/            # ForLookingUpTrip, ForUpdatingTrip,
                         # ForLookingUpNextSegment, ForStoringTimetable,
                         # ForLookingUpTimetable, ForPublishingTrainPosition
    trip_service.py       # TripService(ForUpdatingTrainPosition)
    timetable_service.py  # TimeTableService(ForUpdatingTimetable)
  adapters/
    driving/
      forUpdatingTrainPosition/simulator.py  # Simulator — the sim engine
      forUpdatingTimetable/timetable_update_router.py  # FastAPI router
    driven/
      forLookingUpTrip/, forUpdatingTrip/    # two separate TripRepository
                                             # classes — not one shared repo
      forLookingUpNextSegment/line_stations_repository.py
      forLookingUpTimetable/, forStoringTimetable/
      common/            # database_session.py, unit_of_work.py,
                         # models.py (sqlacodegen-generated, not hand-written)
  main.py                # FastAPI app: timetable HTTP routes only
  simulator_main.py       # separate entrypoint/process: builds its own
                         # Dishka container, runs Simulator.run()
  settings.py
```

No `container.py` — `main.py` and `simulator_main.py` each build their own
`Provider` inline rather than sharing one. No `kafka/` adapter directory —
`ForPublishingTrainPosition` has no implementation yet. No
`TopologyRepository`: `ForLookingUpNextSegment` covers "what's the next
segment," but segment length (`distance_to_next_m`) and per-line
`max_speed_mps`/`max_acceleration_mps2` are queried directly inside
`Simulator` via raw SQLAlchemy against `IDatabaseSession` — the one place
this service currently breaks its own ports-and-adapters convention.

Running as two processes (`main.py` via `fastapi dev`, `simulator_main.py`
via `python -m src.simulator_main`) rather than one deployable with an
internal loop, which is a change from this doc's original framing of
"sim engine and ingestion resolver, same process."

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

Reopened — previously marked resolved, not actually built:

- **Trip generation.** `ForGeneratingTrips`/`TripService.generateTrips` was
  designed and apparently prototyped (`for_generating_trip.py` existed, then
  was deleted) but nothing currently creates `trips` rows from
  `timetable_entries`. Does this come back as the ~6h async loop originally
  designed, or does something else own trip creation now?
- **Kafka publish.** `ForPublishingTrainPosition` is defined but has no
  adapter and no caller. The threshold-based publish design below is still
  the plan, not implemented, and Kafka isn't in `infra/docker-compose.yaml`
  yet either.
- **Position/ETA/status derivation.** `TripService.update` still has a
  `# TODO calc new eta, trip status, position` — `current_position` is never
  interpolated from segment + progress, so nothing downstream would have
  real coordinates to render yet.
- **`TopologyRepository` abstraction.** Never built as a port. Segment
  length and per-line speed/acceleration are queried directly inside
  `Simulator`, not through a port — see Directory structure above.

Resolved by the sim engine / ingestion split:

- **Real-feed inbound port** — mostly resolved by construction: a real ATS
  feed adapter would simply replace the sim engine as producer, calling the
  same `ForUpdatingTrainPosition` port; ingestion's resolver logic doesn't
  change. Still genuinely open: what shape the real raw signal takes
  (track-circuit ID vs. coordinate) and whether it maps onto arc-length/
  fraction the same way the sim engine's raw position does. Revisit once the
  real data format is known.

Resolved this round:

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
  shared `TripRepo`. `ForLookingUpTrip` and `ForUpdatingTrip` are two
  separate repository classes, and `Simulator` additionally queries `Trips`,
  `Lines`, and `LineStations` directly, bypassing both.

## Current status

The position-update flow (`Simulator.run()` -> `ForUpdatingTrainPosition` ->
`TripService.update` -> `ForUpdatingTrip`) is implemented and runs as its own
process via `simulator_main.py`. The concrete gaps left before this matches
the original end-to-end design are trip generation, Kafka publish, and
position/ETA/status derivation — see "Reopened" above.
