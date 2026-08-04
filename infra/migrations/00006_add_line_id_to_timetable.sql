-- +goose Up
ALTER TABLE
    timetable_entries
ADD
    COLUMN IF NOT EXISTS line_id UUID NOT NULL REFERENCES lines(id);

ALTER TABLE
    trips
ADD
    COLUMN IF NOT EXISTS created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now();

-- +goose Down
ALTER TABLE
    timetable_entries DROP COLUMN IF EXISTS line_id;

ALTER TABLE
    trips DROP COLUMN IF EXISTS trips;