# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Tashmetrio's end goal is a **live map of Tashkent Metro trains**, built as a
pitch artifact for the metro operator (Toshkent Metropoliteni) — not just a
personal tool. Full design/rationale lives in `docs/PROJECT_CONTEXT.md`
(read it for anything below that needs more depth); `docs/*.mmd` and
`docs/tashkent_metro_domain_model.html` are diagrams generated from it, not
separate sources of truth.

**Current state of the repo**: only step 1 of the build order below exists —
the OSM topology extraction pipeline (`scripts/overpass_api.py`) and a
standalone HTML viewer to visually verify its output. Everything else in
this section (backend, Kafka, simulator, frontend) is planned, not yet
built. Don't assume services, directories, or dependencies described below
exist until you've checked.

## Collaboration mode

**Default to guidance and feedback, not implementation.** Do not write, edit,
or generate code unless the user explicitly asks for that specific piece of
work ("implement X", "write Y", "fix Z"). This holds even when a fix looks
small or obvious, and even mid-conversation after a design discussion — a
decision on *what* to do is not authorization to go write it.

- The default working mode is: the user writes the code, Claude reviews it,
  explains tradeoffs, answers questions, and flags issues. Treat
  `scripts/overpass_api.py` and `static/tashkent_metro_viewer.html` as the
  reference example — the user owns those, Claude's role there is
  verification/explanation, not authorship.
- Exploratory questions ("what do you think", "how should I approach this",
  "what's wrong with this") get a direct, concise answer in words — not a
  patch.
- The user may explicitly hand a piece of work off ("this part has no value
  to me, you write it" / "just implement this one") — only then treat that
  specific piece as fair game for direct implementation, and only for the
  scope actually handed off.
- If it's ambiguous whether a message is asking for discussion/review versus
  asking for code, ask before writing anything.
- This applies to all future build-order steps (domain models, simulator,
  Kafka pipeline, WebSocket API, frontend), not just the current OSM scope.

### Why simulated data, not a real feed

There is no public real-time GPS/AVL feed for Tashkent Metro. ATTO is the
fare-payment operator (turnstile taps, balances) and has no train position
data; real position would come from the operator's ATS/signaling system
(track-circuit occupancy), not GPS, since three of four lines run
underground. So for v1, simulated positions aren't a stopgap — they're the
only option, and that constraint is part of the pitch itself: the simulator
is a swappable producer at the top of the pipeline, and everything
downstream (Kafka, consumer, WebSocket, frontend) is meant to stay identical
when a real feed replaces it later.

### Planned tech stack

Backend: FastAPI, PostgreSQL (PostGIS + pgvector), SQLAlchemy async +
asyncpg. Messaging: FastStream + Kafka. DI: Dishka. Migrations: Goose.
Package management: uv. Architecture: DDD / hexagonal (ports & adapters).
Frontend: React + MapLibre (GeoJSON line layer, animated markers).

### Planned data flow

```
Train position sensors (track circuits underground, GPS on surface)
    -> Metro operator / ATS (publishes segment position, status)
    -> Ingestion service (resolves raw position -> topology: line/segment/direction)
         <-> Topology DB (lines, stations — Postgres/PostGIS)
         <-- Demo simulator (swappable producer, dev only)
    -> Kafka (train.positions keyed by train_id, network.alerts keyed by incident_id)
    -> Backend consumer -> current-state cache (Redis)
    -> WebSocket gateway (snapshot-on-connect from Redis, then live deltas)
    -> Frontend map (React + MapLibre)
```

A Redis state cache sits between Kafka and the WebSocket gateway so newly
connected clients get an immediate snapshot rather than waiting on future
deltas — Kafka is a stream, not a queryable "where is everything right now."

### Planned domain model

`Line`, `Station`, `LineStation` form the rarely-changing topology
aggregate — `LineStation` orders stations per line (`sequence`,
`distance_to_next_m`) and feeds both frontend draw order and the
simulator's travel-time math. `TrainService` is a *scheduled* run
(line, direction, departure time); `Train` is the *live* vehicle instance
(`status`, `current_position`, `current_segment_id`) — kept separate from
`TrainService` so the simulator (today) or a real operator feed (later) can
populate `Train` the same way, without changing the schedule concept.
`Incident` attaches to a `Line` or `Station`, not to a specific train,
matching how delays are actually announced and letting ETA recalculation
cascade to every affected train automatically.

```
LINE ||--o{ LINE_STATION : orders
STATION ||--o{ LINE_STATION : appears_on
LINE ||--o{ TRAIN_SERVICE : schedules
TRAIN_SERVICE ||--o| TRAIN : realized_by
LINE ||--o{ INCIDENT : affected_by
STATION ||--o{ INCIDENT : affected_by
```

### Build order

1. **OSM data extraction (stations, line geometry) → fill gaps by hand — this repo's current scope.**
2. Domain models + Postgres/PostGIS schema (Goose migrations)
3. Simulation engine (domain service, tick-driven)
4. Kafka pipeline (FastStream producer/consumer, `Event[T]` envelopes)
5. WebSocket API + Redis state cache
6. Frontend map (React + MapLibre)

### Open / deferred decisions

- Whether `Train` position updates go through the full domain core every
  tick, or take a lighter path for high-frequency ticks vs. notable events
  (arrival, delay) — a tick-rate/purism tradeoff, not a correctness one at
  demo scale (~30–40 trains, 1–2s ticks).
- Whether alerts stay pure-random or move to rule-based scenarios later.
- Real ATS/CBTC data format is unknown until operator conversations happen.

## Commands

Activate the venv before running anything (Python 3.14):

```bash
source venv/bin/activate
```

Fetch/regenerate the OSM data (writes to `./osm_data` by default):

```bash
python scripts/overpass_api.py [--out-dir ./osm_data]
```

This hits the live public Overpass API (`overpass-api.de`) over the network —
no local server, no test suite, no build/lint step exists in this repo.

To visually verify a fetch, open `static/tashkent_metro_viewer.html` in a
browser and drop in the generated `lines.geojson` and `stations.geojson`
(via the file inputs in the sidebar — it does not fetch data itself).

## Architecture of the current code

**`scripts/overpass_api.py`** is the entire data pipeline, run as a one-shot
script (not a library/package despite living under `scripts/` with an
`__init__.py`). It runs in two passes against Overpass:

1. **Route relations** (`route=subway`) — gives line geometry (way members
   with `role=""`) and bare stop-position nodes (`role=stop`, unnamed).
2. **Station nodes** (`railway=station`+`station=subway`, or
   `public_transport=station`+`station=subway`) — gives the actual named
   station entities, queried separately because in Tashkent's OSM data they
   are not name-bearing members of the route relations.

The key non-obvious step is **snapping**: named stations from pass 2 aren't
directly ordered by the route relation, so each station is projected onto its
line's stitched polyline (haversine + planar local projection,
`project_point_to_polyline`), and the resulting arc-length determines station
order along the line. `STATION_SNAP_THRESHOLD_M` (50m) controls how far a
station may sit from a line's geometry and still count as "on" it.

