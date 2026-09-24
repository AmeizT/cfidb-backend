"""Scope selection only; all metric calculations stay in composition.py."""
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.churches.services.regional_scope import active_zone, uses_regional_shell, permitted_zones


def regional_scope(assemblies, params, user):
    directory = list(assemblies.order_by("zone__name", "zone_id", "country", "id").values(
        "id", "zone_id", "zone__name", "country", "country_code"))
    # Match legacy country names to codes already present in this permitted scope.
    codes = {r["country"].strip().casefold(): r["country_code"].strip().upper()
             for r in directory if r["country"].strip() and r["country_code"].strip()}
    zones = {}
    countries_by_assembly = {}
    for row in directory:
        country_name = row["country"].strip()
        key = row["country_code"].strip().upper() or codes.get(country_name.casefold()) or country_name.casefold() or "unknown"
        countries_by_assembly[row["id"]] = key
        zone = zones.setdefault(row["zone_id"], {"id": row["zone_id"], "name": row["zone__name"], "countries": {}})
        zone["countries"].setdefault(key, {"id": key, "name": country_name or row["country_code"] or "Country not recorded"})
    options = [{**zone, "countries": sorted(zone["countries"].values(), key=lambda c: (c["name"].casefold(), c["id"]))}
               for zone in zones.values()]
    saved_zone = active_zone(user) if uses_regional_shell(user) else None
    raw_zone = params.get("zone") or (str(saved_zone.pk) if saved_zone else None)
    if raw_zone:
        try:
            zone_id = int(raw_zone)
        except (ValueError, TypeError):
            raise ValidationError({"zone": "Use a zone ID."})
        selected = next((z for z in options if z["id"] == zone_id), None)
        if selected is None:
            empty_zone = permitted_zones(user).filter(pk=zone_id).first()
            if empty_zone:
                return assemblies.none(), {"zones": options, "zone": zone_id, "country": None, "countries": []}
            raise PermissionDenied("You do not have access to this zone.")
    else:
        assigned = set() if user.is_superuser else set(user.assigned_zones.values_list("id", flat=True))
        selected = next((z for z in options if z["id"] in assigned), options[0] if options else None)
    if not selected:
        return assemblies.none(), {"zones": options, "zone": None, "country": None, "countries": []}
    country = params.get("country") or selected["countries"][0]["id"]
    if country != "all" and country not in {c["id"] for c in selected["countries"]}:
        raise PermissionDenied("This country is not available in the selected zone.")
    ids = [r["id"] for r in directory if r["zone_id"] == selected["id"]
           and (country == "all" or countries_by_assembly[r["id"]] == country)]
    return assemblies.filter(pk__in=ids), {
        "zones": options, "zone": selected["id"], "country": country, "countries": selected["countries"],
    }
