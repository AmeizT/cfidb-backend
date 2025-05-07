# apps/integrations/serializers.py

from rest_framework import serializers
from apps.integrations.models import IntegrationProvider, Integration

class IntegrationProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = IntegrationProvider
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class IntegrationSerializer(serializers.ModelSerializer):
    integration_provider = IntegrationProviderSerializer(read_only=True)
    integration_provider_id = serializers.PrimaryKeyRelatedField(
        queryset=IntegrationProvider.objects.all(), write_only=True, source="integration_provider"
    )

    class Meta:
        model = Integration
        fields = [
            'id',
            'integration_id',
            'integration_type',
            'integration_provider',
            'integration_provider_id',
            'user',
            'meta_data',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']