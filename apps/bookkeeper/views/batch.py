import json
import re

from rest_framework import status
from rest_framework.response import Response

from apps.bookkeeper.serializers import BatchEnvelopeSerializer
from apps.bookkeeper.services import BatchEntryValidationError


def parse_batch_payload(request, file_fields=()):
    raw_entries = request.data.get("entries")
    if isinstance(raw_entries, str):
        try:
            entries = json.loads(raw_entries)
        except json.JSONDecodeError:
            entries = None
    else:
        entries = raw_entries
    if not isinstance(entries, list) or not entries:
        return None, Response(
            {"message": "Some entries are invalid.", "errors": {"entries": {"0": {"non_field_errors": ["Add at least one entry."]}}}},
            status=status.HTTP_400_BAD_REQUEST,
        )
    for key, uploaded in request.FILES.items():
        match = re.fullmatch(r"entries(?:\.|\[)(\d+)(?:\]\[|\.)([^\]]+)\]?", key)
        if not match:
            continue
        index, field = int(match.group(1)), match.group(2)
        if index < len(entries) and field in file_fields:
            entries[index][field] = uploaded
    envelope = BatchEnvelopeSerializer(data={"period": request.data.get("period"), "report": request.data.get("report")})
    if not envelope.is_valid():
        return None, Response({"message": "Some entries are invalid.", "errors": envelope.errors}, status=status.HTTP_400_BAD_REQUEST)
    return {**envelope.validated_data, "entries": entries}, None


def validate_batch_entries(serializer_class, entries, request):
    serializer = serializer_class(data=entries, many=True, context={"request": request})
    if serializer.is_valid():
        return serializer.validated_data, None
    errors = {
        str(index): error
        for index, error in enumerate(serializer.errors)
        if error
    }
    return None, Response(
        {"message": "Some entries are invalid.", "errors": {"entries": errors}},
        status=status.HTTP_400_BAD_REQUEST,
    )


def batch_error_response(exc):
    return Response(
        {"message": exc.message, "errors": exc.errors},
        status=status.HTTP_400_BAD_REQUEST,
    )


def active_assembly_or_error(request):
    assembly = getattr(request.user, "church", None)
    if assembly is not None:
        return assembly, None
    return None, Response(
        {"message": "An active assembly is required to create entries."},
        status=status.HTTP_403_FORBIDDEN,
    )
