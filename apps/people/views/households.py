from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch, Q
from django.utils.dateparse import parse_date
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from apps.people.models import FormerMember, Household, HouseholdMember, MembershipEndReason
from apps.people.permissions import can_access_assembly, filter_membership_queryset_for_user
from apps.people.serializers.households import (
    FormerMemberReadmitSerializer,
    FormerMemberDetailSerializer,
    FormerMemberSerializer,
    HouseholdMemberSerializer,
    HouseholdDetailSerializer,
    HouseholdSerializer,
)
from apps.shared.pagination import DataTablePagination
from apps.people.schemas import PeopleTableSchemaMixin


def _scope_households(queryset, user, field="assembly"):
    from apps.people.permissions import get_user_transfer_assembly_ids, get_user_transfer_region_ids, is_global_transfer_admin

    if is_global_transfer_admin(user):
        return queryset
    assembly_ids = get_user_transfer_assembly_ids(user)
    region_ids = get_user_transfer_region_ids(user)
    query = Q(**{f"{field}_id__in": assembly_ids}) if assembly_ids else Q(pk__in=[])
    if region_ids:
        query |= Q(**{f"{field}__zone__region_id__in": region_ids})
    return queryset.filter(query).distinct()


class FormerMemberViewSet(PeopleTableSchemaMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DataTablePagination
    serializer_class = FormerMemberSerializer
    table_schema_name = "former_members"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return FormerMemberDetailSerializer
        return FormerMemberSerializer

    def get_queryset(self):
        queryset = filter_membership_queryset_for_user(FormerMember.objects.all(), self.request.user)
        reason = self.request.query_params.get("reason")
        if reason and reason != "all":
            queryset = queryset.filter(end_reason=reason)
        for parameter, field in (("ended_from", "ended_on__gte"), ("ended_to", "ended_on__lte")):
            value = self.request.query_params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(member__first_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__member_key__icontains=search)
            )
        return queryset

    @action(detail=True, methods=["post"])
    def readmit(self, request, pk=None):
        former = self.get_object()
        serializer = FormerMemberReadmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assembly = serializer.validated_data.get("assembly", former.assembly)
        if not can_access_assembly(request.user, assembly):
            raise PermissionDenied("You cannot readmit members into this assembly.")
        try:
            membership = former.readmit(created_by=request.user, **serializer.validated_data)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        from apps.people.serializers.transfers import AssemblyMembershipSerializer
        return Response(AssemblyMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class HouseholdViewSet(PeopleTableSchemaMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DataTablePagination
    serializer_class = HouseholdSerializer
    table_schema_name = "households"

    def get_serializer_class(self):
        if self.action == "retrieve":
            return HouseholdDetailSerializer
        return HouseholdSerializer

    def get_queryset(self):
        queryset = (
            Household.objects.with_member_counts()
            .select_related("assembly")
            .prefetch_related(Prefetch(
                "household_memberships",
                queryset=HouseholdMember.objects.filter(member__is_trash=False).select_related("member"),
            ))
            .order_by("name", "pk")
        )
        queryset = _scope_households(queryset, self.request.user)
        assembly = self.request.query_params.get("assembly")
        status_value = self.request.query_params.get("status")
        search = self.request.query_params.get("search", "").strip()
        if assembly:
            queryset = queryset.filter(assembly_id=assembly)
        if status_value:
            queryset = queryset.filter(status=status_value)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(phone_number__icontains=search)
                | Q(email__icontains=search)
                | Q(address__icontains=search)
                | Q(city__icontains=search)
            )
        return queryset

    @action(detail=False, methods=["get"], url_path="transfer-options")
    def transfer_options(self, request):
        from apps.churches.models import Church
        return Response([
            {"id": assembly.pk, "name": assembly.name}
            for assembly in Church.objects.select_related("zone").all()
            if can_access_assembly(request.user, assembly)
        ])

    def perform_create(self, serializer):
        from apps.people.create_security import active_create_assembly
        if self.request.headers.get("X-Assembly-ID") is not None:
            active = active_create_assembly(self.request)
            if serializer.validated_data.get("assembly", active) != active:
                raise PermissionDenied("The requested assembly does not match the active workspace.")
        assembly = serializer.validated_data.get("assembly") or getattr(self.request.user, "church", None)
        if assembly is None or not can_access_assembly(self.request.user, assembly):
            raise PermissionDenied("You cannot create a household for this assembly.")
        serializer.save(assembly=assembly)

    @action(detail=True, methods=["post"], url_path="add-member")
    def add_member(self, request, pk=None):
        household = self.get_object()
        data = request.data.copy()
        data["household"] = household.pk
        serializer = HouseholdMemberSerializer(data=data, context=self.get_serializer_context())
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()
        return Response(HouseholdMemberSerializer(membership).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        household = self.get_object()
        try:
            household.close(updated_by=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        return Response(self.get_serializer(household).data)


class HouseholdMemberViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DataTablePagination
    serializer_class = HouseholdMemberSerializer

    def get_queryset(self):
        queryset = HouseholdMember.objects.filter(member__is_trash=False).select_related(
            "household", "household__assembly", "member"
        )
        return _scope_households(queryset, self.request.user, field="household__assembly")

    def perform_create(self, serializer):
        household = serializer.validated_data["household"]
        if not can_access_assembly(self.request.user, household.assembly):
            raise PermissionDenied("You cannot modify this household.")
        serializer.save()

    @action(detail=True, methods=["post"])
    def leave(self, request, pk=None):
        membership = self.get_object()
        try:
            membership.leave(
                left_on=parse_date(request.data["left_on"]) if request.data.get("left_on") else None,
                notes=request.data.get("notes"),
                updated_by=request.user,
            )
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict) from exc
        return Response(self.get_serializer(membership).data)

    @action(detail=True, methods=["post"], url_path="make-primary")
    def make_primary(self, request, pk=None):
        membership = self.get_object()
        try:
            membership.make_primary_contact(updated_by=request.user)
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages) from exc
        return Response(self.get_serializer(membership).data)
