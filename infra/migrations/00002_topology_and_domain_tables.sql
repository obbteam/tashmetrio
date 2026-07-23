-- +goose Up
CREATE TABLE IF NOT EXISTS lines (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    name TEXT NOT NULL,
    geom geometry(LineString, 4326) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS idx_lines_geom ON lines USING GIST (geom);

CREATE TABLE IF NOT EXISTS stations (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    osm_id TEXT NOT NULL,
    name TEXT NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    PRIMARY KEY (id),
    UNIQUE (name),
    UNIQUE (osm_id)
);

CREATE INDEX IF NOT EXISTS idx_stations_geom ON stations USING GIST (geom);

CREATE TABLE IF NOT EXISTS line_stations (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    line_id UUID NOT NULL,
    station_id UUID NOT NULL,
    sequence INTEGER NOT NULL,
    distance_to_next_m INTEGER,
    PRIMARY KEY (id),
    FOREIGN KEY (line_id) REFERENCES lines (id) ON DELETE CASCADE,
    FOREIGN KEY (station_id) REFERENCES stations (id) ON DELETE CASCADE,
    UNIQUE (line_id, sequence),
    UNIQUE (line_id, station_id)
);

CREATE INDEX IF NOT EXISTS idx_line_stations_line_id ON line_stations (line_id);

CREATE INDEX IF NOT EXISTS idx_line_stations_station_id ON line_stations (station_id);

CREATE TABLE IF NOT EXISTS transfers (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    station_a_id UUID NOT NULL,
    station_b_id UUID NOT NULL,
    walk_time_s INTEGER NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (station_a_id) REFERENCES stations (id) ON DELETE CASCADE,
    FOREIGN KEY (station_b_id) REFERENCES stations (id) ON DELETE CASCADE,
    UNIQUE (station_a_id, station_b_id),
    CONSTRAINT tranfers_pair_should_be_single CHECK (station_a_id < station_b_id)
);

CREATE TABLE IF NOT EXISTS trains (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    name TEXT NOT NULL,
    line_id UUID NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    FOREIGN KEY (line_id) REFERENCES lines (id) ON DELETE CASCADE
);

CREATE TYPE direction_type as ENUM ('FORWARD', 'BACKWARD');

CREATE TABLE IF NOT EXISTS timetable_entries (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    train_id UUID NOT NULL,
    direction direction_type NOT NULL,
    departure_time TIME NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (train_id) REFERENCES trains (id) ON DELETE CASCADE
);

CREATE TYPE trip_status_type as ENUM ('ON TIME', 'DELAYED', 'CANCELLED');

CREATE TABLE IF NOT EXISTS trips (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    train_id UUID NOT NULL,
    timetable_entry_id UUID NOT NULL,
    departure_time TIMESTAMP WITH TIME ZONE NOT NULL,
    estimated_arrival_time TIMESTAMP WITH TIME ZONE NOT NULL,
    trip_status trip_status_type NOT NULL,
    current_segment_id UUID,
    progress_pct NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (
        progress_pct BETWEEN 0
        AND 100
    ),
    current_position geometry(Point, 4326),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (id),
    FOREIGN KEY (train_id) REFERENCES trains (id) ON DELETE CASCADE,
    FOREIGN KEY (timetable_entry_id) REFERENCES timetable_entries (id) ON DELETE CASCADE,
    FOREIGN KEY (current_segment_id) REFERENCES line_stations (id) ON DELETE SET NULL,
    EXCLUDE USING gist (
        train_id WITH =,
        tstzrange(departure_time, estimated_arrival_time) WITH &&
    ) -- the RANGE is [departure_time, estimated_arrival_time). Change this if need to protect against a,b b,c entries
);

CREATE INDEX IF NOT EXISTS idx_trips_current_segment_id ON trips (current_segment_id);

CREATE INDEX IF NOT EXISTS idx_trips_current_position ON trips USING GIST (current_position);

CREATE TABLE incidents (
    id UUID DEFAULT uuid_generate_v4() NOT NULL,
    line_id UUID,
    station_id UUID,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ended_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (id),
    FOREIGN KEY (station_id) REFERENCES stations (id) ON DELETE CASCADE,
    FOREIGN KEY (line_id) REFERENCES lines (id) ON DELETE CASCADE,
    CONSTRAINT line_or_station_not_null CHECK (
        line_id IS NOT NULL
        OR station_id IS NOT NULL
    )
);

CREATE INDEX idx_incidents_line_id ON incidents (line_id);

CREATE INDEX idx_incidents_station_id ON incidents (station_id);

-- +goose Down
DROP INDEX IF EXISTS idx_incidents_station_id;

DROP INDEX IF EXISTS idx_incidents_line_id;

DROP TABLE IF EXISTS incidents;

DROP INDEX IF EXISTS idx_trips_current_position;

DROP INDEX IF EXISTS idx_trips_current_segment_id;

DROP TABLE IF EXISTS trips;

DROP TYPE IF EXISTS trip_status_type CASCADE;

DROP TABLE IF EXISTS timetable_entries;

DROP TYPE IF EXISTS direction_type CASCADE;

DROP TABLE IF EXISTS trains;

DROP TABLE IF EXISTS transfers;

DROP INDEX IF EXISTS idx_line_stations_station_id;

DROP INDEX IF EXISTS idx_line_stations_line_id;

DROP TABLE IF EXISTS line_stations;

DROP INDEX IF EXISTS idx_stations_geom;

DROP TABLE IF EXISTS stations;

DROP INDEX IF EXISTS idx_lines_geom;

DROP TABLE IF EXISTS lines;