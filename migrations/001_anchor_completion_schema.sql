CREATE TABLE IF NOT EXISTS stores (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    base_url TEXT NOT NULL,
    parser_key TEXT NOT NULL UNIQUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_runs (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT NOT NULL REFERENCES stores(id),
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at TIMESTAMPTZ,
    fetched_count INTEGER NOT NULL DEFAULT 0,
    curated_count INTEGER NOT NULL DEFAULT 0,
    persisted_count INTEGER NOT NULL DEFAULT 0,
    skipped_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS category_role_map (
    category TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    layer_role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS scenario_profiles_reference (
    scenario_key TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    required_roles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    optional_roles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    season_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    occasion_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS shop_products (
    id BIGSERIAL PRIMARY KEY,
    store_id BIGINT NOT NULL REFERENCES stores(id),
    source_product_id TEXT NOT NULL,
    title TEXT NOT NULL,
    brand TEXT,
    category TEXT NOT NULL,
    subcategory TEXT,
    gender_target TEXT NOT NULL,
    current_price NUMERIC(12, 2),
    old_price NUMERIC(12, 2),
    currency TEXT NOT NULL DEFAULT 'RUB',
    product_url TEXT NOT NULL,
    primary_image_url TEXT,
    description_raw TEXT,
    material_raw TEXT,
    fit_raw TEXT,
    color_raw TEXT,
    availability_raw TEXT,
    metadata_quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    is_curated BOOLEAN NOT NULL DEFAULT FALSE,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (store_id, source_product_id)
);

CREATE INDEX IF NOT EXISTS idx_shop_products_category ON shop_products(category);
CREATE INDEX IF NOT EXISTS idx_shop_products_gender ON shop_products(gender_target);
CREATE INDEX IF NOT EXISTS idx_shop_products_curated ON shop_products(is_curated);
CREATE INDEX IF NOT EXISTS idx_shop_products_price ON shop_products(current_price);

CREATE TABLE IF NOT EXISTS shop_product_images (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES shop_products(id) ON DELETE CASCADE,
    image_url TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, image_url)
);

CREATE TABLE IF NOT EXISTS shop_product_sizes (
    id BIGSERIAL PRIMARY KEY,
    product_id BIGINT NOT NULL REFERENCES shop_products(id) ON DELETE CASCADE,
    size_label TEXT NOT NULL,
    size_system TEXT NOT NULL DEFAULT '',
    size_value TEXT,
    availability TEXT NOT NULL DEFAULT 'unknown',
    size_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (product_id, size_label, size_system)
);

CREATE TABLE IF NOT EXISTS shop_product_tags (
    product_id BIGINT PRIMARY KEY REFERENCES shop_products(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    style_primary TEXT,
    style_secondary TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    formality TEXT,
    budget_tier TEXT,
    season_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    weather_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    occasion_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    scenario_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    warmth_level SMALLINT NOT NULL DEFAULT 0,
    fit_type TEXT,
    silhouette TEXT,
    color_family TEXT,
    pattern TEXT,
    body_fit_notes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    body_size_relevance TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    pairing_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    avoid_pairing_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    source_preference_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    image_quality_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    metadata_completeness_score NUMERIC(5, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_product_tags_role ON shop_product_tags(role);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_season ON shop_product_tags USING GIN (season_tags);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_weather ON shop_product_tags USING GIN (weather_tags);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_occasion ON shop_product_tags USING GIN (occasion_tags);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_scenario ON shop_product_tags USING GIN (scenario_tags);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_style_secondary ON shop_product_tags USING GIN (style_secondary);
CREATE INDEX IF NOT EXISTS idx_shop_product_tags_body_size_relevance ON shop_product_tags USING GIN (body_size_relevance);

CREATE TABLE IF NOT EXISTS user_wardrobe_items (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT,
    gender_target TEXT NOT NULL,
    primary_image_url TEXT,
    color_raw TEXT,
    fit_raw TEXT,
    material_raw TEXT,
    role TEXT NOT NULL,
    style_primary TEXT,
    style_secondary TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    formality TEXT,
    season_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    weather_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    occasion_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    warmth_level SMALLINT NOT NULL DEFAULT 0,
    notes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_wardrobe_items_user ON user_wardrobe_items(user_id);
CREATE INDEX IF NOT EXISTS idx_user_wardrobe_items_role ON user_wardrobe_items(role);
