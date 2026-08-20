from rest_framework import serializers
from apps.bookkeeper.models import Income
from apps.churches.serializers import CountryInfoSerializer

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







