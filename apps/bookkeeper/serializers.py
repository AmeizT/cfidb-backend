from apps.bookkeeper.models import (
    Asset, 
    Income, 
    Expenditure, 
    FixedExpenditure, 
    Payroll, 
    Pledge, 
    Remittance,
    ShortfallPayment,
    Tithe
)
from rest_framework import serializers
from apps.people.serializers.database import MemberSerializer
from apps.users.serializers import ListUserSerializer, MinifiedUserSerializer, UserNamesSerializer
from apps.churches.serializers import AssemblyISOSerializer, CountryInfoSerializer
from apps.bookkeeper.models import AssetImage


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
            'sum',
            'expenses',
            'balance',
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
