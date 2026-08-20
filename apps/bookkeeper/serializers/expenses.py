from rest_framework import serializers
from apps.bookkeeper.models import FixedExpenditure, Expenditure
from apps.churches.serializers import AssemblyISOSerializer

class ExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expenditure
        fields = '__all__'
        read_only_fields = ['assembly', 'report', 'created_by', 'timestamp']


class CreateFixedExpenditureSerializer(serializers.ModelSerializer):
    class Meta:
        model = FixedExpenditure
        fields = '__all__'


class FixedExpenditureSerializer(serializers.ModelSerializer):
    assembly = AssemblyISOSerializer()
    
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
    

class FixedExpenditureNormalizedSerializer(serializers.ModelSerializer):
    breakdown = serializers.SerializerMethodField()

    class Meta:
        model = FixedExpenditure
        fields = [
            "id",
            "timestamp",
            "breakdown",
            "total",
            "remarks",
            "is_remittance_verified",
        ]

    def get_breakdown(self, obj):
        fields = {
            "Rent": obj.rent,
            "Water": obj.water,
            "Electricity": obj.electricity,
            "Wages": obj.wages,
            "Bank Charges": obj.bank_charges,
            "Car Maintenance": obj.car_maintenance,
            "Fuel": obj.fuel,
            "Humanitarian": obj.humanitarian,
            "Insurance": obj.insurance,
            "Security": obj.security,
            "Telephone": obj.telephone,
            "Internet": obj.internet,
            "Investment": obj.investment,
            "Remittance": obj.remittance,
        }

        return [
            {"type": name, "amount": value}
            for name, value in fields.items()
            if value and value > 0
        ]
    

class ReportExpenseSerializer(serializers.Serializer):
    fixed_expenses = serializers.SerializerMethodField()
    variable_expenses = serializers.SerializerMethodField()
    total_fixed = serializers.SerializerMethodField()
    total_variable = serializers.SerializerMethodField()
    grand_total = serializers.SerializerMethodField()

    def get_fixed_expenses(self, obj):
        fixed = obj.expenditure_set.all()
        return FixedExpenditureNormalizedSerializer(fixed, many=True).data

    def get_variable_expenses(self, obj):
        variable = obj.variable_expenditure_set.all()
        return ExpenditureSerializer(variable, many=True).data

    def get_total_fixed(self, obj):
        return sum(f.total for f in obj.expenditure_set.all())

    def get_total_variable(self, obj):
        return sum(v.total for v in obj.variable_expenditure_set.all())

    def get_grand_total(self, obj):
        return (
            self.get_total_fixed(obj)
            + self.get_total_variable(obj)
        )