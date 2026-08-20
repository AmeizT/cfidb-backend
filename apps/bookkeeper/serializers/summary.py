from django.db import models
from rest_framework import serializers
from apps.bookkeeper.models import (
    Income, 
    Expenditure, 
    FixedExpenditure,
    RemittancePayment,
    Tithe,
)
from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework import serializers
from apps.churches.models import Church
from apps.churches.serializers import LocaleSerializer
from apps.bookkeeper.models import Income, FixedExpenditure, Expenditure, Tithe

class MonthlyIncomeSummarySerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_offering = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_fundraising = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_thanksgiving = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_donations = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)


class FinanceSummarySerializer:
    @staticmethod
    def safe_value(obj, attr, default=Decimal("0")):
        return getattr(obj, attr, default) if obj else default

    @staticmethod
    def latest_monthly(queryset):
        return queryset.order_by("-updated_at", "-created_at", "-id").first()

    @staticmethod
    def get_data(church: Church, year: int, month: int, *, skip_recursion=False):
        # Filter by month/year
        income = FinanceSummarySerializer.latest_monthly(Income.objects.filter(
            church=church,
            timestamp__year=year,
            timestamp__month=month
        ))

        tithes_total = Tithe.objects.filter(
            assembly=church,
            timestamp__year=year,
            timestamp__month=month
        ).aggregate(total=Sum("amount"))['total'] or Decimal("0")

        remittance_due = (Decimal(tithes_total) * Decimal("0.10")).quantize(Decimal("0.01"))
        remittance_paid = RemittancePayment.objects.filter(
            report__assembly=church,
            payment_date__year=year,
            payment_date__month=month,
            status=RemittancePayment.Status.VERIFIED,
        ).aggregate(total=Sum("amount_paid"))["total"] or Decimal("0")

        fixed_expenses = FinanceSummarySerializer.latest_monthly(FixedExpenditure.objects.filter(
            assembly=church,
            timestamp__year=year,
            timestamp__month=month
        ))

        flexible_expenses = Expenditure.objects.filter(
            assembly=church,
            invoice_date__year=year,
            invoice_date__month=month
        )

        flexible_expense_list = [
            {
                "title": expense.name,
                "amount": expense.price,
                "category": expense.category,
                "timestamp": expense.invoice_date,
            }
            for expense in flexible_expenses
        ]

        total_flexible = sum(e['amount'] for e in flexible_expense_list)
        total_fixed = FinanceSummarySerializer.safe_value(fixed_expenses, "total")

        total_expenses = total_fixed + total_flexible + remittance_paid
        gross_income = FinanceSummarySerializer.safe_value(income, "total_income")
        total_income = gross_income + tithes_total
        balance = total_income - total_expenses

        previous_totals = {}

        if not skip_recursion:
            if month == 1:
                prev_month = 12
                prev_year = year - 1
            else:
                prev_month = month - 1
                prev_year = year

            if prev_year >= 2000:
                previous_data = FinanceSummarySerializer.get_data(church, prev_year, prev_month, skip_recursion=True)
                previous_totals = previous_data.get("totals", {})

        start_year = 2025
        book_balance = FinanceSummarySerializer.get_book_balance(church, year, month)

        # Prepare fixedExpensesList
        fixedExpensesList = []
        # Get previous month fixed expenses
        if month == 1:
            prev_month = 12
            prev_year = year - 1
        else:
            prev_month = month - 1
            prev_year = year

        prev_fixed_expenses = FinanceSummarySerializer.latest_monthly(FixedExpenditure.objects.filter(
            assembly=church,
            timestamp__year=prev_year,
            timestamp__month=prev_month
        ))

        # Sum of fixed expenses with remittance for current month
        total_fixed_with_remittance = total_fixed + remittance_paid

        # List of decimal fields to consider excluding id and total
        decimal_fields = [field for field in FixedExpenditure._meta.fields if isinstance(field, models.DecimalField) and field.name not in ["id", "total"]]

        for field in decimal_fields:
            amount = FinanceSummarySerializer.safe_value(fixed_expenses, field.name)
            prev_amount = FinanceSummarySerializer.safe_value(prev_fixed_expenses, field.name)
            trend = None
            if prev_amount != 0:
                trend = ((amount - prev_amount) / prev_amount) * 100

            percentage = None
            if total_fixed_with_remittance != 0:
                percentage = (amount / total_fixed_with_remittance) * 100

            fixedExpensesList.append({
                "name": field.name,
                "amount": amount,
                "previous": prev_amount,
                "trend": float(trend) if trend is not None else None,
                "percentage": float(percentage) if percentage is not None else None,
            })

        # Prepare incomeList
        incomeList = []
        prev_income = FinanceSummarySerializer.latest_monthly(Income.objects.filter(
            church=church,
            timestamp__year=prev_year,
            timestamp__month=prev_month
        ))

        income_fields = [
            field for field in Income._meta.fields
            if isinstance(field, models.DecimalField) and field.name not in ["id", "total_income"]
        ]

        total_income_with_tithes = gross_income + tithes_total

        for field in income_fields:
            amount = FinanceSummarySerializer.safe_value(income, field.name)
            prev_amount = FinanceSummarySerializer.safe_value(prev_income, field.name)
            trend = None
            if prev_amount != 0:
                trend = ((amount - prev_amount) / prev_amount) * 100

            percentage = None
            if total_income_with_tithes != 0:
                percentage = (amount / total_income_with_tithes) * 100

            incomeList.append({
                "name": field.name,
                "amount": amount,
                "previous": prev_amount,
                "trend": float(trend) if trend is not None else None,
                "percentage": float(percentage) if percentage is not None else None,
            })

        # Add tithesTotal to incomeList
        prev_tithes_total = Tithe.objects.filter(
            assembly=church,
            timestamp__year=prev_year,
            timestamp__month=prev_month
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
        trend = None
        if prev_tithes_total != 0:
            trend = ((tithes_total - prev_tithes_total) / prev_tithes_total) * 100
        percentage = None
        if total_income_with_tithes != 0:
            percentage = (tithes_total / total_income_with_tithes) * 100
        incomeList.append({
            "name": "tithes",
            "amount": tithes_total,
            "previous": prev_tithes_total,
            "trend": float(trend) if trend is not None else None,
            "percentage": float(percentage) if percentage is not None else None,
        })

        return {
            "income": {
                "gross_income": gross_income,
                "breakdown": {
                    "offering": FinanceSummarySerializer.safe_value(income, "offering"),
                    "thanksgiving": FinanceSummarySerializer.safe_value(income, "thanksgiving"),
                    "fundraising": FinanceSummarySerializer.safe_value(income, "fundraising"),
                    "donations": FinanceSummarySerializer.safe_value(income, "donations"),
                },
                "tithes": tithes_total,
            },
            "fixedExpenses": {
                **{
                    field.name: FinanceSummarySerializer.safe_value(fixed_expenses, field.name)
                    for field in FixedExpenditure._meta.fields
                    if isinstance(field, models.DecimalField) and field.name not in ["id", "total"]
                },
                "remittance": remittance_due,
                "remittance_due": remittance_due,
                "remittance_verified_paid": remittance_paid,
                "remittance_outstanding": max(remittance_due - remittance_paid, Decimal("0")),
            },
            "fixedExpensesList": fixedExpensesList,
            "incomeList": incomeList,
            "flexibleExpenses": flexible_expense_list,
            "totals": {
                "totalTithes": tithes_total,
                "totalIncome": total_income,
                "totalExpenses": total_expenses,
                "balance": balance,
                "balance_carried_forward": previous_totals.get("balance", Decimal("0")),
                "bookBalance": book_balance,
                "expenseToIncomeRatio": float(total_expenses) / float(total_income) if total_income else 0,
            },
            "locale": LocaleSerializer(church).data,
            "timestamp": {
                "year": year,
                "month": month,
                "month_name": date(year, month, 1).strftime("%B"),
            },
            "meta": {
                "church_id": church.id,
                "generated_at": timezone.now(),
            },
        }

    @staticmethod
    def get_yearly_data(church: Church, year: int):
        result = []
        for month in range(1, 13):
            result.append(FinanceSummarySerializer.get_data(church, year, month, skip_recursion=True))
        return {
            "year": year,
            "monthlySummaries": result,
            "totals": FinanceSummarySerializer.aggregate_yearly_totals(result),
            "expenditureSeries": FinanceSummarySerializer.get_expenditure_series(result),
            "incomeSeries": FinanceSummarySerializer.get_income_series(result),
        }

    @staticmethod
    def aggregate_yearly_totals(monthly_data):
        total_income = sum(m['totals']['totalIncome'] for m in monthly_data)
        total_expenses = sum(m['totals']['totalExpenses'] for m in monthly_data)
        total_tithes = sum(m['totals']['totalTithes'] for m in monthly_data)
        balance = total_income - total_expenses

        return {
            "totalIncome": total_income,
            "totalExpenses": total_expenses,
            "totalTithes": total_tithes,
            "balance": balance,
            "expenseToIncomeRatio": float(total_expenses) / float(total_income) if total_income else 0,
        }

    @staticmethod
    def get_book_balance(church, year, month):
        book_balance = Decimal("0")

        for m in range(1, month + 1):
            income = FinanceSummarySerializer.latest_monthly(Income.objects.filter(
                church=church, timestamp__year=year, timestamp__month=m
            ))

            fixed = FinanceSummarySerializer.latest_monthly(FixedExpenditure.objects.filter(
                assembly=church, timestamp__year=year, timestamp__month=m
            ))

            flexible_total = Expenditure.objects.filter(
                assembly=church, invoice_date__year=year, invoice_date__month=m
            ).aggregate(total=models.Sum("price"))["total"] or Decimal("0")

            tithes_total = Tithe.objects.filter(
                assembly=church, timestamp__year=year, timestamp__month=m
            ).aggregate(total=models.Sum("amount"))["total"] or Decimal("0")

            month_income = (income.total_income if income else Decimal("0")) + tithes_total
            verified_remittance = RemittancePayment.objects.filter(
                report__assembly=church,
                payment_date__year=year,
                payment_date__month=m,
                status=RemittancePayment.Status.VERIFIED,
            ).aggregate(total=models.Sum("amount_paid"))["total"] or Decimal("0")
            month_expenses = (
                (fixed.total if fixed else Decimal("0"))
                + flexible_total
                + verified_remittance
            )

            # Add the month’s savings to running book balance
            month_savings = month_income - month_expenses
            book_balance += month_savings

        return book_balance

    @staticmethod
    def get_expenditure_series(monthly_data):
        return [{"month": m["timestamp"]["month_name"], "total": m["totals"]["totalExpenses"]} for m in monthly_data]

    @staticmethod
    def get_income_series(monthly_data):
        return [{"month": m["timestamp"]["month_name"], "total": m["totals"]["totalIncome"]} for m in monthly_data]
