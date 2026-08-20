from dataclasses import dataclass

from rest_framework.exceptions import PermissionDenied


@dataclass(frozen=True)
class JethroContext:
    user: object
    active_assembly: object
    region: object | None
    role: tuple[str, ...]
    permissions: tuple[str, ...]


def resolve_jethro_context(user):
    assembly = getattr(user, "church", None)
    if assembly is None:
        raise PermissionDenied("Select an active assembly before using Jethro.")

    zone = getattr(assembly, "zone", None)
    region = getattr(zone, "region", None)
    roles = tuple(user.roles.values_list("name", flat=True))
    permissions = tuple(user.get_all_permissions())
    return JethroContext(user, assembly, region, roles, permissions)
