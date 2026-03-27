ALTER TABLE shop_product_sizes
    ALTER COLUMN size_system SET DEFAULT '';

UPDATE shop_product_sizes
SET size_system = ''
WHERE size_system IS NULL;

ALTER TABLE shop_product_sizes
    ALTER COLUMN size_system SET NOT NULL;

ALTER TABLE shop_product_tags
    ADD COLUMN IF NOT EXISTS body_size_relevance TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[];

CREATE INDEX IF NOT EXISTS idx_shop_product_tags_body_size_relevance
    ON shop_product_tags USING GIN (body_size_relevance);
