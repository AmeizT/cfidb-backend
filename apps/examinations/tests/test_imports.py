from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase

from apps.examinations.models import (
    CBAStudentReference,
    Examination,
    ExaminationImport,
    ExaminationImportRow,
    ResultStatus,
)
from apps.examinations.serializers import ExaminationImportRowSerializer
from apps.examinations.services.cba_students import sync_cba_students
from apps.examinations.services.imports import (
    confirm_examination_import,
    parse_examination_text,
    process_examination_import,
)
from apps.examinations.utils import normalize_student_number


class StudentNumberNormalizationTests(SimpleTestCase):
    def test_supported_student_number_variants_normalize_identically(self):
        variants = [
            "S2426007",
            "S24260 07",
            "S24 26007",
            "S 2426007",
            " S2426007",
            "S2426007 ",
            "S2426-007",
        ]

        for value in variants:
            with self.subTest(value=value):
                self.assertEqual(
                    normalize_student_number(value),
                    "S2426007",
                )

    def test_parser_preserves_raw_number_and_normalizes_for_matching(self):
        rows = parse_examination_text("S24260 07 | 80", Decimal("100"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].raw_student_number, "S24260 07")
        self.assertEqual(rows[0].normalized_student_number, "S2426007")
        self.assertEqual(rows[0].score, Decimal("80"))

    def test_parser_does_not_consume_space_separated_score(self):
        rows = parse_examination_text("S2427015 60", Decimal("100"))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].raw_student_number, "S2427015")
        self.assertEqual(rows[0].normalized_student_number, "S2427015")
        self.assertEqual(rows[0].score, Decimal("60"))


class ExaminationImportStudentNumberTests(TestCase):
    def setUp(self):
        self.student = CBAStudentReference.objects.create(
            source_id=2426007,
            student_number="S2426007",
            first_name="Normalized",
            last_name="Student",
        )
        self.examination = Examination.objects.create(
            name="Student Number Matching",
            academic_year=2026,
            total_marks=Decimal("100"),
        )

    def create_import(self):
        return ExaminationImport.objects.create(
            examination=self.examination,
            pdf_file="examinations/test-import.pdf",
            original_filename="test-import.pdf",
        )

    def process_text(self, import_batch, text):
        with patch(
            "apps.examinations.services.imports.extract_pdf_text",
            return_value=text,
        ):
            return process_examination_import(import_batch.pk)

    def test_spaced_number_matches_synchronized_student(self):
        import_batch = self.create_import()

        self.process_text(import_batch, "S24260 07 | 80")

        row = import_batch.rows.get()
        import_batch.refresh_from_db()
        self.assertEqual(row.raw_student_number, "S24260 07")
        self.assertEqual(row.normalized_student_number, "S2426007")
        self.assertEqual(row.matched_student, self.student)
        self.assertEqual(
            row.match_status,
            ExaminationImportRow.MatchStatus.MATCHED,
        )
        self.assertEqual(import_batch.matched_rows, 1)
        self.assertEqual(import_batch.invalid_rows, 0)

        confirm_examination_import(import_batch.pk)
        self.assertEqual(
            self.examination.results.get().student_number_snapshot,
            "S2426007",
        )

    def test_duplicate_detection_uses_normalized_number(self):
        import_batch = self.create_import()

        self.process_text(
            import_batch,
            "S24260 07 | 80\nS2426007 | 75",
        )

        rows = list(import_batch.rows.order_by("row_number"))
        self.assertEqual(
            [row.raw_student_number for row in rows],
            ["S24260 07", "S2426007"],
        )
        self.assertEqual(
            {row.normalized_student_number for row in rows},
            {"S2426007"},
        )
        self.assertEqual(
            {row.match_status for row in rows},
            {ExaminationImportRow.MatchStatus.DUPLICATE},
        )

    def test_reprocessing_replaces_invalid_rows_and_refreshes_stats(self):
        import_batch = self.create_import()
        old_row = ExaminationImportRow.objects.create(
            import_batch=import_batch,
            row_number=1,
            raw_student_number="S24260 07",
            normalized_student_number="",
            raw_result="80",
            score=Decimal("80"),
            result_status=ResultStatus.SCORED,
            match_status=ExaminationImportRow.MatchStatus.INVALID,
            validation_message="Student number is invalid.",
        )
        import_batch.total_rows = 1
        import_batch.invalid_rows = 1
        import_batch.save(update_fields=["total_rows", "invalid_rows"])

        self.process_text(import_batch, "S24260 07 | 80")

        import_batch.refresh_from_db()
        row = import_batch.rows.get()
        self.assertNotEqual(row.pk, old_row.pk)
        self.assertEqual(row.raw_student_number, "S24260 07")
        self.assertEqual(row.normalized_student_number, "S2426007")
        self.assertEqual(row.matched_student, self.student)
        self.assertEqual(import_batch.total_rows, 1)
        self.assertEqual(import_batch.matched_rows, 1)
        self.assertEqual(import_batch.invalid_rows, 0)
        self.assertEqual(import_batch.duplicate_rows, 0)

    def test_manual_raw_number_correction_recalculates_match(self):
        import_batch = self.create_import()
        row = ExaminationImportRow.objects.create(
            import_batch=import_batch,
            row_number=1,
            raw_student_number="invalid",
            normalized_student_number="INVALID",
            raw_result="80",
            score=Decimal("80"),
            result_status=ResultStatus.SCORED,
            match_status=ExaminationImportRow.MatchStatus.INVALID,
        )
        serializer = ExaminationImportRowSerializer(
            row,
            data={"raw_student_number": "S24 26007"},
            partial=True,
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        corrected = serializer.save()
        self.assertEqual(corrected.raw_student_number, "S24 26007")
        self.assertEqual(corrected.normalized_student_number, "S2426007")
        self.assertEqual(corrected.matched_student, self.student)
        self.assertEqual(
            corrected.match_status,
            ExaminationImportRow.MatchStatus.MATCHED,
        )

    @patch("apps.examinations.services.cba_students.fetch_all_cba_users")
    def test_cba_sync_normalizes_student_number(self, fetch_users):
        self.student.delete()
        fetch_users.return_value = [{
            "id": 99,
            "user_id": "S2426-007",
            "role": "student",
            "first_name": "Synced",
            "last_name": "Student",
        }]

        sync_cba_students()

        self.assertEqual(
            CBAStudentReference.objects.get(source_id=99).student_number,
            "S2426007",
        )
