from rest_framework import serializers
from apps.bookkeeper.models import Asset
from rest_framework import serializers
from apps.bookkeeper.models import AssetImage
from apps.churches.serializers import AssemblyISOSerializer

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