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

Three inbound ports feed two domain services (`TripService`,
`TimetableService`):

**1. Sim engine -> `ForUpdatingTrainPosition` -> `TripService.updateTrainPosition`
-> `ForPublishingTrainPosition` (Kafka) + `ForPersistingTrip` (`TripRepo`)**

The sim engine queries `TripRepo` directly to find currently-active trips (it
needs this to know what to simulate — this is the old "Dispatcher" filter,
now owned by the sim engine rather than ingestion), computes a new raw
position per trip per tick using the speed model below, and calls this port
**once per active trip**. `TripService` resolves that raw position into
segment/direction/interpolated point, persists the `Trip`, and publishes the
event. Per-trip granularity, not one batched tick call — this also happens to
match the shape a real ATS feed would use (one occupancy report per train),
not just the sim engine's shape.

**2. UI -> `ForUpdatingTimetable` -> `TimetableService.updateTimetable` ->
`ForPersistingTimetable` -> `TimetableRepo`**

Named for completeness; no validation/conflict logic designed yet, and not in
current build scope.

**3. Async-loop adapter (~6h) -> `ForGeneratingTrips` -> `TripService.generateTrips`
<- `ForLookingUpTrips` (`TripRepo` read) -> `ForPersistingTrip` -> `TripRepo`**

Runs on its own independent cadence, decoupled from the 1–2s position tick —
resolves the earlier open question about trip generation competing with
per-tick work. Logic unchanged from the original design: for every
`timetable_entries` row without a `trips` row for the relevant day, create
one, with `estimated_arrival_time` computed from line length ÷ speed.

`TripRepo` is **one shared repository** used by both the sim engine (reads,
to find active trips) and `TripService` (writes, to persist resolved
positions and generated trips). Accepted as fine for now — sim engine and
ingestion are components of a single deployable, not separate services.
Revisit only if they're ever split apart, since an external producer (e.g. a
real ATS-fed deployment) shouldn't read this table directly.

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
- **Constants are per-line**: `max_speed_mps` and `acceleration_mps2` live as
  new columns on `lines` (needs a migration, not yet written) rather than a
  single network-wide constant, a separate lookup table, or a code constant.
- **Short segments** (shorter than the combined accel+decel distance, which
  would need a triangular profile instead of trapezoidal) are a known,
  accepted gap for now — not implemented. A short segment may show a brief
  unrealistic speed spike; revisit if it turns out to matter visually once
  real Tashkent segment lengths are loaded.
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
2. Sim engine queries `TripRepo` directly for trips whose `[departure_time,
   estimated_arrival_time)` window contains `now()`.
3. For each active trip, sim engine computes the new raw position via the
   trapezoidal speed profile (elapsed time since departure -> speed ->
   arc-length delta).
4. Sim engine calls `ForUpdatingTrainPosition` once per active trip with the
   raw position.
5. `TripService.updateTrainPosition` resolves the raw position into
   segment/direction, asks `TopologyRepository`/PostGIS to interpolate the
   actual point, and persists the `Trip`.
6. Publishes a `train.positions` event only if the train has moved more than
   a threshold since the last published position — the threshold is a
   fraction of the current segment's `distance_to_next_m` (e.g. 1%), not a
   flat distance, so short and long segments both get a reasonable update
   rate. A trip dwelling at a station with zero movement simply doesn't
   publish — no heartbeat — since Redis already holds its last known
   position and nothing downstream needs a "still here" signal.
7. Commit.

**Trip generation (independent ~6h trigger):**
1. Async-loop adapter fires `ForGeneratingTrips`.
2. `TripService.generateTrips` reads `timetable_entries`, checks each for an
   existing `trips` row via `ForLookingUpTrips`.
3. Creates missing rows (with `estimated_arrival_time` from line length ÷
   speed) via `ForPersistingTrip`.
4. Commit.

**Timetable edit (placeholder, not designed):**
`UI -> ForUpdatingTimetable -> TimetableService.updateTimetable ->
ForPersistingTimetable -> TimetableRepo`.

## Directory structure (self-contained, no shared package yet)

```
services/ingestion/
  domain/               # Trip, Train, TimetableEntry, Line, Station,
                         # LineStation entities; TripService (updateTrainPosition,
                         # generateTrips); TimetableService (updateTimetable,
                         # placeholder)
  sim_engine/           # own tick loop; direct TripRepo reads (active-trip
                         # lookup); trapezoidal speed profile; calls
                         # ForUpdatingTrainPosition per active trip
  application/          # inbound ports: ForUpdatingTrainPosition,
                         # ForGeneratingTrips, ForUpdatingTimetable
  adapters/
    inbound/
      trip_generation_clock.py   # ~6h loop -> ForGeneratingTrips
      timetable_api.py           # placeholder, future UI-facing endpoint
    outbound/
      postgres/         # TripRepo (shared: sim_engine reads, TripService
                         # writes), TimetableRepo, TopologyRepository,
                         # SQLAlchemy models/mappers
      kafka/             # EventPublisher impl (FastStream), Event[T] envelope
  container.py           # Dishka providers wiring ports -> adapters
  main.py                # entrypoint: start sim engine loop + generation
                          # clock + FastStream app
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

Resolved by the sim engine / ingestion split:

- ~~`TripGenerator` scheduling~~ — resolved: independent ~6h trigger,
  decoupled entirely from the 1–2s position tick.
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
- ~~Speed profile parameters~~ — resolved: per-line constants
  (`max_speed_mps`, `acceleration_mps2`), new columns on `lines` (migration
  not yet written).
- ~~Short-segment clamp~~ — resolved: deferred as a known, accepted gap. No
  triangular-profile logic implemented; short segments may show a brief
  unrealistic speed spike.
- ~~Publish granularity~~ — resolved: publish on every tick, but downsampled
  by position delta — a trip only publishes once it's moved more than a
  threshold (a fraction of the current segment's length) since its last
  published position. No dwell heartbeat: a stationary trip simply doesn't
  publish, since Redis already holds its last known position.
- ~~Shared `TripRepo`~~ — accepted: sim engine reads it directly,
  `TripService` writes to it, both components of one deployable. Revisit
  only if sim engine and ingestion are ever split into genuinely separate
  services.

No open questions remain from this design pass. The next concrete step this
unblocks is writing the `lines.max_speed_mps` / `lines.acceleration_mps2`
migration.
