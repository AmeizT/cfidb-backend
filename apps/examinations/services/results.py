from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from apps.examinations.models import ResultStatus


ACADEMIC_YEARS = (2024, 2025, 2026)
TWO_PLACES = Decimal("0.01")


def round_percentage(value):
    if value is None:
        return None
    return Decimal(value).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def calculate_percentage(score, total_marks):
    if score is None or not total_marks:
        return None
    return round_percentage(_raw_percentage(score, total_marks))


def _raw_percentage(score, total_marks):
    if score is None or not total_marks:
        return None
    return (Decimal(score) / Decimal(total_marks)) * 100


def grade_for_percentage(value):
    if value is None:
        return None

    percentage = Decimal(value)
    if percentage >= 90:
        return "A+"
    if percentage >= 85:
        return "A"
    if percentage >= 80:
        return "A-"
    if percentage >= 75:
        return "B+"
    if percentage >= 70:
        return "B"
    if percentage >= 65:
        return "B-"
    if percentage >= 60:
        return "C+"
    if percentage >= 55:
        return "C"
    if percentage >= 50:
        return "D"
    return "F"


def summarize_results(results):
    grouped = defaultdict(list)
    examinations_written = 0

    for result in results:
        year = result.examination.academic_year
        if year in ACADEMIC_YEARS:
            grouped[year].append(result)
        if result.status == ResultStatus.SCORED:
            examinations_written += 1

    yearly_averages = {}
    for year in ACADEMIC_YEARS:
        percentages = [
            _raw_percentage(result.score, result.examination.total_marks)
            for result in grouped[year]
            if result.status == ResultStatus.SCORED
        ]
        percentages = [value for value in percentages if value is not None]
        yearly_averages[str(year)] = (
            round_percentage(sum(percentages) / len(percentages))
            if percentages
            else None
        )

    available = [value for value in yearly_averages.values() if value is not None]
    overall_average = (
        round_percentage(sum(available) / len(available)) if available else None
    )

    return {
        "examinations_written": examinations_written,
        "yearly_averages": yearly_averages,
        "overall_average": overall_average,
        "final_grade": grade_for_percentage(overall_average),
        "overall_result": (
            "Pass" if overall_average is not None and overall_average >= 50 else
            "Fail" if overall_average is not None else None
        ),
    }


def serialize_result(result):
    percentage = (
        calculate_percentage(result.score, result.examination.total_marks)
        if result.status == ResultStatus.SCORED else None
    )
    return {
        "id": result.id,
        "examination_id": result.examination_id,
        "examination_name": result.examination.name,
        "examination_date": result.examination.examination_date,
        "academic_year": result.examination.academic_year,
        "score": round_percentage(result.score),
        "total_marks": round_percentage(result.examination.total_marks),
        "percentage": percentage,
        "status": result.status,
        "grade": grade_for_percentage(percentage),
    }


def build_transcript(student, results):
    results = list(results)
    summary = summarize_results(results)
    grouped_results = {str(year): [] for year in ACADEMIC_YEARS}
    for result in results:
        year = result.examination.academic_year
        if year in ACADEMIC_YEARS:
            grouped_results[str(year)].append(serialize_result(result))

    return {
        "student": {
            "id": student.id,
            "student_number": student.student_number,
            "full_name": student.full_name,
        },
        "academic_period": "2024–2026",
        "results": grouped_results,
        **summary,
    }
