from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.examinations.views import (
    CBAStudentReferenceViewSet,
    ExaminationImportRowViewSet,
    ExaminationImportViewSet,
    ExaminationViewSet,
    ExaminationStudentListView,
    ExaminationStudentTranscriptPDFView,
    ExaminationStudentTranscriptView,
    MyExaminationResultsView,
)


router = DefaultRouter()
router.register(
    "cba-students",
    CBAStudentReferenceViewSet,
    basename="cba-student",
)
router.register(
    "examinations",
    ExaminationViewSet,
    basename="examination",
)
router.register(
    "examination-imports",
    ExaminationImportViewSet,
    basename="examination-import",
)
router.register(
    "examination-import-rows",
    ExaminationImportRowViewSet,
    basename="examination-import-row",
)


urlpatterns = [
    path("", include(router.urls)),
    path(
        "examination-students/",
        ExaminationStudentListView.as_view(),
        name="examination-students",
    ),
    path(
        "examination-students/<int:student_id>/transcript/",
        ExaminationStudentTranscriptView.as_view(),
        name="examination-student-transcript",
    ),
    path(
        "examination-students/<int:student_id>/transcript/pdf/",
        ExaminationStudentTranscriptPDFView.as_view(),
        name="examination-student-transcript-pdf",
    ),
    path(
        "students/me/examination-results/",
        MyExaminationResultsView.as_view(),
        name="my-examination-results",
    ),
]
