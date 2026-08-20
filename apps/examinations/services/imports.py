import re
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader

from apps.examinations.models import (
    ExaminationImport,
    ExaminationImportRow,
    ExaminationResult,
    ResultStatus,
)
from apps.examinations.utils import (
    get_student_model,
    get_student_number_field,
    is_valid_student_number,
    normalize_student_number,
)


PARSER_VERSION = "1.1.0"

ABSENT_PATTERNS = (
    "absent from examination",
    "absent",
    "did not write",
    "did not sit",
    "no show",
    "dnw",
)

WITHHELD_PATTERNS = (
    "withheld",
    "result withheld",
)

CANCELLED_PATTERNS = (
    "cancelled",
    "canceled",
    "void",
)


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    raw_student_number: str
    normalized_student_number: str
    raw_result: str
    score: Decimal | None
    result_status: str | None
    validation_message: str = ""


def _student_number_regex():
    pattern = getattr(
        settings,
        "EXAMINATIONS_STUDENT_NUMBER_REGEX",
        r"\b[A-Za-z]{1,4}(?:[\s-]*\d){5,}\b",
    )
    return re.compile(pattern, flags=re.IGNORECASE)


def extract_pdf_text(file_obj):
    file_obj.seek(0)
    reader = PdfReader(file_obj)

    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)

    return "\n".join(pages)


def _detect_non_scored_status(value):
    normalized = re.sub(r"\s+", " ", value).strip().lower()

    if any(pattern in normalized for pattern in ABSENT_PATTERNS):
        return ResultStatus.ABSENT

    if any(pattern in normalized for pattern in WITHHELD_PATTERNS):
        return ResultStatus.WITHHELD

    if any(pattern in normalized for pattern in CANCELLED_PATTERNS):
        return ResultStatus.CANCELLED

    return None


def _parse_result(raw_value, total_marks):
    value = re.sub(r"\s+", " ", raw_value).strip()

    non_scored_status = _detect_non_scored_status(value)
    if non_scored_status:
        return None, non_scored_status, ""

    number_match = re.search(r"(?<![\w.])-?\d+(?:\.\d+)?", value)
    if not number_match:
        return None, None, "No valid score or result status was found."

    try:
        score = Decimal(number_match.group(0))
    except InvalidOperation:
        return None, None, "The extracted score is invalid."

    if score < 0:
        return None, None, "Score cannot be negative."

    if score > total_marks:
        return (
            None,
            None,
            f"Score cannot exceed total marks ({total_marks}).",
        )

    return score, ResultStatus.SCORED, ""


def parse_examination_text(text, total_marks):
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    student_regex = _student_number_regex()
    parsed_rows = []
    row_number = 0

    for index, line in enumerate(lines):
        matches = list(student_regex.finditer(line))
        if not matches:
            continue

        for match_index, match in enumerate(matches):
            row_number += 1
            raw_student_number = match.group(0)

            if match_index + 1 < len(matches):
                tail = line[match.end():matches[match_index + 1].start()]
            else:
                tail = line[match.end():]

            candidate = tail.strip(" :-|\t")

            if not candidate:
                lookahead_parts = []
                for next_line in lines[index + 1:index + 3]:
                    if student_regex.search(next_line):
                        break
                    lookahead_parts.append(next_line)
                candidate = " ".join(lookahead_parts).strip()

            score, result_status, validation_message = _parse_result(
                candidate,
                total_marks,
            )

            # The permissive regex can consume a whitespace-separated score
            # (for example, ``S2427015 60``). Peel off that final group only
            # when the text after the full match did not produce a result.
            # Otherwise internal whitespace remains in the raw audit value.
            if validation_message:
                trailing_group = re.fullmatch(
                    r"(.+?)[\s-]+(\d+)",
                    raw_student_number,
                )
                if trailing_group:
                    possible_raw = trailing_group.group(1)
                    possible_candidate = " ".join(
                        part
                        for part in (
                            trailing_group.group(2),
                            candidate,
                        )
                        if part
                    )
                    possible_result = _parse_result(
                        possible_candidate,
                        total_marks,
                    )
                    if (
                        is_valid_student_number(possible_raw)
                        and not possible_result[2]
                    ):
                        raw_student_number = possible_raw
                        candidate = possible_candidate
                        score, result_status, validation_message = (
                            possible_result
                        )

            normalized_student_number = normalize_student_number(
                raw_student_number
            )

            parsed_rows.append(
                ParsedRow(
                    row_number=row_number,
                    raw_student_number=raw_student_number,
                    normalized_student_number=normalized_student_number,
                    raw_result=candidate,
                    score=score,
                    result_status=result_status,
                    validation_message=validation_message,
                )
            )

    return parsed_rows


