from copy import deepcopy


BASE_VARIANT = {
    "mode": "list",
    "border": "y",
    "theme": "neutral",
    "interaction": {
        "editable": False,
        "selectable": True,
        "density": "comfortable",
    },
}


REGIONAL_CHURCHES_TABLE_SCHEMA = {
    "intent": "minimal",
    "columns": [
        {"id": "name", "label": "Assembly Name"},
        {"id": "code", "label": "Code"},
        {"id": "zone_name", "label": "Zone"},
        {"id": "country", "label": "Country"},
        {"id": "city", "label": "City"},
        {"id": "pastor_names", "label": "Pastor"},
        {"id": "status", "label": "Status"},
    ],
    "variant": deepcopy(BASE_VARIANT),
}


REGIONAL_USERS_TABLE_SCHEMA = {
    "intent": "minimal",
    "columns": [
        {"id": "full_name", "label": "Name"},
        {"id": "email", "label": "Email"},
        {"id": "role_names", "label": "Role"},
        {"id": "church_name", "label": "Assembly"},
        {"id": "zone_name", "label": "Zone"},
        {"id": "church_country", "label": "Country"},
        {"id": "status", "label": "Status"},
    ],
    "variant": deepcopy(BASE_VARIANT),
}


def get_regional_churches_table_schema(user=None):
    return deepcopy(REGIONAL_CHURCHES_TABLE_SCHEMA)


def get_regional_users_table_schema(user=None):
    return deepcopy(REGIONAL_USERS_TABLE_SCHEMA)


def get_regional_directory_table_schemas(user=None):
    return {
        "churches": get_regional_churches_table_schema(user),
        "users": get_regional_users_table_schema(user),
    }
