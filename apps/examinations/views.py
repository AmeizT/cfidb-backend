from django.conf import settings
from django.db.models import Count, Prefetch, Q
from django.http import HttpResponse
from django.utils.text import slugify
from django.utils import timezone
from rest_framework import filters, mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.examinations.models import (
    CBAStudentReference,
    Examination,
    ExaminationImport,
    ExaminationImportRow,
    ExaminationResult,
)
from apps.examinations.permissions import CanManageExaminations
from apps.examinations.serializers import (
    CBAStudentReferenceSerializer,
    ConfirmImportSerializer,
    ExaminationImportCreateSerializer,
    ExaminationImportRowSerializer,
    ExaminationImportSerializer,
    ExaminationResultSerializer,
    ExaminationSerializer,
    PublishExaminationSerializer,
)
from apps.examinations.services.cba_students import sync_cba_students
from apps.examinations.services.imports import (
    confirm_examination_import,
    process_examination_import,
    refresh_import_stats,
)
from apps.examinations.services.results import (
    ACADEMIC_YEARS,
    build_transcript,
    summarize_results,
)
from apps.examinations.services.transcript_pdf import render_transcript_pdf
from apps.examinations.utils import resolve_student_for_user




class CBAStudentReferenceViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanManageExaminations]
    serializer_class = CBAStudentReferenceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "student_number",
        "first_name",
        "last_name",
        "email",
    ]
    ordering_fields = [
        "student_number",
        "first_name",
        "last_name",
        "synced_at",
    ]
    ordering = ["first_name", "last_name"]

    def get_queryset(self):
        queryset = CBAStudentReference.objects.all()

        is_active = self.request.query_params.get("is_active")
        if is_active in {"true", "1"}:
            queryset = queryset.filter(is_active=True)
        elif is_active in {"false", "0"}:
            queryset = queryset.filter(is_active=False)

        return queryset

    @action(detail=False, methods=["post"], url_path="sync")
    def sync(self, request):
        result = sync_cba_students()
        return Response(result, status=status.HTTP_200_OK)


class ExaminationViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageExaminations]
    serializer_class = ExaminationSerializer

    def get_queryset(self):
        queryset = (
            Examination.objects
            .select_related("created_by")
            .annotate(
                result_count=Count("results", distinct=True),
                import_count=Count("imports", distinct=True),
            )
        )

        status_value = self.request.query_params.get("status")
        academic_year = self.request.query_params.get("academic_year")
        search = self.request.query_params.get("search")

        if status_value:
            queryset = queryset.filter(status=status_value)

        if academic_year:
            queryset = queryset.filter(academic_year=academic_year)

        if search:
            queryset = queryset.filter(name__icontains=search)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(
        detail=True,
        methods=["get", "post"],
        url_path="imports",
    )
    def imports(self, request, pk=None):
        examination = self.get_object()

        if request.method == "GET":
            queryset = examination.imports.select_related(
                "uploaded_by",
                "examination",
            )
            serializer = ExaminationImportSerializer(
                queryset,
                many=True,
                context=self.get_serializer_context(),
            )
            return Response(serializer.data)

        serializer = ExaminationImportCreateSerializer(
            data=request.data,
            context=self.get_serializer_context(),
        )
        serializer.is_valid(raise_exception=True)

        pdf_file = serializer.validated_data["pdf_file"]

        import_batch = ExaminationImport.objects.create(
            examination=examination,
            pdf_file=pdf_file,
            original_filename=pdf_file.name,
            uploaded_by=request.user,
        )

        process_async = getattr(
            settings,
            "EXAMINATIONS_PROCESS_IMPORTS_ASYNC",
            False,
        )

        if process_async:
            try:
                from examinations.tasks import (
                    process_examination_import_task,
                )
                process_examination_import_task.delay(import_batch.pk)
            except (ImportError, ModuleNotFoundError):
                process_examination_import(import_batch.pk)
        else:
            process_examination_import(import_batch.pk)

        import_batch.refresh_from_db()

        return Response(
            ExaminationImportSerializer(
                import_batch,
                context=self.get_serializer_context(),
            ).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["get"],
        url_path="results",
    )
    def results(self, request, pk=None):
        examination = self.get_object()

        queryset = (
            examination.results
            .select_related("student", "examination", "source_import")
            .all()
        )

        result_status = request.query_params.get("status")
        if result_status:
            queryset = queryset.filter(status=result_status)

        serializer = ExaminationResultSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="publish",
    )
    def publish(self, request, pk=None):
        examination = self.get_object()

        serializer = PublishExaminationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not examination.results.exists():
            raise ValidationError(
                "This examination has no confirmed results."
            )

        examination.status = Examination.Status.PUBLISHED
        examination.published_at = timezone.now()
        examination.save(
            update_fields=["status", "published_at", "updated_at"]
        )

        return Response(
            ExaminationSerializer(
                examination,
                context=self.get_serializer_context(),
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="unpublish",
    )
    def unpublish(self, request, pk=None):
        examination = self.get_object()
        examination.status = Examination.Status.DRAFT
        examination.published_at = None
        examination.save(
            update_fields=["status", "published_at", "updated_at"]
        )

        return Response(
            ExaminationSerializer(
                examination,
                context=self.get_serializer_context(),
            ).data
        )


class ExaminationImportViewSet(
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanManageExaminations]
    serializer_class = ExaminationImportSerializer

    def get_queryset(self):
        queryset = (
            ExaminationImport.objects
            .select_related("examination", "uploaded_by")
            .all()
        )

        examination_id = self.request.query_params.get("examination")
        status_value = self.request.query_params.get("status")

        if examination_id:
            queryset = queryset.filter(examination_id=examination_id)

        if status_value:
            queryset = queryset.filter(status=status_value)

        return queryset

    @action(
        detail=True,
        methods=["get"],
        url_path="rows",
    )
    def rows(self, request, pk=None):
        import_batch = self.get_object()

        queryset = (
            import_batch.rows
            .select_related("matched_student", "import_batch__examination")
            .all()
        )

        match_status = request.query_params.get("match_status")
        if match_status:
            queryset = queryset.filter(match_status=match_status)

        serializer = ExaminationImportRowSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(
        detail=True,
        methods=["post"],
        url_path="process",
    )
    def process(self, request, pk=None):
        import_batch = self.get_object()
        process_examination_import(import_batch.pk)
        import_batch.refresh_from_db()

        return Response(
            ExaminationImportSerializer(
                import_batch,
                context=self.get_serializer_context(),
            ).data
        )

    @action(
        detail=True,
        methods=["post"],
        url_path="confirm",
    )
    def confirm(self, request, pk=None):
        import_batch = self.get_object()

        serializer = ConfirmImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = confirm_examination_import(
            import_id=import_batch.pk,
            allow_partial=serializer.validated_data["allow_partial"],
        )

        return Response(
            {
                "import": ExaminationImportSerializer(
                    result["import_batch"],
                    context=self.get_serializer_context(),
                ).data,
                "created_count": result["created_count"],
                "updated_count": result["updated_count"],
            }
        )


class ExaminationImportRowViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [CanManageExaminations]
    serializer_class = ExaminationImportRowSerializer

    def get_queryset(self):
        return (
            ExaminationImportRow.objects
            .select_related(
                "matched_student",
                "import_batch",
                "import_batch__examination",
            )
            .all()
        )

    def perform_update(self, serializer):
        row = serializer.save()
        row.full_clean()
        row.save()
        refresh_import_stats(row.import_batch)


class MyExaminationResultsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        student = resolve_student_for_user(request.user)

        if student is None:
            return Response([])

        queryset = (
            ExaminationResult.objects
            .select_related(
                "student",
                "examination",
                "source_import",
            )
            .filter(
                student=student,
                examination__status=Examination.Status.PUBLISHED,
            )
        )

        academic_year = request.query_params.get("academic_year")
        if academic_year:
            queryset = queryset.filter(
                examination__academic_year=academic_year
            )

        serializer = ExaminationResultSerializer(
            queryset,
            many=True,
            context={"request": request},
        )
        return Response(serializer.data)


def _students_with_results():
    results = (
        ExaminationResult.objects
        .select_related("examination")
        .filter(examination__academic_year__in=ACADEMIC_YEARS)
        .order_by("examination__academic_year", "examination__examination_date", "examination__name")
    )
    return CBAStudentReference.objects.prefetch_related(
        Prefetch("examination_results", queryset=results, to_attr="summary_results")
    )


def _summary_record(student):
    return {
        "id": student.id,
        "student_number": student.student_number,
        "full_name": student.full_name,
        **summarize_results(student.summary_results),
    }


class ExaminationStudentListView(APIView):
    permission_classes = [CanManageExaminations]

    def get(self, request):
        queryset = _students_with_results()
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(student_number__icontains=search)
                | Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
            )

        records = [_summary_record(student) for student in queryset]
        academic_year = request.query_params.get("academic_year")
        final_grade = request.query_params.get("final_grade")
        no_results = request.query_params.get("no_results") in {"1", "true"}
        incomplete = request.query_params.get("incomplete") in {"1", "true"}

        if academic_year in {str(year) for year in ACADEMIC_YEARS}:
            records = [
                record for record in records
                if record["yearly_averages"][academic_year] is not None
            ]
        if final_grade:
            records = [record for record in records if record["final_grade"] == final_grade]
        if no_results:
            records = [record for record in records if record["examinations_written"] == 0]
        if incomplete:
            records = [
                record for record in records
                if record["examinations_written"] > 0
                and any(value is None for value in record["yearly_averages"].values())
            ]

        ordering = request.query_params.get("ordering", "full_name")
        descending = ordering.startswith("-")
        field = ordering.lstrip("-")
        if field in {"student_number", "full_name", "examinations_written", "overall_average", "final_grade"}:
            records.sort(
                key=lambda record: (record[field] is None, record[field] or ""),
                reverse=descending,
            )

        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 25))))
        except (TypeError, ValueError):
            raise ValidationError("Page and page size must be valid integers.")
        count = len(records)
        start = (page - 1) * page_size
        return Response({
            "count": count,
            "page": page,
            "page_size": page_size,
            "results": records[start:start + page_size],
        })


class ExaminationStudentTranscriptView(APIView):
    permission_classes = [CanManageExaminations]

    def get_student_and_transcript(self, student_id):
        student = _students_with_results().filter(pk=student_id).first()
        if student is None:
            from rest_framework.exceptions import NotFound
            raise NotFound("Student transcript is unavailable.")
        return student, build_transcript(student, student.summary_results)

    def get(self, request, student_id):
        _, transcript = self.get_student_and_transcript(student_id)
        transcript["generated_date"] = timezone.localdate()
        return Response(transcript)


class ExaminationStudentTranscriptPDFView(ExaminationStudentTranscriptView):
    def get(self, request, student_id):
        student, transcript = self.get_student_and_transcript(student_id)
        pdf = render_transcript_pdf(transcript)
        safe_name = (slugify(student.full_name) or "student").title()
        filename = f"{student.student_number}-{safe_name}-Transcript-2024-2026.pdf"
        response = HttpResponse(pdf, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
