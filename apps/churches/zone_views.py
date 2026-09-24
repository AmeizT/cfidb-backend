from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from apps.churches.zone_serializers import ZoneIdentitySerializer
from apps.churches.services.regional_scope import permitted_zones


class ZoneIdentityView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ZoneIdentitySerializer

    def get_queryset(self):
        return permitted_zones(self.request.user)
