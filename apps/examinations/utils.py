import re

from django.conf import settings
from django.apps import apps


def get_student_model():
    model_label = getattr(
        settings,
        "EXAMINATIONS_STUDENT_MODEL",
        settings.AUTH_USER_MODEL,
    )
    return apps.get_model(model_label, require_ready=True)


def get_student_number_field():
    return getattr(
        settings,
        "EXAMINATIONS_STUDENT_NUMBER_FIELD",
        "student_number",
    )


def get_student_user_field():
    return getattr(
        settings,
        "EXAMINATIONS_STUDENT_USER_FIELD",
        "user",
    )


def normalize_student_number(value: str | None) -> str:
    if not value:
        return ""

    return re.sub(r"[^A-Za-z0-9]", "", str(value)).upper()


def is_valid_student_number(value: str | None) -> bool:
    normalized = normalize_student_number(value)
    return bool(re.fullmatch(r"[A-Z]{1,4}\d{5,}", normalized))


def get_student_number(student):
    field_name = get_student_number_field()
    return normalize_student_number(getattr(student, field_name, ""))


def get_student_name(student):
    if student is None:
        return ""

    get_full_name = getattr(student, "get_full_name", None)
    if callable(get_full_name):
        name = get_full_name().strip()
        if name:
            return name

    user = getattr(student, "user", None)
    if user is not None:
        get_full_name = getattr(user, "get_full_name", None)
        if callable(get_full_name):
            name = get_full_name().strip()
            if name:
                return name

        first_name = getattr(user, "first_name", "")
        last_name = getattr(user, "last_name", "")
        name = f"{first_name} {last_name}".strip()
        if name:
            return name

    first_name = getattr(student, "first_name", "")
    last_name = getattr(student, "last_name", "")
    name = f"{first_name} {last_name}".strip()
    if name:
        return name

    return str(student)


def resolve_student_for_user(user):
    Student = get_student_model()
    user_model_label = user._meta.label

    if Student._meta.label == user_model_label:
        return user

    user_field = get_student_user_field()
    if not user_field:
        return None
    return Student.objects.filter(**{user_field: user}).first()