def _student_lookup(student_numbers):
    Student = get_student_model()
    student_number_field = get_student_number_field()
    normalized_numbers = {
        normalize_student_number(value)
        for value in student_numbers
        if normalize_student_number(value)
    }
    students_by_number = {}

    for student in Student.objects.all():
        normalized = normalize_student_number(
            getattr(student, student_number_field, "")
        )
        if normalized in normalized_numbers:
            students_by_number[normalized] = student

    return students_by_number


def find_student_by_number(student_number):
    normalized = normalize_student_number(student_number)
    if not is_valid_student_number(normalized):
        return None
    return _student_lookup({normalized}).get(normalized)


def refresh_import_stats(import_batch):
    counts = Counter(
        import_batch.rows.values_list("match_status", flat=True)
    )

    import_batch.total_rows = import_batch.rows.count()
    import_batch.matched_rows = counts[
        ExaminationImportRow.MatchStatus.MATCHED
    ]
    import_batch.unmatched_rows = counts[
        ExaminationImportRow.MatchStatus.UNMATCHED
    ]
    import_batch.invalid_rows = counts[
        ExaminationImportRow.MatchStatus.INVALID
    ]
    import_batch.duplicate_rows = counts[
        ExaminationImportRow.MatchStatus.DUPLICATE
    ]
    import_batch.excluded_rows = counts[
        ExaminationImportRow.MatchStatus.EXCLUDED
    ]

    import_batch.save(
        update_fields=[
            "total_rows",
            "matched_rows",
            "unmatched_rows",
            "invalid_rows",
            "duplicate_rows",
            "excluded_rows",
        ]
    )

    return import_batch


