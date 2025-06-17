from django.db import models
from django.db.models import Q
from apps.bookkeeper.models import (
    Asset, 
    Income, 
    Expenditure, 
    FixedExpenditure,
    MonthlyFinanceSnapshot, 
    Payroll, 
    Pledge, 
    Remittance,
    ShortfallPayment,
    Tithe
)
from rest_framework import serializers
from apps.churches.models import Church
from apps.people.serializers.database import MemberSerializer
from apps.users.serializers import ListUserSerializer, MinifiedUserSerializer, UserNamesSerializer
from apps.churches.serializers import AssemblyISOSerializer, CountryInfoSerializer, LocaleSerializer
from apps.bookkeeper.models import AssetImage
from datetime import date
from django.utils import timezone


class AssetImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetImage
        fields = "__all__"
        
class AssetSerializer(serializers.ModelSerializer):
    assembly = AssemblyISOSerializer()
    asset_images = AssetImageSerializer(many=True, read_only=True)

    class Meta:
        model = Asset
        fields = [
            "id",
            "assembly", 
            "item_code", 
            "item_name", 
            "description", 
            "condition",
            "asset_type", 
            "units",
            "acquisition_date", 
            "acquisition_cost", 
            "residual",
            "vendor",
            "asset_images", 
            "created_by",
            "created_at",
            "updated_at",

            # "name", 
            # "asset_type", 
            # "assembly", 
            # "condition",
            # "created_at",
            # "created_by",
            # "description", 
            # "id", 
            # "purchase_date", 
            # "purchase_price", 
            # "quantity", 
            # "serial_number", 
            # "supplier",
            # "updated_at",
            # "current_value",
        ]

class CreateAssetSerializer(serializers.ModelSerializer):
    images = AssetImageSerializer(many=True, read_only=True)
    asset_images = serializers.ListField(
        child=serializers.ImageField(max_length=1000000, allow_empty_file=False, use_url=False),
        write_only=True
    )
    class Meta:
        model = Asset
        fields = [
            "assembly", 
            "item_code", 
            "item_name", 
            "description", 
            "condition",
            "asset_type", 
            "units",
            "acquisition_date", 
            "acquisition_cost", 
            "residual",
            "vendor",
            "images", 
            "asset_images",
            "created_by",
        ]

    def create(self, validated_data):
        asset_images = validated_data.pop('asset_images')
        asset = Asset.objects.create(**validated_data)
        for image in asset_images:
            AssetImage.objects.create(asset=asset, image=image)
        return asset
        
    
class IncomeSerializer(serializers.ModelSerializer):
    church = CountryInfoSerializer()
    class Meta:
        model = Income
        fields = [
            'id',
            'church',
            'timestamp',
            'offering',
            'fundraising',
            'thanksgiving',
            'donations',
            'total_income',
            'statement',
            'created_at',
            'updated_at',
        ]


class CreateIncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = '__all__'


class CreateFixedExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedExpenditure
        fields = '__all__'


class FixedExpenditureSerializer(serializers.ModelSerializer):
    assembly = AssemblyISOSerializer()
    remittance_moderator = UserNamesSerializer()
    
    class Meta:
        model = FixedExpenditure
        fields = [
            "id",
            "assembly",
            "created_by",
            "timestamp",
            "rent",
            "wages",
            "water",
            "electricity",
            "telephone",
            "internet",
            "security",
            "fuel",
            "car_maintenance",
            "humanitarian",
            "investment",
            "bank_charges",
            "insurance",
            "remarks",
            "remittance",
            "remittance_receipt",
            "remittance_moderator",
            "is_remittance_verified"
        ]
        
        
class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
            

class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'     


class PledgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pledge
        fields = '__all__' 


class ShortfallPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShortfallPayment
        fields = '__all__' 

class RemittanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Remittance
        fields = '__all__' 


class RemittanceDataSerializer(serializers.ModelSerializer):
    shortfall_payments = ShortfallPaymentSerializer(many=True)
    editor = MinifiedUserSerializer()

    class Meta:
        model = Remittance
        fields = [
            'id',
            'branch',
            'editor',
            'period',
            'amount_due', 
            'amount_paid', 
            'shortfall', 
            'timestamp', 
            'shortfall_payments', 
            'has_shortfall',
            'created_at',
            'updated_at',
        ]


class TitheSerializer(serializers.ModelSerializer):
    member = MemberSerializer()
    branch = AssemblyISOSerializer()

    class Meta:
        model = Tithe
        fields = [
            'id', 
            'branch', 
            'member', 
            'amount', 
            'payment_method', 
            'receipt', 
            'timestamp',
            'created_at', 
            'updated_at'
        ]
        
        
class CreateTitheSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tithe
        fields = "__all__"



from rest_framework import serializers

class MonthlyIncomeSummarySerializer(serializers.Serializer):
    month = serializers.IntegerField()
    year = serializers.IntegerField()
    total_offering = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_fundraising = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_thanksgiving = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_donations = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_income = serializers.DecimalField(max_digits=10, decimal_places=2)


from rest_framework import serializers
from decimal import Decimal
from apps.bookkeeper.models import Income, FixedExpenditure, Expenditure, Tithe
from django.db.models import Sum

class FinanceSummarySerializer:
    @staticmethod
    def safe_value(obj, attr, default=Decimal("0")):
        return getattr(obj, attr, default) if obj else default

    @staticmethod
    def get_data(church: Church, year: int, month: int, *, skip_recursion=False):
        # Filter by month/year
        income = Income.objects.filter(
            church=church,
            timestamp__year=year,
            timestamp__month=month
        ).first()

        tithes_total = Tithe.objects.filter(
            branch=church,
            timestamp__year=year,
            timestamp__month=month
        ).aggregate(total=Sum("amount"))['total'] or Decimal("0")

        remittance = Decimal(tithes_total) * Decimal("0.25")

        fixed_expenses = FixedExpenditure.objects.filter(
            assembly=church,
            timestamp__year=year,
            timestamp__month=month
        ).first()

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

        total_expenses = total_fixed + total_flexible + remittance
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

        # Determine start year for valid book balance data
        start_year = 2025

        snapshot = MonthlyFinanceSnapshot.objects.filter(
            church=church, year=year, month=month
        ).first()
        book_balance = snapshot.balance if snapshot else Decimal("0")

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
                "remittance": remittance,
            },
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
            "totals": FinanceSummarySerializer.aggregate_yearly_totals(result)
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
