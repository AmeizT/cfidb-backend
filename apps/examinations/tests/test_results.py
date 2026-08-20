from datetime import date
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from pypdf import PdfReader

from apps.examinations.models import (
    CBAStudentReference,
    Examination,
    ExaminationResult,
    ResultStatus,
)
from apps.examinations.services.results import (
    build_transcript,
    calculate_percentage,
    grade_for_percentage,
    summarize_results,
)
from apps.examinations.services.transcript_pdf import render_transcript_pdf


def result(pk, year, score, total=100, status=ResultStatus.SCORED, name="Exam"):
    examination = SimpleNamespace(
        academic_year=year,
        total_marks=Decimal(str(total)),
        examination_date=date(year, 6, 1),
        name=name,
    )
    return SimpleNamespace(
        id=pk,
        examination_id=pk,
        examination=examination,
        score=None if score is None else Decimal(str(score)),
        status=status,
    )


class ResultCalculationTests(SimpleTestCase):
    def test_percentages_are_normalized_for_different_total_marks(self):
        self.assertEqual(calculate_percentage(40, 50), Decimal("80.00"))
        self.assertEqual(calculate_percentage(120, 150), Decimal("80.00"))

    def test_grade_boundaries(self):
        expected = {
            "90": "A+", "89.99": "A", "85": "A", "84.99": "A-",
            "80": "A-", "75": "B+", "70": "B", "65": "B-",
            "60": "C+", "55": "C", "50": "D", "49.99": "F", "0": "F",
        }
        for percentage, grade in expected.items():
            with self.subTest(percentage=percentage):
                self.assertEqual(grade_for_percentage(Decimal(percentage)), grade)

    def test_absent_results_are_not_counted(self):
        summary = summarize_results([
            result(1, 2024, 0),
            result(2, 2024, None, status=ResultStatus.ABSENT),
            result(3, 2024, None, status=ResultStatus.WITHHELD),
        ])
        self.assertEqual(summary["examinations_written"], 1)
        self.assertEqual(summary["yearly_averages"]["2024"], Decimal("0.00"))
        self.assertEqual(summary["final_grade"], "F")

    def test_overall_average_uses_only_available_years(self):
        summary = summarize_results([
            result(1, 2024, 40, total=50),
            result(2, 2026, 60, total=100),
        ])
        self.assertEqual(summary["yearly_averages"]["2025"], None)
        self.assertEqual(summary["overall_average"], Decimal("70.00"))
        self.assertEqual(summary["final_grade"], "B")
        self.assertEqual(summary["overall_result"], "Pass")

    def test_year_average_is_mean_of_normalized_exam_percentages(self):
        summary = summarize_results([
            result(1, 2024, 45, total=50),
            result(2, 2024, 60, total=100),
        ])
        self.assertEqual(summary["yearly_averages"]["2024"], Decimal("75.00"))

    def test_transcript_pdf_is_generated_with_all_year_sections(self):
        student = SimpleNamespace(id=3, student_number="S2629012", full_name="Tuamena Matheus")
        transcript = build_transcript(student, [
            result(1, 2024, 45, total=50, name="Foundations of Faith"),
            result(2, 2025, None, status=ResultStatus.ABSENT, name="Christian Leadership"),
            result(3, 2026, 75, name="Biblical Interpretation"),
        ])
        pdf = render_transcript_pdf(transcript)
        self.assertTrue(pdf.startswith(b"%PDF"))
        reader = PdfReader(BytesIO(pdf))
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        self.assertIn("2024 Examination Results", text)
        self.assertIn("2025 Examination Results", text)
        self.assertIn("2026 Examination Results", text)
        self.assertIn("Tuamena Matheus", text)


class ResultIntegrityTests(TestCase):
    def setUp(self):
        self.student = CBAStudentReference.objects.create(
            source_id=1,
            student_number="S2629012",
            first_name="Tuamena",
            last_name="Matheus",
        )
        self.examination = Examination.objects.create(
            name="Foundations",
            academic_year=2024,
            examination_date=date(2024, 6, 1),
            total_marks=Decimal("50"),
            pass_mark=Decimal("25"),
        )

    def test_student_cannot_have_duplicate_results_for_an_examination(self):
        ExaminationResult.objects.create(
            examination=self.examination,
            student=self.student,
            student_number_snapshot=self.student.student_number,
            score=Decimal("40"),
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            ExaminationResult.objects.create(
                examination=self.examination,
                student=self.student,
                student_number_snapshot=self.student.student_number,
                score=Decimal("30"),
            )

    def test_absent_result_requires_null_score(self):
        invalid = ExaminationResult(
            examination=self.examination,
            student=self.student,
            student_number_snapshot=self.student.student_number,
            score=Decimal("0"),
            status=ResultStatus.ABSENT,
        )
        with self.assertRaisesMessage(Exception, "cannot have a score"):
            invalid.full_clean()
