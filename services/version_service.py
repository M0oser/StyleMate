from database.db import list_wardrobe_versions


def get_user_versions(user_id):
    if not user_id:
        raise ValueError("user_id is required")

    return list_wardrobe_versions(user_id)