from copy import deepcopy


def _column(key, label, data_type="text", **overrides):
    column = {
        "id": key,
        "key": key,
        "label": label,
        "data_type": data_type,
        "sortable": True,
        "filterable": False,
        "searchable": data_type == "text",
        "visible": True,
        "exportable": True,
        "formatter": data_type,
    }
    column.update(overrides)
    return column


def _schema(columns, intent="minimal"):
    return {
        "intent": intent,
        "columns": columns,
        "variant": {
            "mode": "list",
            "border": "y",
            "theme": "neutral",
            "interaction": {"editable": False, "selectable": False, "density": "comfortable"},
        },
    }


MEMBERS_TABLE_SCHEMA = _schema([
    _column("full_name", "Member"),
    _column("gender", "Gender", filterable=True),
    _column("age", "Age", "number", searchable=False),
    _column("phone_number", "Phone"),
    _column("email", "Email"),
    _column("membership_status", "Status", filterable=True),
    _column("created_at", "Created", "date", searchable=False),
])

CHILDREN_TABLE_SCHEMA = _schema([
    _column("full_name", "Child"),
    _column("gender", "Gender", filterable=True),
    _column("age", "Age", "number", searchable=False),
    _column("guardian_name", "Guardian"),
    _column("guardian_relationship", "Relationship", filterable=True),
    _column("membership_status", "Status", filterable=True),
    _column("membersince", "Member Since", "date", searchable=False),
])

FORMER_MEMBERS_TABLE_SCHEMA = _schema([
    _column("member_full_name", "Member"),
    _column("former_assembly_name", "Former Assembly", filterable=True),
    _column("ended_on", "Ended", "date", searchable=False),
    _column("end_reason", "Reason", filterable=True),
    _column("current_assembly_name", "Current Assembly", filterable=True),
])

HOUSEHOLDS_TABLE_SCHEMA = _schema([
    _column("name", "Household"),
    _column("head_of_household", "Head of Household"),
    _column("active_member_count", "Members", "number", searchable=False),
    _column("location", "Location"),
    _column("contact", "Contact"),
    _column("status", "Status", filterable=True),
    _column("created_at", "Created", "date", searchable=False),
])

TRANSFERS_TABLE_SCHEMA = _schema([
    _column("member_full_name", "Member"),
    _column("from_assembly_name", "From Assembly", filterable=True),
    _column("to_assembly_name", "To Assembly", filterable=True),
    _column("effective_date", "Effective Date", "date", searchable=False),
    _column("status", "Status", filterable=True),
    _column("requested_at", "Requested", "date", searchable=False),
])

BAPTISMS_TABLE_SCHEMA = _schema([
    _column("member_full_name", "Member"),
    _column("baptized_at", "Baptism Date", "date", searchable=False),
    _column("baptized_where", "Location"),
    _column("status", "Status", filterable=True),
])

BABY_DEDICATIONS_TABLE_SCHEMA = _schema([
    _column("child_full_name", "Child"),
    _column("guardian_name", "Guardian"),
    _column("dedication_date", "Dedication Date", "date", searchable=False),
    _column("location", "Location"),
    _column("status", "Status", filterable=True),
])


def get_people_table_schema(name):
    schemas = {
        "members": MEMBERS_TABLE_SCHEMA,
        "adults": MEMBERS_TABLE_SCHEMA,
        "children": CHILDREN_TABLE_SCHEMA,
        "former_members": FORMER_MEMBERS_TABLE_SCHEMA,
        "households": HOUSEHOLDS_TABLE_SCHEMA,
        "transfers": TRANSFERS_TABLE_SCHEMA,
        "baptisms": BAPTISMS_TABLE_SCHEMA,
        "baby_dedications": BABY_DEDICATIONS_TABLE_SCHEMA,
    }
    return deepcopy(schemas[name])


class PeopleTableSchemaMixin:
    table_schema_name = None

    def get_table_schema(self):
        return get_people_table_schema(self.table_schema_name)

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        response.data["table_schema"] = self.get_table_schema()
        return response

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        if isinstance(response.data, dict) and "table_schema" not in response.data:
            response.data["table_schema"] = self.get_table_schema()
        return response
