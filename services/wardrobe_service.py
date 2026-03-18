from database.db import (
    add_item_to_wardrobe,
    remove_item_from_wardrobe,
    get_user_wardrobe,
    create_wardrobe_snapshot,
)


def add_catalog_item_to_user_wardrobe(user_id, catalog_id):
    if not user_id:
        raise ValueError("user_id is required")

    if not catalog_id:
        raise ValueError("catalog_id is required")

    row_id = add_item_to_wardrobe(user_id, catalog_id)
    create_wardrobe_snapshot(user_id, comment="Item added to wardrobe")
    return row_id


def remove_catalog_item_from_user_wardrobe(user_id, catalog_id):
    if not user_id:
        raise ValueError("user_id is required")

    if not catalog_id:
        raise ValueError("catalog_id is required")

    remove_item_from_wardrobe(user_id, catalog_id)
    create_wardrobe_snapshot(user_id, comment="Item removed from wardrobe")


def get_active_wardrobe_for_user(user_id):
    if not user_id:
        raise ValueError("user_id is required")

    return get_user_wardrobe(user_id)