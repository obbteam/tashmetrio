-- +goose Up
CREATE TABLE IF NOT EXISTS lines (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    name TEXT NOT NULL,
    geom geometry(LineString, 4326) NOT NULL,
    PRIMARY KEY (pk),
    UNIQUE (name)
);

CREATE INDEX IF NOT EXISTS idx_lines_geom ON lines USING GIST (geom);

CREATE TABLE IF NOT EXISTS stations (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    osm_id TEXT NOT NULL,
    name TEXT NOT NULL,
    geom geometry(Point, 4326) NOT NULL,
    PRIMARY KEY (pk),
    UNIQUE (name),
    UNIQUE (osm_id)
);

CREATE INDEX IF NOT EXISTS idx_stations_geom ON stations USING GIST (geom);

CREATE TABLE IF NOT EXISTS line_stations (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    line_pk UUID NOT NULL,
    station_pk UUID NOT NULL,
    sequence INTEGER NOT NULL,
    distance_to_next_m INTEGER,
    PRIMARY KEY (pk),
    FOREIGN KEY (line_pk) REFERENCES lines (pk) ON DELETE CASCADE,
    FOREIGN KEY (station_pk) REFERENCES stations (pk) ON DELETE CASCADE,
    UNIQUE (line_pk, sequence),
    UNIQUE (line_pk, station_pk)
);

CREATE INDEX IF NOT EXISTS idx_line_stations_line_pk ON line_stations (line_pk);

CREATE INDEX IF NOT EXISTS idx_line_stations_station_pk ON line_stations (station_pk);

CREATE TYPE direction_type as ENUM ('FORWARD', 'BACKWARD');

CREATE TABLE IF NOT EXISTS train_services (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    line_pk UUID NOT NULL,
    direction direction_type NOT NULL,
    departure_time TIME NOT NULL,
    PRIMARY KEY (pk),
    FOREIGN KEY (line_pk) REFERENCES lines (pk) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_train_services_line_pk ON train_services (line_pk);

CREATE TYPE train_status_type as ENUM ('ON TIME', 'DELAYED');

CREATE TABLE IF NOT EXISTS trains (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    service_pk UUID NOT NULL UNIQUE,
    status train_status_type NOT NULL,
    current_segment_pk UUID,
    progress_pct NUMERIC(5, 2) NOT NULL DEFAULT 0 CHECK (
        progress_pct BETWEEN 0
        AND 100
    ),
    current_position geometry(Point, 4326),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    PRIMARY KEY (pk),
    FOREIGN KEY (service_pk) REFERENCES train_services (pk) ON DELETE CASCADE,
    FOREIGN KEY (current_segment_pk) REFERENCES line_stations (pk) ON DELETE SET NULL
);

CREATE INDEX idx_trains_current_segment_pk ON trains (current_segment_pk);

CREATE INDEX idx_trains_current_position ON trains USING GIST (current_position);

CREATE TABLE incidents (
    pk UUID DEFAULT uuid_generate_v4() NOT NULL,
    line_pk UUID,
    station_pk UUID,
    type TEXT NOT NULL,
    severity TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ended_at TIMESTAMP WITH TIME ZONE,
    PRIMARY KEY (pk),
    FOREIGN KEY (station_pk) REFERENCES stations (pk) ON DELETE CASCADE,
    FOREIGN KEY (line_pk) REFERENCES lines (pk) ON DELETE CASCADE,
    CONSTRAINT line_or_station_not_null CHECK (line_pk IS NOT NULL OR station_pk IS NOT NULL)
);

CREATE INDEX idx_incidents_line_pk ON incidents (line_pk);

CREATE INDEX idx_incidents_station_pk ON incidents (station_pk);

-- +goose Down
DROP TYPE IF EXISTS direction_type CASCADE;

DROP TYPE IF EXISTS train_status_type CASCADE;

DROP INDEX IF EXISTS idx_incidents_station_pk;

DROP INDEX IF EXISTS idx_incidents_line_pk;

DROP INDEX IF EXISTS idx_trains_current_position;

DROP INDEX IF EXISTS idx_trains_current_segment_pk;

DROP INDEX IF EXISTS idx_train_services_line_pk;

DROP INDEX IF EXISTS idx_line_stations_station_pk;

DROP INDEX IF EXISTS idx_line_stations_line_pk;

DROP INDEX IF EXISTS idx_stations_geom;

DROP INDEX IF EXISTS idx_lines_geom;

DROP TABLE IF EXISTS incidents;

DROP TABLE IF EXISTS trains;

DROP TABLE IF EXISTS train_services;

DROP TABLE IF EXISTS line_stations;

DROP TABLE IF EXISTS stations;

DROP TABLE IF EXISTS lines;