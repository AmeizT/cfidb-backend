from django_filters.rest_framework import DjangoFilterBackend
from django.db import IntegrityError
from django.utils import timezone
from rest_framework import filters, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.people.filters import MemberFilter
from apps.people.models import AssemblyMembership, MemberTransferRequest
from apps.people.models.members import JuniorMember, Member
from apps.people.permissions import (
    CanManageMembers,
    can_access_assembly,
    filter_membership_queryset_for_user,
    filter_transfer_queryset_for_user,
)
from apps.people.serializers.members import JuniorMemberSerializer, MemberSerializer
from apps.people.schemas import PeopleTableSchemaMixin
from apps.shared.pagination import DataTablePagination
from apps.people.serializers.transfers import AssemblyMembershipSerializer, MemberTransferRequestListSerializer


class MemberView(PeopleTableSchemaMixin, viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    permission_classes = [permissions.IsAuthenticated, CanManageMembers]
    pagination_class = DataTablePagination
    table_schema_name = "members"
    filter_backends = [DjangoFilterBackend]
    filterset_class = MemberFilter
    lookup_field = "member_key"

    def get_queryset(self):
        user = self.request.user

        if getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
            queryset = Member.objects.all()
        elif getattr(user, "is_region_staff", False):
            queryset = Member.objects.filter(assembly__zone__region__in=user.assigned_regions.all()).distinct()
        else:
            queryset = Member.objects.filter(assembly=self.request.user.church)

        if self.request.query_params.get("group") == "adults":
            today = timezone.localdate()
            try:
                cutoff = today.replace(year=today.year - 18)
            except ValueError:
                cutoff = today.replace(year=today.year - 18, day=28)
            queryset = queryset.filter(date_of_birth__lte=cutoff)
        return queryset

    def perform_create(self, serializer):
        from apps.people.create_security import active_create_assembly
        assembly = active_create_assembly(self.request)
        serializer.save(assembly=assembly, created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        self.check_object_permissions(self.request, serializer.instance)
        serializer.save(updated_by=self.request.user)

    def perform_destroy(self, instance):
        self.check_object_permissions(self.request, instance)
        instance.soft_delete(user=self.request.user)

    @action(detail=True, methods=["post"])
    def restore(self, request, member_key=None):
        queryset = Member.all_objects.filter(is_trash=True)
        user = request.user
        if getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
            pass
        elif getattr(user, "is_region_staff", False):
            queryset = queryset.filter(assembly__zone__region__in=user.assigned_regions.all())
        elif getattr(user, "is_db_zone_staff", False):
            queryset = queryset.filter(assembly__zone__in=user.assigned_zones.all())
        else:
            queryset = queryset.filter(assembly=user.church)
        instance = queryset.filter(member_key=member_key).first()
        if instance is None:
            return Response({"detail": "Deleted member not found."}, status=status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, instance)
        try:
            instance.restore(user=request.user)
        except IntegrityError as exc:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({
                "detail": "This member conflicts with an active replacement and cannot be restored."
            }) from exc
        return Response(self.get_serializer(instance).data)

    @action(detail=True, methods=["get"])
    def transfers(self, request, member_key=None):
        member = self.get_object()
        queryset = MemberTransferRequest.objects.select_related(
            "member",
            "from_assembly",
            "to_assembly",
            "requested_by",
            "reviewed_by",
            "completed_by",
        ).filter(member=member)
        queryset = filter_transfer_queryset_for_user(queryset, request.user)
        serializer = MemberTransferRequestListSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(detail=True, methods=["get"], url_path="assembly-memberships")
    def assembly_memberships(self, request, member_key=None):
        member = self.get_object()
        queryset = AssemblyMembership.objects.select_related(
            "member",
            "assembly",
            "created_by",
        ).filter(member=member)
        queryset = filter_membership_queryset_for_user(queryset, request.user)
        serializer = AssemblyMembershipSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)
    

class JuniorMemberView(PeopleTableSchemaMixin, viewsets.ModelViewSet):
    queryset = JuniorMember.objects.all()
    serializer_class = JuniorMemberSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DataTablePagination
    table_schema_name = "children"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["first_name", "middle_name", "last_name", "guardian__first_name", "guardian__last_name"]
    ordering_fields = ["first_name", "last_name", "date_of_birth", "membersince", "membership_status", "created_at"]
    ordering = ["last_name", "first_name"]
    lookup_field = "member_key"

    def get_queryset(self):
        user = self.request.user
        queryset = JuniorMember.objects.select_related("church", "guardian")
        if getattr(user, "is_admin", False) or getattr(user, "is_superuser", False):
            pass
        elif getattr(user, "is_region_staff", False):
            queryset = queryset.filter(church__zone__region__in=user.assigned_regions.all())
        else:
            queryset = queryset.filter(church=user.church)
        gender = self.request.query_params.get("gender")
        status = self.request.query_params.get("status")
        if gender:
            queryset = queryset.filter(gender=gender)
        if status:
            queryset = queryset.filter(membership_status=status)
        return queryset.distinct()
