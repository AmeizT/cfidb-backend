from urllib.parse import urljoin

import requests
from django.conf import settings
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.examinations.models import CBAStudentReference
from apps.examinations.utils import normalize_student_number


def _request_headers():
    headers = {"Accept": "application/json"}

    token = getattr(settings, "CBA_API_TOKEN", "").strip()
    if token:
        scheme = getattr(settings, "CBA_API_AUTH_SCHEME", "Bearer").strip()
        headers["Authorization"] = f"{scheme} {token}".strip()

    return headers


def _extract_page(payload):
    if isinstance(payload, list):
        return payload, None

    if not isinstance(payload, dict):
        raise ValueError("The CBA users endpoint returned an unsupported response.")

    for key in ("results", "data", "users"):
        value = payload.get(key)
        if isinstance(value, list):
            return value, payload.get("next")

    raise ValueError("No users list was found in the CBA API response.")


def fetch_all_cba_users():
    url = getattr(settings, "CBA_API_USERS_URL", "").strip()
    if not url:
        raise ValueError("CBA_API_USERS_URL is not configured.")

    timeout = getattr(settings, "CBA_API_TIMEOUT", 30)
    verify_ssl = getattr(settings, "CBA_API_VERIFY_SSL", True)
    headers = _request_headers()

    users = []
    next_url = url

    with requests.Session() as session:
        while next_url:
            response = session.get(
                next_url,
                headers=headers,
                timeout=timeout,
                verify=verify_ssl,
            )
            response.raise_for_status()

            page_users, next_page = _extract_page(response.json())
            users.extend(page_users)

            next_url = (
                urljoin(next_url, next_page)
                if next_page
                else None
            )

    return users


@transaction.atomic
def sync_cba_students():
    users = fetch_all_cba_users()

    CBAStudentReference.objects.update(is_active=False)

    created = 0
    updated = 0
    skipped = 0

    for payload in users:
        if str(payload.get("role", "")).lower() != "student":
            skipped += 1
            continue

        source_id = payload.get("id")
        student_number = normalize_student_number(payload.get("user_id"))

        if not source_id or not student_number:
            skipped += 1
            continue

        student = CBAStudentReference.objects.filter(
            source_id=source_id,
        ).first()

        if student is None:
            student = CBAStudentReference.objects.filter(
                student_number=student_number,
            ).first()

        was_created = student is None
        if student is None:
            student = CBAStudentReference(source_id=source_id)

        student.source_id = source_id
        student.student_number = student_number
        student.source_username = payload.get("username") or None
        student.first_name = payload.get("first_name") or ""
        student.last_name = payload.get("last_name") or ""
        student.email = payload.get("email") or ""
        student.role = payload.get("role") or "student"
        student.avatar = payload.get("avatar") or ""
        student.avatar_fallback = payload.get("avatar_fallback") or ""
        student.is_admin = bool(payload.get("is_admin", False))
        student.is_active = True
        student.source_created_at = parse_datetime(
            payload.get("created_at") or ""
        )
        student.source_updated_at = parse_datetime(
            payload.get("updated_at") or ""
        )
        student.raw_payload = payload
        student.full_clean()
        student.save()

        if was_created:
            created += 1
        else:
            updated += 1

    return {
        "received": len(users),
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "active_students": CBAStudentReference.objects.filter(
            is_active=True,
        ).count(),
    }
