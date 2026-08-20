from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.examinations.models import (
    CBAStudentReference,
    Examination,
    ExaminationImport,
    ExaminationImportRow,
    ExaminationResult,
    ResultStatus,
)
from apps.examinations.utils import (
    get_student_name,
    get_student_number,
    is_valid_student_number,
    normalize_student_number,
)
from apps.examinations.services.imports import find_student_by_number




class CBAStudentReferenceSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = CBAStudentReference
        fields = [
            "id",
            "source_id",
            "student_number",
            "source_username",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "role",
            "avatar",
            "avatar_fallback",
            "is_admin",
            "is_active",
            "source_created_at",
            "source_updated_at",
            "synced_at",
            "created_at",
        ]
        read_only_fields = fields


class ExaminationSerializer(serializers.ModelSerializer):
    result_count = serializers.IntegerField(read_only=True)
    import_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Examination
        fields = [
            "id",
            "name",
            "academic_year",
            "examination_date",
            "total_marks",
            "pass_mark",
            "status",
            "published_at",
            "result_count",
            "import_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "status",
            "published_at",
            "result_count",
            "import_count",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        instance = self.instance

        examination = Examination(
            name=attrs.get(
                "name",
                getattr(instance, "name", ""),
            ),
            academic_year=attrs.get(
                "academic_year",
                getattr(instance, "academic_year", None),
            ),
            examination_date=attrs.get(
                "examination_date",
                getattr(instance, "examination_date", None),
            ),
            total_marks=attrs.get(
                "total_marks",
                getattr(instance, "total_marks", None),
            ),
            pass_mark=attrs.get(
                "pass_mark",
                getattr(instance, "pass_mark", None),
            ),
        )

        try:
            examination.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict)

        return attrs

    def validate_academic_year(self, value):
        if value not in {2024, 2025, 2026}:
            raise serializers.ValidationError(
                "Academic year must be 2024, 2025, or 2026."
            )
        return value


class ExaminationImportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExaminationImport
        fields = ["pdf_file"]

    def validate_pdf_file(self, value):
        max_size = getattr(
            settings,
            "EXAMINATIONS_MAX_PDF_SIZE",
            10 * 1024 * 1024,
        )

        if value.size > max_size:
            raise serializers.ValidationError(
                f"PDF must be smaller than {max_size // (1024 * 1024)} MB."
            )

        content_type = getattr(value, "content_type", "")
        if content_type and content_type != "application/pdf":
            raise serializers.ValidationError(
                "Only PDF files are allowed."
            )

        return value


class ExaminationImportSerializer(serializers.ModelSerializer):
    examination_name = serializers.CharField(
        source="examination.name",
        read_only=True,
    )

    class Meta:
        model = ExaminationImport
        fields = [
            "id",
            "examination",
            "examination_name",
            "pdf_file",
            "original_filename",
            "status",
            "total_rows",
            "matched_rows",
            "unmatched_rows",
            "invalid_rows",
            "duplicate_rows",
            "excluded_rows",
            "parser_version",
            "error_message",
            "uploaded_by",
            "created_at",
            "processed_at",
        ]
        read_only_fields = fields


class ExaminationImportRowSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    student_number = serializers.SerializerMethodField()

    class Meta:
        model = ExaminationImportRow
        fields = [
            "id",
            "import_batch",
            "row_number",
            "raw_student_number",
            "normalized_student_number",
            "raw_result",
            "score",
            "result_status",
            "matched_student",
            "student_name",
            "student_number",
            "match_status",
            "validation_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "import_batch",
            "row_number",
            "student_name",
            "student_number",
            "created_at",
            "updated_at",
        ]

    def get_student_name(self, obj):
        return get_student_name(obj.matched_student)

    def get_student_number(self, obj):
        if obj.matched_student is None:
            return ""
        return get_student_number(obj.matched_student)

    def validate(self, attrs):
        instance = self.instance

        raw_student_number = attrs.get(
            "raw_student_number",
            instance.raw_student_number,
        )
        score = attrs.get("score", instance.score)
        result_status = attrs.get(
            "result_status",
            instance.result_status,
        )
        matched_student = attrs.get(
            "matched_student",
            instance.matched_student,
        )
        match_status = attrs.get(
            "match_status",
            instance.match_status,
        )
        raw_was_corrected = "raw_student_number" in attrs
        if raw_was_corrected and "matched_student" not in attrs:
            matched_student = None

        if matched_student is not None:
            match_status = ExaminationImportRow.MatchStatus.MATCHED
            attrs["match_status"] = match_status
            attrs["validation_message"] = ""
            attrs["normalized_student_number"] = (
                get_student_number(matched_student)
            )
        elif raw_was_corrected:
            normalized_student_number = normalize_student_number(
                raw_student_number
            )
            attrs["normalized_student_number"] = normalized_student_number

            if not is_valid_student_number(normalized_student_number):
                attrs["matched_student"] = None
                attrs["match_status"] = (
                    ExaminationImportRow.MatchStatus.INVALID
                )
                attrs["validation_message"] = "Student number is invalid."
            else:
                matched_student = find_student_by_number(
                    normalized_student_number
                )
                attrs["matched_student"] = matched_student
                attrs["match_status"] = (
                    ExaminationImportRow.MatchStatus.MATCHED
                    if matched_student is not None
                    else ExaminationImportRow.MatchStatus.UNMATCHED
                )
                attrs["validation_message"] = (
                    ""
                    if matched_student is not None
                    else "No student matched this student number."
                )
        elif match_status == ExaminationImportRow.MatchStatus.MATCHED:
            raise serializers.ValidationError(
                {
                    "matched_student": (
                        "A matched row must have a student."
                    )
                }
            )
        else:
            attrs["normalized_student_number"] = (
                normalize_student_number(raw_student_number)
            )

        normalized_student_number = attrs.get(
            "normalized_student_number",
            instance.normalized_student_number,
        )
        duplicate_exists = (
            normalized_student_number
            and instance.import_batch.rows.exclude(pk=instance.pk).filter(
                normalized_student_number=normalized_student_number
            ).exists()
        )
        if (
            duplicate_exists
            and attrs.get("match_status", match_status)
            != ExaminationImportRow.MatchStatus.EXCLUDED
        ):
            attrs["matched_student"] = None
            attrs["match_status"] = ExaminationImportRow.MatchStatus.DUPLICATE
            attrs["validation_message"] = (
                "This student number appears more than once in the uploaded PDF."
            )

        if result_status == ResultStatus.SCORED:
            if score is None:
                raise serializers.ValidationError(
                    {"score": "A scored result must have a score."}
                )

            if score < 0:
                raise serializers.ValidationError(
                    {"score": "Score cannot be negative."}
                )

            total_marks = instance.import_batch.examination.total_marks
            if score > total_marks:
                raise serializers.ValidationError(
                    {
                        "score": (
                            f"Score cannot exceed total marks "
                            f"({total_marks})."
                        )
                    }
                )

        elif result_status in {
            ResultStatus.ABSENT,
            ResultStatus.WITHHELD,
            ResultStatus.CANCELLED,
        }:
            attrs["score"] = None

        if match_status == ExaminationImportRow.MatchStatus.EXCLUDED:
            attrs["matched_student"] = None

        return attrs


class ExaminationResultSerializer(serializers.ModelSerializer):
    examination_name = serializers.CharField(
        source="examination.name",
        read_only=True,
    )
    academic_year = serializers.IntegerField(
        source="examination.academic_year",
        read_only=True,
    )
    examination_date = serializers.DateField(
        source="examination.examination_date",
        read_only=True,
    )
    total_marks = serializers.DecimalField(
        source="examination.total_marks",
        max_digits=7,
        decimal_places=2,
        read_only=True,
    )
    pass_mark = serializers.DecimalField(
        source="examination.pass_mark",
        max_digits=7,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )

    student_name = serializers.SerializerMethodField()
    student_number = serializers.SerializerMethodField()
    percentage = serializers.DecimalField(
        max_digits=7,
        decimal_places=2,
        read_only=True,
        allow_null=True,
    )
    passed = serializers.BooleanField(
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = ExaminationResult
        fields = [
            "id",
            "examination",
            "examination_name",
            "academic_year",
            "examination_date",
            "total_marks",
            "pass_mark",
            "student",
            "student_name",
            "student_number",
            "student_number_snapshot",
            "score",
            "status",
            "percentage",
            "passed",
            "raw_imported_value",
            "source_import",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_student_name(self, obj):
        return get_student_name(obj.student)

    def get_student_number(self, obj):
        return get_student_number(obj.student)


class ConfirmImportSerializer(serializers.Serializer):
    allow_partial = serializers.BooleanField(default=False)


class PublishExaminationSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError(
                "Set confirm to true to publish the examination."
            )
        return value