@transaction.atomic
def process_examination_import(import_id):
    import_batch = (
        ExaminationImport.objects
        .select_for_update()
        .select_related("examination")
        .get(pk=import_id)
    )

    import_batch.status = ExaminationImport.Status.PROCESSING
    import_batch.error_message = ""
    import_batch.parser_version = PARSER_VERSION
    import_batch.save(
        update_fields=[
            "status",
            "error_message",
            "parser_version",
        ]
    )

    try:
        text = extract_pdf_text(import_batch.pdf_file)
        parsed_rows = parse_examination_text(
            text=text,
            total_marks=import_batch.examination.total_marks,
        )

        import_batch.rows.all().delete()

        normalized_counts = Counter(
            row.normalized_student_number
            for row in parsed_rows
            if row.normalized_student_number
        )

        unique_numbers = {
            row.normalized_student_number
            for row in parsed_rows
            if (
                row.normalized_student_number
                and normalized_counts[row.normalized_student_number] == 1
                and is_valid_student_number(row.normalized_student_number)
                and not row.validation_message
            )
        }

        students_by_number = _student_lookup(unique_numbers)

        rows_to_create = []

        for parsed in parsed_rows:
            matched_student = None
            validation_message = parsed.validation_message

            if not parsed.normalized_student_number:
                match_status = (
                    ExaminationImportRow.MatchStatus.INVALID
                )
                validation_message = (
                    validation_message or "Student number is missing."
                )
            elif not is_valid_student_number(
                parsed.normalized_student_number
            ):
                match_status = (
                    ExaminationImportRow.MatchStatus.INVALID
                )
                validation_message = "Student number is invalid."
            elif normalized_counts[parsed.normalized_student_number] > 1:
                match_status = (
                    ExaminationImportRow.MatchStatus.DUPLICATE
                )
                validation_message = (
                    "This student number appears more than once "
                    "in the uploaded PDF."
                )
            elif validation_message:
                match_status = (
                    ExaminationImportRow.MatchStatus.INVALID
                )
            else:
                matched_student = students_by_number.get(
                    parsed.normalized_student_number
                )

                if matched_student is None:
                    match_status = (
                        ExaminationImportRow.MatchStatus.UNMATCHED
                    )
                    validation_message = (
                        "No student matched this student number."
                    )
                else:
                    match_status = (
                        ExaminationImportRow.MatchStatus.MATCHED
                    )

            rows_to_create.append(
                ExaminationImportRow(
                    import_batch=import_batch,
                    row_number=parsed.row_number,
                    raw_student_number=parsed.raw_student_number,
                    normalized_student_number=(
                        parsed.normalized_student_number
                    ),
                    raw_result=parsed.raw_result,
                    score=parsed.score,
                    result_status=parsed.result_status,
                    matched_student=matched_student,
                    match_status=match_status,
                    validation_message=validation_message,
                )
            )

        ExaminationImportRow.objects.bulk_create(rows_to_create)

        refresh_import_stats(import_batch)

        import_batch.status = (
            ExaminationImport.Status.REVIEW_REQUIRED
        )
        import_batch.processed_at = timezone.now()

        if not parsed_rows:
            import_batch.status = ExaminationImport.Status.FAILED
            import_batch.error_message = (
                "No examination result rows were detected in the PDF."
            )

        import_batch.save(
            update_fields=[
                "status",
                "processed_at",
                "error_message",
            ]
        )

        return import_batch

    except Exception as exc:
        import_batch.status = ExaminationImport.Status.FAILED
        import_batch.error_message = str(exc)
        import_batch.processed_at = timezone.now()
        import_batch.save(
            update_fields=[
                "status",
                "error_message",
                "processed_at",
            ]
        )
        raise


@transaction.atomic
def confirm_examination_import(import_id, allow_partial=False):
    import_batch = (
        ExaminationImport.objects
        .select_for_update()
        .select_related("examination")
        .get(pk=import_id)
    )

    rows = list(
        import_batch.rows
        .select_for_update()
        .select_related("matched_student")
        .all()
    )

    unresolved_rows = [
        row
        for row in rows
        if row.match_status not in {
            ExaminationImportRow.MatchStatus.MATCHED,
            ExaminationImportRow.MatchStatus.EXCLUDED,
        }
    ]

    if unresolved_rows and not allow_partial:
        raise ValidationError(
            "Resolve or exclude all unmatched, duplicate, and invalid "
            "rows before confirming this import."
        )

    matched_rows = [
        row
        for row in rows
        if row.match_status == ExaminationImportRow.MatchStatus.MATCHED
    ]

    if not matched_rows:
        raise ValidationError(
            "There are no matched rows available to confirm."
        )

    created_count = 0
    updated_count = 0

    for row in matched_rows:
        row.full_clean()

        result, created = ExaminationResult.objects.update_or_create(
            examination=import_batch.examination,
            student=row.matched_student,
            defaults={
                "student_number_snapshot": (
                    row.normalized_student_number
                ),
                "score": row.score,
                "status": row.result_status,
                "raw_imported_value": row.raw_result,
                "source_import": import_batch,
            },
        )

        result.full_clean()
        result.save()

        if created:
            created_count += 1
        else:
            updated_count += 1

    import_batch.status = ExaminationImport.Status.COMPLETED
    import_batch.processed_at = timezone.now()
    import_batch.error_message = ""
    import_batch.save(
        update_fields=[
            "status",
            "processed_at",
            "error_message",
        ]
    )

    refresh_import_stats(import_batch)

    return {
        "import_batch": import_batch,
        "created_count": created_count,
        "updated_count": updated_count,
    }
