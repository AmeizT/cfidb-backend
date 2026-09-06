"""Assembly checks shared by the existing Create endpoints."""
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.people.permissions import can_access_assembly


def active_create_assembly(request):
    assembly = getattr(request.user, "church", None)
    if assembly is None or not can_access_assembly(request.user, assembly):
        raise PermissionDenied("You cannot create records for this assembly.")
    # An explicit scope also protects a form opened before a workspace switch.
    expected = request.headers.get("X-Assembly-ID")
    if expected is not None and str(assembly.pk) != str(expected):
        raise ValidationError({"assembly": "The active assembly changed. Reopen the form."})
    return assembly


def reject_other_assembly(request, assembly):
    for field in ("assembly", "church"):
        supplied = request.data.get(field)
        if supplied is not None and str(supplied) != str(assembly.pk):
            raise PermissionDenied("You cannot create records for this assembly.")


def validate_create_image(image):
    if image.size > 500 * 1024:
        raise ValidationError("Images must be 500 KB or smaller.")
    # DRF ImageField has decoded the content with Pillow before this validator.
    if getattr(getattr(image, "image", None), "format", None) not in {"JPEG", "PNG", "WEBP"}:
        raise ValidationError("Choose a JPEG, PNG, or WebP image.")
    return image
