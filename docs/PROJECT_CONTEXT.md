# Tashkent Metro Live Map — Project Context

## Goal

Build a live map of Tashkent Metro trains as a **pitch artifact for the metro operator**
(Toshkent Metropoliteni), not just a personal tool. The strategy is to build a fully working
demo on simulated data first, then use it to convince the operator to grant access to a real
data feed — swapping one component, not rebuilding the system.

## Data reality check

- There is **no public real-time GPS/AVL feed** for Tashkent Metro trains.
- **ATTO is not a train-tracking system.** It's the fare payment operator (turnstile taps,
  card balances). It has no train position data.
- Real train position, if the operator has it, comes from their **ATS/signaling system**
  (track-circuit occupancy), not GPS — **three of the four lines run underground**, where
  consumer GPS doesn't work. Only the elevated Circle Line could plausibly use GPS.
- Conclusion: for v1, **simulated positions are not a stopgap, they're the only option**, and
  that's a legitimate framing for the pitch itself: "here's what we can show with zero
  operator data — imagine this fed by your real signaling feed."

## Scope for v1

Full scope: live positions, arrival predictions, delays, alerts.
- Predictions: derived directly from simulated schedule + current position (no ML needed for v1).
- Delays/alerts: pure random injection for demo flavor (simplest option, chosen for now).

## Tech stack

- Backend: FastAPI, PostgreSQL (PostGIS + pgvector), SQLAlchemy async with asyncpg
- Messaging: FastStream + Kafka
- DI: Dishka
- Migrations: Goose
- Package management: uv
- Architecture: DDD / Hexagonal (ports & adapters)
- Frontend: React + MapLibre (GeoJSON line layer, animated markers)

## Static line/station data

- Not yet sourced. Plan: pull station nodes + line geometry from OpenStreetMap (Overpass API)
  as a starting point, then fill gaps by hand against the official map.
- Derive per-segment travel time from distance ÷ commercial speed (~46 km/h), adjusted per
  segment for underground vs. the elevated Circle Line.
- Lives in PostGIS: `stations` (Point), line segments (LineString).

## Data flow architecture

```
Train position sensors (track circuits underground, GPS on surface)
        -> Metro operator / ATS (publishes segment position, status)
        -> Ingestion service (validates, maps position to topology)
             <-> Topology DB (lines, stations — Postgres/PostGIS)
             <-- Demo simulator (swappable producer, dev only, feeds ingestion
                 the same shape a real feed would)
        -> Kafka (train.positions, network.alerts topics)
        -> Backend consumer -> current-state cache (Redis)
        -> WebSocket gateway (fans out to connected clients)
        -> Frontend map (React + MapLibre)
```

Key design decisions baked into this:
- The ingestion service resolves raw position into topology (line/segment/direction) —
  a raw coordinate or track-circuit ID means nothing on its own.
- A state cache (Redis) sits between Kafka and the WebSocket gateway so a newly connected
  client gets a current snapshot immediately, not just future deltas. Kafka is a stream,
  not a queryable "where is everything right now."
- The simulator is a swappable producer at the top of the pipeline — everything downstream
  (Kafka, consumer, WebSocket, frontend) stays identical when a real feed replaces it. This
  is the core credibility argument for the pitch.

## Domain model

- **`Line`, `Station`, `LineStation`** — topology aggregate (rarely changes). `LineStation` is
  the join that orders stations per line (`sequence`, `distance_to_next_m`), feeding both the
  frontend draw order and the simulator's travel-time math.
- **`TrainService`** — a *scheduled* run (line, direction, departure time). Belongs to a
  simulation/operations context.
- **`Train`** — the *live* vehicle instance actually moving (`status`, `current_position`,
  `current_segment_id`). Deliberately separate from `TrainService`: the simulator populates
  `Train` from `TrainService` entries today; a real operator feed would do the same from
  their dispatch data tomorrow. The schedule concept doesn't change, only who writes to
  the live table.
- **`Incident`** — attaches to a `Line` or `Station`, not to a specific train. Matches how
  delays are actually announced, and lets ETA recalculation cascade automatically to every
  affected train without special-casing.

```
LINE ||--o{ LINE_STATION : orders
STATION ||--o{ LINE_STATION : appears_on
LINE ||--o{ TRAIN_SERVICE : schedules
TRAIN_SERVICE ||--o| TRAIN : realized_by
LINE ||--o{ INCIDENT : affected_by
STATION ||--o{ INCIDENT : affected_by
```

## Kafka topics

**`train.positions`** — partition key: `train_id` (guarantees ordering per train; partitioning
by `line_id` instead would interleave updates from different trains and break smooth
interpolation on the frontend).

Fields: `train_id` (PK), `service_id` (FK), `line_id` (FK), `segment_id` (FK), `progress_pct`,
`lat`, `lon`, `direction`, `status`, `emitted_at`.

`segment_id` + `progress_pct` are sent alongside raw lat/lon so the frontend can interpolate
along the known line geometry rather than guessing which track a raw coordinate belongs to.

**`network.alerts`** — partition key: `incident_id` (keeps raised → escalated → cleared
updates ordered for the same incident).

Fields: `incident_id` (PK), `line_id` (FK), `station_id` (FK), `type`, `severity`,
`started_at`, `ended_at`.

Both topics reuse the existing `Event[T]` envelope pattern already built for the chat app's
Kafka publishing — only the payload shape is new.

Producer: ingestion service. Consumer: backend consumer, which writes to the Redis state cache.

## Hexagonal layout

- **Inbound adapters**: HTTP API (FastAPI, read queries — lines, stations) and the simulation
  clock (ticks every 1–2s; later, a real-feed adapter would sit alongside it, ideally
  implementing the same inbound port so both normalize to the same shape before hitting
  the domain).
- **Inbound ports**: use case interfaces.
- **Domain core**: `Train`, `Line`, `Station`, `Incident` aggregates + domain services. Only
  ever talks to interfaces, never to Postgres/Kafka/Redis directly.
- **Outbound ports**: repository and publisher interfaces.
- **Outbound adapters**: Postgres repo (topology, schedules), Kafka producer (publishes
  events), Redis cache (live state reads). Dishka binds these to the ports at startup — this
  is the mechanism that makes swapping the simulator for a real feed a wiring change, not a
  domain change.

Open question to resolve during build, not before: whether `Train` position updates go
through the full domain core every tick (aggregate load/validate/persist) or take a lighter
path and only hit the domain on notable events (arrival, delay) — a tick-rate/purism
tradeoff, not a correctness one at demo scale (~30–40 trains, 1–2s ticks).

## Build order

1. OSM data extraction (stations, line geometry) → fill gaps by hand
2. Domain models + Postgres/PostGIS schema (Goose migrations)
3. Simulation engine (domain service, tick-driven)
4. Kafka pipeline (FastStream producer/consumer, `Event[T]` envelopes)
5. WebSocket API + Redis state cache
6. Frontend map (React + MapLibre)

## Open / deferred decisions

- Exact source for full station coordinate data (OSM confirmed usable as a starting point,
  not yet pulled).
- Whether alerts stay pure-random or move to rule-based scenarios later (deferred, not ruled out).
- Real ATS/CBTC data format is unknown until ATTO/operator conversations happen — ingestion
  service's real-feed adapter is speculative until then.