OSM also splits each physical line into **two route relations** (one per
direction) sharing a `ref` tag — `dedupe_lines_by_ref` collapses these to one
relation per line before geometry stitching.

Output files (also checked into `osm_data/`) chain together:

- `stations.geojson` — all named station points.
- `lines.geojson` — one LineString per physical line, stitched from way
  segments in `stitch_line_geometry` (greedy endpoint-matching; order isn't
  guaranteed in OSM way lists).
- `line_stations.json` — per-line ordered station sequence with
  inter-station distances, derived from the snap step above. This is the
  file meant to seed a `LINE_STATION`-style table downstream.
- `res.json` — raw Overpass API response, kept for debugging fetches.

**`static/tashkent_metro_viewer.html`** is a self-contained (no build step,
no dependencies) HTML/JS/SVG viewer. It re-implements the same
haversine/snap-to-line logic independently in JS
(`STATION_LINE_THRESHOLD_M`, 300m — deliberately looser than the Python
side's 50m, since it's just for display grouping) to determine which
line(s) a station belongs to for the legend/toggle UI. It does its own
pan/zoom via a manual SVG transform (`view.scale/tx/ty`), not a mapping
library.

## Working with Overpass/OSM data

- If a fetch returns 0 lines or 0 stations, the bbox (`TASHKENT_BBOX`) or the
  tag scheme is the first thing to check — the script's docstring and inline
  warnings explain the specific tags expected for this dataset.
- `STATION_SNAP_THRESHOLD_M` is the main tunable if stations are
  missing/misattributed from a line after a fetch.
- After regenerating, check `line_stations.json` station counts/order
  against the official map — this is a heuristic pipeline (snapping,
  greedy stitching) over inherently inconsistent crowdsourced OSM tagging.
