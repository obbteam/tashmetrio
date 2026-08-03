-- +goose Up
ALTER TABLE lines ADD COLUMN IF NOT EXISTS max_speed_mps NUMERIC(5, 2) NOT NULL;
ALTER TABLE lines ADD COLUMN IF NOT EXISTS max_acceleration_mps2 NUMERIC(5, 2) NOT NULL;

-- +goose Down
ALTER TABLE lines DROP COLUMN IF EXISTS max_speed_mps;
ALTER TABLE lines DROP COLUMN IF EXISTS max_acceleration_mps2;
