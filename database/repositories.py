from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Sequence

from psycopg.types.json import Jsonb

from database.postgres import PostgresDatabase
from normalizers.products import NormalizedShopProduct
from vocab.fashion import CATEGORY_ROLE_REFERENCE, COMPLETION_SCENARIOS, STORE_DEFINITIONS


class CompletionDataRepository:
    """Repository layer for the PostgreSQL completion catalog."""

    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def initialize_schema(self, migrations_path: Path) -> None:
        migration_files = [migrations_path] if migrations_path.is_file() else sorted(migrations_path.glob("*.sql"))
        with self.database.connection() as conn:
            conn.execute("SELECT pg_advisory_xact_lock(%s)", (814239,))
            for migration_file in migration_files:
                conn.execute(migration_file.read_text(encoding="utf-8"))

    def seed_reference_data(self) -> None:
        with self.database.connection() as conn:
            for store in STORE_DEFINITIONS:
                conn.execute(
                    """
                    INSERT INTO stores (name, base_url, parser_key, is_active, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (parser_key) DO UPDATE
                    SET name = EXCLUDED.name,
                        base_url = EXCLUDED.base_url,
                        is_active = EXCLUDED.is_active,
                        notes = EXCLUDED.notes,
                        updated_at = NOW()
                    """,
                    (store.name, store.base_url, store.parser_key, store.is_active, store.notes),
                )

            for category, role, layer_role in CATEGORY_ROLE_REFERENCE:
                conn.execute(
                    """
                    INSERT INTO category_role_map (category, role, layer_role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (category) DO UPDATE
                    SET role = EXCLUDED.role,
                        layer_role = EXCLUDED.layer_role
                    """,
                    (category, role, layer_role),
                )

            for scenario_key, payload in COMPLETION_SCENARIOS.items():
                conn.execute(
                    """
                    INSERT INTO scenario_profiles_reference (
                        scenario_key,
                        label,
                        required_roles,
                        optional_roles,
                        season_tags,
                        occasion_tags,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (scenario_key) DO UPDATE
                    SET label = EXCLUDED.label,
                        required_roles = EXCLUDED.required_roles,
                        optional_roles = EXCLUDED.optional_roles,
                        season_tags = EXCLUDED.season_tags,
                        occasion_tags = EXCLUDED.occasion_tags,
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        scenario_key,
                        payload["label"],
                        payload["required_roles"],
                        payload["optional_roles"],
                        payload["season_tags"],
                        payload["occasion_tags"],
                        Jsonb(payload),
                    ),
                )

    def start_ingestion_run(self, store_key: str, metadata: dict[str, Any] | None = None) -> int:
        store_id = self._get_store_id(store_key)
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO ingestion_runs (store_id, status, metadata)
                VALUES (%s, 'running', %s)
                RETURNING id
                """,
                (store_id, Jsonb(metadata or {})),
            ).fetchone()
            return int(row["id"])

    def finish_ingestion_run(
        self,
        run_id: int,
        *,
        status: str,
        fetched_count: int,
        curated_count: int,
        persisted_count: int,
        skipped_count: int,
        error_count: int,
        error_message: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        with self.database.connection() as conn:
            conn.execute(
                """
                UPDATE ingestion_runs
                SET status = %s,
                    finished_at = NOW(),
                    fetched_count = %s,
                    curated_count = %s,
                    persisted_count = %s,
                    skipped_count = %s,
                    error_count = %s,
                    error_message = %s,
                    metadata = %s
                WHERE id = %s
                """,
                (
                    status,
                    fetched_count,
                    curated_count,
                    persisted_count,
                    skipped_count,
                    error_count,
                    error_message,
                    Jsonb(metadata or {}),
                    run_id,
                ),
            )

    def upsert_shop_product(
        self,
        product: NormalizedShopProduct,
        *,
        is_curated: bool,
        metadata_quality_score: float,
        tags: dict[str, Any],
    ) -> int:
        store_id = self._get_store_id(product.source_store)
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO shop_products (
                    store_id,
                    source_product_id,
                    title,
                    brand,
                    category,
                    subcategory,
                    gender_target,
                    current_price,
                    old_price,
                    currency,
                    product_url,
                    primary_image_url,
                    description_raw,
                    material_raw,
                    fit_raw,
                    color_raw,
                    availability_raw,
                    metadata_quality_score,
                    is_curated,
                    raw_payload,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                ON CONFLICT (store_id, source_product_id) DO UPDATE
                SET title = EXCLUDED.title,
                    brand = EXCLUDED.brand,
                    category = EXCLUDED.category,
                    subcategory = EXCLUDED.subcategory,
                    gender_target = EXCLUDED.gender_target,
                    current_price = EXCLUDED.current_price,
                    old_price = EXCLUDED.old_price,
                    currency = EXCLUDED.currency,
                    product_url = EXCLUDED.product_url,
                    primary_image_url = EXCLUDED.primary_image_url,
                    description_raw = EXCLUDED.description_raw,
                    material_raw = EXCLUDED.material_raw,
                    fit_raw = EXCLUDED.fit_raw,
                    color_raw = EXCLUDED.color_raw,
                    availability_raw = EXCLUDED.availability_raw,
                    metadata_quality_score = EXCLUDED.metadata_quality_score,
                    is_curated = EXCLUDED.is_curated,
                    raw_payload = EXCLUDED.raw_payload,
                    updated_at = NOW()
                RETURNING id
                """,
                (
                    store_id,
                    product.source_product_id,
                    product.title,
                    product.brand,
                    product.category,
                    product.subcategory,
                    product.gender_target,
                    product.current_price,
                    product.old_price,
                    product.currency,
                    product.product_url,
                    product.primary_image_url,
                    product.description_raw,
                    product.material_raw,
                    product.fit_raw,
                    product.color_raw,
                    product.availability_raw,
                    metadata_quality_score,
                    is_curated,
                    Jsonb(product.raw_payload or {}),
                ),
            ).fetchone()
            product_id = int(row["id"])
            self._replace_product_images(conn, product_id, product.images)
            self._replace_product_sizes(conn, product_id, product.sizes)
            self._upsert_product_tags(conn, product_id, tags)
            return product_id

    def upsert_user_wardrobe_item(self, payload: dict[str, Any]) -> int:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO user_wardrobe_items (
                    user_id,
                    title,
                    category,
                    subcategory,
                    gender_target,
                    primary_image_url,
                    color_raw,
                    fit_raw,
                    material_raw,
                    role,
                    style_primary,
                    style_secondary,
                    formality,
                    season_tags,
                    weather_tags,
                    occasion_tags,
                    warmth_level,
                    notes,
                    updated_at
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                )
                RETURNING id
                """,
                (
                    payload["user_id"],
                    payload["title"],
                    payload["category"],
                    payload.get("subcategory"),
                    payload.get("gender_target", "women"),
                    payload.get("primary_image_url"),
                    payload.get("color_raw"),
                    payload.get("fit_raw"),
                    payload.get("material_raw"),
                    payload["role"],
                    payload.get("style_primary"),
                    payload.get("style_secondary", []),
                    payload.get("formality"),
                    payload.get("season_tags", []),
                    payload.get("weather_tags", []),
                    payload.get("occasion_tags", []),
                    payload.get("warmth_level", 0),
                    Jsonb(payload.get("notes", {})),
                ),
            ).fetchone()
            return int(row["id"])

    def list_user_wardrobe_items(
        self,
        *,
        user_id: int,
        item_ids: Sequence[int] | None = None,
    ) -> list[dict[str, Any]]:
        conditions = ["user_id = %s"]
        params: list[Any] = [user_id]

        if item_ids:
            conditions.append("id = ANY(%s)")
            params.append(list(item_ids))

        query = f"""
            SELECT
                id,
                user_id,
                title,
                category,
                subcategory,
                gender_target,
                primary_image_url,
                color_raw,
                fit_raw,
                material_raw,
                role,
                style_primary,
                style_secondary,
                formality,
                season_tags,
                weather_tags,
                occasion_tags,
                warmth_level,
                notes,
                created_at,
                updated_at
            FROM user_wardrobe_items
            WHERE {' AND '.join(conditions)}
            ORDER BY id
        """
        with self.database.connection(autocommit=True) as conn:
            rows = [dict(row) for row in conn.execute(query, params).fetchall()]

        if item_ids:
            index_map = {int(item_id): position for position, item_id in enumerate(item_ids)}
            rows.sort(key=lambda row: index_map.get(int(row["id"]), len(index_map)))
        return rows

    def delete_user_wardrobe_items(self, *, user_id: int, item_ids: Sequence[int] | None = None) -> int:
        conditions = ["user_id = %s"]
        params: list[Any] = [user_id]

        if item_ids:
            conditions.append("id = ANY(%s)")
            params.append(list(item_ids))

        with self.database.connection() as conn:
            row = conn.execute(
                f"DELETE FROM user_wardrobe_items WHERE {' AND '.join(conditions)} RETURNING id",
                params,
            ).fetchall()
            return len(row)

    def get_or_create_user_profile(self, *, user_id: int, owner_token: str) -> dict[str, Any]:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO user_profiles (user_id, owner_token)
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE
                SET owner_token = EXCLUDED.owner_token,
                    last_active_at = NOW()
                RETURNING
                    user_id,
                    owner_token,
                    display_name,
                    gender,
                    style_preferences,
                    onboarding_completed,
                    created_at,
                    updated_at,
                    last_active_at
                """,
                (user_id, owner_token),
            ).fetchone()
        return dict(row)

    def update_user_profile(
        self,
        *,
        user_id: int,
        owner_token: str,
        display_name: str,
        gender: str,
        style_preferences: Sequence[str],
        onboarding_completed: bool,
    ) -> dict[str, Any]:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                UPDATE user_profiles
                SET owner_token = %s,
                    display_name = %s,
                    gender = %s,
                    style_preferences = %s,
                    onboarding_completed = %s,
                    updated_at = NOW(),
                    last_active_at = NOW()
                WHERE user_id = %s
                RETURNING
                    user_id,
                    owner_token,
                    display_name,
                    gender,
                    style_preferences,
                    onboarding_completed,
                    created_at,
                    updated_at,
                    last_active_at
                """,
                (
                    owner_token,
                    display_name,
                    gender,
                    list(style_preferences),
                    onboarding_completed,
                    user_id,
                ),
            ).fetchone()
        return dict(row)

    def save_user_feedback(
        self,
        *,
        user_id: int,
        owner_token: str,
        feedback: str,
        scenario: str,
        requested_style: str,
        item_styles: Sequence[str],
        item_categories: Sequence[str],
        item_colors: Sequence[str],
        item_warmth: Sequence[str],
        item_sources: Sequence[str],
    ) -> dict[str, Any]:
        with self.database.connection() as conn:
            row = conn.execute(
                """
                INSERT INTO user_outfit_feedback (
                    user_id,
                    owner_token,
                    feedback,
                    scenario,
                    requested_style,
                    item_styles,
                    item_categories,
                    item_colors,
                    item_warmth,
                    item_sources
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    id,
                    user_id,
                    owner_token,
                    feedback,
                    scenario,
                    requested_style,
                    item_styles,
                    item_categories,
                    item_colors,
                    item_warmth,
                    item_sources,
                    created_at
                """,
                (
                    user_id,
                    owner_token,
                    feedback,
                    scenario,
                    requested_style,
                    list(item_styles),
                    list(item_categories),
                    list(item_colors),
                    list(item_warmth),
                    list(item_sources),
                ),
            ).fetchone()
        return dict(row)

    def list_user_feedback(self, *, user_id: int) -> list[dict[str, Any]]:
        with self.database.connection(autocommit=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    user_id,
                    owner_token,
                    feedback,
                    scenario,
                    requested_style,
                    item_styles,
                    item_categories,
                    item_colors,
                    item_warmth,
                    item_sources,
                    created_at
                FROM user_outfit_feedback
                WHERE user_id = %s
                ORDER BY id ASC
                """,
                (user_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def list_products_for_enrichment(
        self,
        *,
        store_key: str | None = None,
        curated_only: bool = False,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []

        if store_key:
            conditions.append("s.parser_key = %s")
            params.append(store_key)
        if curated_only:
            conditions.append("p.is_curated = TRUE")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_sql = "LIMIT %s" if limit is not None else ""
        if limit is not None:
            params.append(limit)

        query = f"""
            SELECT
                p.*,
                s.parser_key AS source_store,
                COALESCE(
                    jsonb_agg(DISTINCT jsonb_build_object('image_url', i.image_url, 'sort_order', i.sort_order))
                    FILTER (WHERE i.id IS NOT NULL),
                    '[]'::jsonb
                ) AS images,
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'size_label', z.size_label,
                            'size_system', z.size_system,
                            'size_value', z.size_value,
                            'availability', z.availability,
                            'size_notes', z.size_notes
                        )
                    ) FILTER (WHERE z.id IS NOT NULL),
                    '[]'::jsonb
                ) AS sizes
            FROM shop_products p
            JOIN stores s ON s.id = p.store_id
            LEFT JOIN shop_product_images i ON i.product_id = p.id
            LEFT JOIN shop_product_sizes z ON z.product_id = p.id
            {where_sql}
            GROUP BY p.id, s.parser_key
            ORDER BY p.updated_at DESC
            {limit_sql}
        """
        with self.database.connection(autocommit=True) as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def list_catalog_products_for_quality_audit(
        self,
        *,
        store_key: str | None = None,
        curated_only: bool = True,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []

        if store_key:
            conditions.append("s.parser_key = %s")
            params.append(store_key)
        if curated_only:
            conditions.append("p.is_curated = TRUE")

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        limit_sql = "LIMIT %s" if limit is not None else ""
        if limit is not None:
            params.append(limit)

        query = f"""
            SELECT
                p.id,
                p.source_product_id,
                p.title,
                p.category,
                p.subcategory,
                p.gender_target,
                p.current_price,
                p.color_raw,
                p.material_raw,
                p.fit_raw,
                p.metadata_quality_score,
                s.parser_key AS store_key,
                t.role,
                t.style_primary,
                t.formality,
                t.season_tags,
                t.weather_tags,
                t.occasion_tags,
                t.scenario_tags,
                t.warmth_level,
                t.color_family,
                t.body_fit_notes,
                t.body_size_relevance,
                COALESCE(
                    jsonb_agg(
                        DISTINCT jsonb_build_object(
                            'size_label', z.size_label,
                            'size_system', z.size_system,
                            'size_value', z.size_value,
                            'availability', z.availability,
                            'size_notes', z.size_notes
                        )
                    ) FILTER (WHERE z.id IS NOT NULL),
                    '[]'::jsonb
                ) AS sizes
            FROM shop_products p
            JOIN stores s ON s.id = p.store_id
            LEFT JOIN shop_product_tags t ON t.product_id = p.id
            LEFT JOIN shop_product_sizes z ON z.product_id = p.id
            {where_sql}
            GROUP BY p.id, s.parser_key, t.product_id
            ORDER BY p.updated_at DESC
            {limit_sql}
        """
        with self.database.connection(autocommit=True) as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def refresh_shop_product_tags(self, product_id: int, tags: dict[str, Any], metadata_quality_score: float) -> None:
        with self.database.connection() as conn:
            conn.execute(
                "UPDATE shop_products SET metadata_quality_score = %s, updated_at = NOW() WHERE id = %s",
                (metadata_quality_score, product_id),
            )
            self._upsert_product_tags(conn, product_id, tags)

    def get_scenario_profile(self, scenario_key: str) -> dict[str, Any]:
        with self.database.connection(autocommit=True) as conn:
            row = conn.execute(
                """
                SELECT
                    scenario_key,
                    label,
                    required_roles,
                    optional_roles,
                    season_tags,
                    occasion_tags,
                    metadata
                FROM scenario_profiles_reference
                WHERE scenario_key = %s
                """,
                (scenario_key,),
            ).fetchone()
        if not row:
            raise KeyError(f"Unknown scenario profile: {scenario_key}")
        return dict(row)

    def find_completion_candidates_for_scenario(
        self,
        *,
        scenario_key: str,
        missing_roles: Sequence[str],
        gender_target: str,
        season_tags: Sequence[str] | None = None,
        weather_tags: Sequence[str] | None = None,
        budget_tiers: Sequence[str] | None = None,
        max_price: float | None = None,
        excluded_product_ids: Sequence[int] | None = None,
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        profile = self.get_scenario_profile(scenario_key)
        metadata = profile.get("metadata") or {}
        scenario_filters = [scenario_key, *(metadata.get("scenario_aliases") or [])]
        effective_season_tags = list(season_tags or profile.get("season_tags") or [])
        if effective_season_tags == ["all_season"]:
            effective_season_tags = []
        effective_weather_tags = list(weather_tags or metadata.get("weather_tags") or [])

        return self.find_completion_candidates(
            missing_roles=missing_roles,
            gender_target=gender_target,
            season_tags=effective_season_tags or None,
            weather_tags=effective_weather_tags or None,
            scenario_tags=scenario_filters,
            budget_tiers=budget_tiers,
            max_price=max_price,
            excluded_product_ids=excluded_product_ids,
            limit=limit,
        )

    def find_completion_candidates(
        self,
        *,
        missing_roles: Sequence[str],
        gender_target: str,
        season_tags: Sequence[str] | None = None,
        weather_tags: Sequence[str] | None = None,
        scenario_tags: Sequence[str] | None = None,
        budget_tiers: Sequence[str] | None = None,
        max_price: float | None = None,
        excluded_product_ids: Sequence[int] | None = None,
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        missing_roles = list(dict.fromkeys(missing_roles))
        season_tags = list(dict.fromkeys(season_tags or []))
        weather_tags = list(dict.fromkeys(weather_tags or []))
        scenario_tags = list(dict.fromkeys(scenario_tags or []))
        budget_tiers = list(dict.fromkeys(budget_tiers or []))
        conditions = [
            "p.is_curated = TRUE",
            "s.is_active = TRUE",
            "p.gender_target IN (%s, 'unisex', 'broad')",
            "t.role = ANY(%s)",
        ]
        params: list[Any] = [gender_target, missing_roles]

        if season_tags:
            conditions.append("t.season_tags && %s")
            params.append(season_tags)
        if weather_tags:
            conditions.append("t.weather_tags && %s")
            params.append(weather_tags)
        if scenario_tags:
            conditions.append("t.scenario_tags && %s")
            params.append(scenario_tags)
        if budget_tiers:
            conditions.append("t.budget_tier = ANY(%s)")
            params.append(budget_tiers)
        if max_price is not None:
            conditions.append("p.current_price <= %s")
            params.append(max_price)
        if excluded_product_ids:
            conditions.append("NOT (p.id = ANY(%s))")
            params.append(list(excluded_product_ids))

        params.append(max(limit * 5, 120))
        query = f"""
            SELECT
                p.*,
                s.name AS store_name,
                s.parser_key AS store_key,
                s.base_url,
                t.role,
                t.style_primary,
                t.style_secondary,
                t.formality,
                t.budget_tier,
                t.season_tags,
                t.weather_tags,
                t.occasion_tags,
                t.scenario_tags,
                t.warmth_level,
                t.color_family,
                t.body_size_relevance,
                t.pairing_tags,
                t.avoid_pairing_tags,
                t.source_preference_score,
                t.image_quality_score,
                t.metadata_completeness_score
            FROM shop_products p
            JOIN stores s ON s.id = p.store_id
            JOIN shop_product_tags t ON t.product_id = p.id
            WHERE {' AND '.join(conditions)}
            ORDER BY
                t.source_preference_score DESC,
                t.metadata_completeness_score DESC,
                p.metadata_quality_score DESC,
                p.updated_at DESC
            LIMIT %s
        """
        with self.database.connection(autocommit=True) as conn:
            rows = conn.execute(query, params).fetchall()
        candidates = [dict(row) for row in rows]
        ranked = self._rank_completion_candidates(
            candidates,
            missing_roles=missing_roles,
            season_tags=season_tags,
            weather_tags=weather_tags,
            scenario_tags=scenario_tags,
        )
        deduped = self._dedupe_completion_candidates(ranked)
        return deduped[:limit]

    def list_stores(self) -> list[dict[str, Any]]:
        with self.database.connection(autocommit=True) as conn:
            rows = conn.execute("SELECT * FROM stores ORDER BY parser_key").fetchall()
        return [dict(row) for row in rows]

    def _get_store_id(self, store_key: str) -> int:
        with self.database.connection(autocommit=True) as conn:
            row = conn.execute(
                "SELECT id FROM stores WHERE parser_key = %s",
                (store_key,),
            ).fetchone()
        if not row:
            raise KeyError(f"Store '{store_key}' is not registered. Run database initialization first.")
        return int(row["id"])

    @staticmethod
    def _replace_product_images(conn: Any, product_id: int, images: Iterable[Any]) -> None:
        conn.execute("DELETE FROM shop_product_images WHERE product_id = %s", (product_id,))
        for image in images:
            conn.execute(
                """
                INSERT INTO shop_product_images (product_id, image_url, sort_order)
                VALUES (%s, %s, %s)
                ON CONFLICT (product_id, image_url) DO UPDATE
                SET sort_order = EXCLUDED.sort_order
                """,
                (product_id, image.url, image.sort_order),
            )

    @staticmethod
    def _replace_product_sizes(conn: Any, product_id: int, sizes: Iterable[Any]) -> None:
        conn.execute("DELETE FROM shop_product_sizes WHERE product_id = %s", (product_id,))
        for size in sizes:
            conn.execute(
                """
                INSERT INTO shop_product_sizes (
                    product_id,
                    size_label,
                    size_system,
                    size_value,
                    availability,
                    size_notes
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    product_id,
                    size.size_label,
                    size.size_system or "",
                    size.size_value,
                    size.availability,
                    size.size_notes,
                ),
            )

    @staticmethod
    def _upsert_product_tags(conn: Any, product_id: int, tags: dict[str, Any]) -> None:
        conn.execute(
            """
            INSERT INTO shop_product_tags (
                product_id,
                role,
                style_primary,
                style_secondary,
                formality,
                budget_tier,
                season_tags,
                weather_tags,
                occasion_tags,
                scenario_tags,
                warmth_level,
                fit_type,
                silhouette,
                color_family,
                pattern,
                body_fit_notes,
                body_size_relevance,
                pairing_tags,
                avoid_pairing_tags,
                source_preference_score,
                image_quality_score,
                metadata_completeness_score,
                updated_at
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
            )
            ON CONFLICT (product_id) DO UPDATE
            SET role = EXCLUDED.role,
                style_primary = EXCLUDED.style_primary,
                style_secondary = EXCLUDED.style_secondary,
                formality = EXCLUDED.formality,
                budget_tier = EXCLUDED.budget_tier,
                season_tags = EXCLUDED.season_tags,
                weather_tags = EXCLUDED.weather_tags,
                occasion_tags = EXCLUDED.occasion_tags,
                scenario_tags = EXCLUDED.scenario_tags,
                warmth_level = EXCLUDED.warmth_level,
                fit_type = EXCLUDED.fit_type,
                silhouette = EXCLUDED.silhouette,
                color_family = EXCLUDED.color_family,
                pattern = EXCLUDED.pattern,
                body_fit_notes = EXCLUDED.body_fit_notes,
                body_size_relevance = EXCLUDED.body_size_relevance,
                pairing_tags = EXCLUDED.pairing_tags,
                avoid_pairing_tags = EXCLUDED.avoid_pairing_tags,
                source_preference_score = EXCLUDED.source_preference_score,
                image_quality_score = EXCLUDED.image_quality_score,
                metadata_completeness_score = EXCLUDED.metadata_completeness_score,
                updated_at = NOW()
            """,
            (
                product_id,
                tags["role"],
                tags.get("style_primary"),
                tags.get("style_secondary", []),
                tags.get("formality"),
                tags.get("budget_tier"),
                tags.get("season_tags", []),
                tags.get("weather_tags", []),
                tags.get("occasion_tags", []),
                tags.get("scenario_tags", []),
                tags.get("warmth_level", 0),
                tags.get("fit_type"),
                tags.get("silhouette"),
                tags.get("color_family"),
                tags.get("pattern"),
                tags.get("body_fit_notes", []),
                tags.get("body_size_relevance", []),
                tags.get("pairing_tags", []),
                tags.get("avoid_pairing_tags", []),
                tags.get("source_preference_score", 0),
                tags.get("image_quality_score", 0),
                tags.get("metadata_completeness_score", 0),
            ),
        )

    @staticmethod
    def _rank_completion_candidates(
        candidates: list[dict[str, Any]],
        *,
        missing_roles: Sequence[str],
        season_tags: Sequence[str],
        weather_tags: Sequence[str],
        scenario_tags: Sequence[str],
    ) -> list[dict[str, Any]]:
        return sorted(
            candidates,
            key=lambda row: CompletionDataRepository._completion_sort_key(
                row,
                missing_roles=missing_roles,
                season_tags=season_tags,
                weather_tags=weather_tags,
                scenario_tags=scenario_tags,
            ),
            reverse=True,
        )

    @staticmethod
    def _completion_sort_key(
        row: dict[str, Any],
        *,
        missing_roles: Sequence[str],
        season_tags: Sequence[str],
        weather_tags: Sequence[str],
        scenario_tags: Sequence[str],
    ) -> tuple[float, ...]:
        role = row.get("role")
        row_scenarios = row.get("scenario_tags") or []
        row_seasons = row.get("season_tags") or []
        row_weather = row.get("weather_tags") or []
        style_primary = row.get("style_primary")

        scenario_overlap = CompletionDataRepository._intersection_size(row_scenarios, scenario_tags)
        season_overlap = CompletionDataRepository._intersection_size(row_seasons, season_tags)
        weather_overlap = CompletionDataRepository._intersection_size(row_weather, weather_tags)
        role_priority = 1 if role in missing_roles else 0
        sport_context = set(scenario_tags) & {"gym", "running", "outdoor_light"}
        sport_alignment = 1 if sport_context and role in {"active_top", "active_bottom", "running_shoes"} else 0
        activewear_penalty = -1 if scenario_tags and not sport_context and style_primary == "activewear" else 0

        return (
            role_priority,
            sport_alignment,
            scenario_overlap,
            season_overlap,
            weather_overlap,
            activewear_penalty,
            float(row.get("source_preference_score") or 0),
            float(row.get("metadata_completeness_score") or 0),
            float(row.get("image_quality_score") or 0),
            float(row.get("metadata_quality_score") or 0),
        )

    @staticmethod
    def _dedupe_completion_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[tuple[str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for row in candidates:
            dedupe_key = (str(row.get("base_url") or ""), str(row.get("source_product_id") or row.get("id")))
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            deduped.append(row)
        return deduped

    @staticmethod
    def _intersection_size(left: Sequence[str] | None, right: Sequence[str] | None) -> int:
        if not left or not right:
            return 0
        return len(set(left) & set(right))
