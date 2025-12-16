from rest_framework import serializers
from apps.reports.models import UnifiedReport
from apps.people.serializers.database import AttendanceSerializer
from apps.bookkeeper.serializers import FinanceSummarySerializer, FixedExpenditureSerializer, IncomeSerializer, TitheSerializer

class UnifiedReportSerializer(serializers.ModelSerializer):
    data = serializers.SerializerMethodField()
    finance_summary = serializers.SerializerMethodField()

    class Meta:
        model = UnifiedReport
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at", "finalized_at"]

    def get_data(self, obj):
        return {
            "attendances": AttendanceSerializer(obj.attendance_set.all(), many=True).data,
            "tithes": TitheSerializer(obj.tithe_set.all(), many=True).data,
            "incomes": IncomeSerializer(obj.income_set.all(), many=True).data,
            "expenditures": FixedExpenditureSerializer(obj.expenditure_set.all(), many=True).data,
        }

    def get_finance_summary(self, obj):
        from apps.bookkeeper.models import Church
        church = obj.church

        if not obj.period_start:
            return {}

        year = obj.period_start.year
        month = obj.period_start.month

        return FinanceSummarySerializer.get_data(church, year, month)

    def validate(self, data):
        if self.instance and self.instance.status == "finalized":
            raise serializers.ValidationError("Cannot edit a finalized report. Please ask admin to reopen.")
        return data