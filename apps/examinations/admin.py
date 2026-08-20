from django.contrib import admin

from apps.examinations.models import (
    CBAStudentReference,
    Examination,
    ExaminationImport,
    ExaminationImportRow,
    ExaminationResult,
)

@admin.register(CBAStudentReference)
class CBAStudentReferenceAdmin(admin.ModelAdmin):
    list_display = [
        "student_number",
        "first_name",
        "last_name",
        "email",
        "is_active",
        "synced_at",
    ]
    list_filter = ["is_active", "role", "is_admin"]
    search_fields = [
        "student_number",
        "first_name",
        "last_name",
        "email",
    ]
    readonly_fields = [
        "source_id",
        "source_username",
        "source_created_at",
        "source_updated_at",
        "raw_payload",
        "synced_at",
        "created_at",
    ]


class ExaminationImportInline(admin.TabularInline):
    model = ExaminationImport
    extra = 0
    fields = [
        "original_filename",
        "status",
        "total_rows",
        "matched_rows",
        "unmatched_rows",
        "invalid_rows",
        "created_at",
    ]
    readonly_fields = fields
    show_change_link = True


class ExaminationResultInline(admin.TabularInline):
    model = ExaminationResult
    extra = 0
    fields = [
        "student",
        "student_number_snapshot",
        "score",
        "status",
    ]
    readonly_fields = fields
    show_change_link = True


@admin.register(Examination)
class ExaminationAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "academic_year",
        "examination_date",
        "total_marks",
        "pass_mark",
        "status",
        "published_at",
        "created_at",
    ]
    list_filter = ["status", "academic_year"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at", "published_at"]
    inlines = [ExaminationImportInline, ExaminationResultInline]


class ExaminationImportRowInline(admin.TabularInline):
    model = ExaminationImportRow
    extra = 0
    fields = [
        "row_number",
        "raw_student_number",
        "normalized_student_number",
        "raw_result",
        "score",
        "result_status",
        "matched_student",
        "match_status",
        "validation_message",
    ]
    readonly_fields = ["row_number"]
    show_change_link = True


@admin.register(ExaminationImport)
class ExaminationImportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "examination",
        "original_filename",
        "status",
        "total_rows",
        "matched_rows",
        "unmatched_rows",
        "invalid_rows",
        "duplicate_rows",
        "created_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = [
        "original_filename",
        "examination__name",
    ]
    readonly_fields = [
        "total_rows",
        "matched_rows",
        "unmatched_rows",
        "invalid_rows",
        "duplicate_rows",
        "excluded_rows",
        "parser_version",
        "error_message",
        "created_at",
        "processed_at",
    ]
    inlines = [ExaminationImportRowInline]


@admin.register(ExaminationImportRow)
class ExaminationImportRowAdmin(admin.ModelAdmin):
    list_display = [
        "row_number",
        "import_batch",
        "normalized_student_number",
        "raw_result",
        "score",
        "result_status",
        "matched_student",
        "match_status",
    ]
    list_filter = ["match_status", "result_status"]
    search_fields = [
        "raw_student_number",
        "normalized_student_number",
        "raw_result",
    ]
    autocomplete_fields = ["matched_student"]


@admin.register(ExaminationResult)
class ExaminationResultAdmin(admin.ModelAdmin):
    list_display = [
        "student_number_snapshot",
        "student",
        "examination",
        "score",
        "status",
        "created_at",
    ]
    list_filter = [
        "status",
        "examination__academic_year",
        "examination",
    ]
    search_fields = [
        "student_number_snapshot",
        "examination__name",
    ]
    autocomplete_fields = ["student", "source_import"]
