-- +goose Up
ALTER TABLE
    trips
ADD
    COLUMN IF NOT EXISTS current_segment_time TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now();

-- +goose Down
ALTER TABLE
    trips DROP COLUMN IF EXISTS current_segment_time;