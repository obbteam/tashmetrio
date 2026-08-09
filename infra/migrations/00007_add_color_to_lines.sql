-- +goose Up
ALTER TABLE
    lines
ADD
    COLUMN IF NOT EXISTS color_hex TEXT;

UPDATE
    lines AS l
SET
    color_hex = v.color_hex
FROM
    (
        VALUES
            ('Chilanzor line', '#d60000'),
            ('Oʻzbekiston line', '#0300ee'),
            ('Yunusobod line', '#009900'),
            ('Circle line', '#ffed00')
    ) AS v(name, color_hex)
WHERE
    l.name = v.name;

-- +goose Down
ALTER TABLE
    lines DROP COLUMN IF EXISTS color_hex;