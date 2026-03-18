from database.db import get_outfit_history, get_outfit_items


def get_user_outfit_history(user_id, limit=20):
    if not user_id:
        raise ValueError("user_id is required")
    return get_outfit_history(user_id, limit=limit)


def get_outfit_details(outfit_id):
    if not outfit_id:
        raise ValueError("outfit_id is required")
    return get_outfit_items(outfit_id)