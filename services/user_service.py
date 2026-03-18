from database.db import create_user, list_users


def create_new_user(name):
    if not name or not name.strip():
        raise ValueError("User name cannot be empty")

    return create_user(name.strip())


def get_all_users():
    return list_users()