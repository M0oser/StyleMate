CREATE TABLE IF NOT EXISTS user_profiles (
    user_id BIGINT PRIMARY KEY,
    owner_token TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT 'male',
    style_preferences TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_owner_token
    ON user_profiles(owner_token);

CREATE TABLE IF NOT EXISTS user_outfit_feedback (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    owner_token TEXT NOT NULL,
    feedback TEXT NOT NULL,
    scenario TEXT NOT NULL DEFAULT '',
    requested_style TEXT NOT NULL DEFAULT '',
    item_styles TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    item_categories TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    item_colors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    item_warmth TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    item_sources TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_outfit_feedback_user_id
    ON user_outfit_feedback(user_id);

CREATE INDEX IF NOT EXISTS idx_user_outfit_feedback_feedback
    ON user_outfit_feedback(feedback);
