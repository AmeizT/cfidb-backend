from django.db.models import Q
from rest_framework import permissions, serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from apps.people.create_security import active_create_assembly
from apps.people.models import Member, Ministry, Position


class CreateOptionsInput(serializers.Serializer):
    search = serializers.CharField(required=False, allow_blank=True, max_length=100)
    page = serializers.IntegerField(required=False, default=1, min_value=1)


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
def create_options(request):
    """Read-only selector search; personal search terms stay out of URLs."""
    assembly = active_create_assembly(request)
    data = CreateOptionsInput(data=request.data)
    data.is_valid(raise_exception=True)
    members = Member.objects.filter(assembly=assembly).order_by("last_name", "first_name", "pk")
    search = data.validated_data.get("search", "")
    if search:
        members = members.filter(Q(first_name__icontains=search) | Q(last_name__icontains=search))
    start = (data.validated_data["page"] - 1) * 50
    rows = list(members.only("id", "first_name", "middle_name", "last_name")[start:start + 51])
    return Response({
        "assembly": {"id": assembly.pk, "name": assembly.name},
        "can_create_member": True,
        "members": [{"id": member.pk, "label": member.full_name} for member in rows[:50]],
        "has_more": len(rows) > 50,
        # These are global catalogues, with no assembly ownership or personal data.
        "ministries": list(Ministry.objects.order_by("name").values_list("name", flat=True)),
        "positions": list(Position.objects.order_by("name").values_list("name", flat=True)),
    })
