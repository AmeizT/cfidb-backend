from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.shared.pagination import DataTablePagination
from apps.people.models import AssemblyMembership, MemberTransferRequest
from apps.people.permissions import (
    can_view_transfer,
    filter_membership_queryset_for_user,
    filter_transfer_queryset_for_user,
)
from apps.people.serializers.transfers import (
    AssemblyMembershipSerializer,
    MemberTransferAcceptSerializer,
    MemberTransferCancelSerializer,
    MemberTransferRejectSerializer,
    MemberTransferRequestCreateSerializer,
    MemberTransferRequestDetailSerializer,
    MemberTransferRequestListSerializer,
)
from apps.people.services.member_transfer_service import (
    accept_transfer_request,
    cancel_transfer_request,
    create_transfer_request,
    reject_transfer_request,
)
from apps.people.schemas import PeopleTableSchemaMixin


class MemberTransferRequestViewSet(PeopleTableSchemaMixin, viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = DataTablePagination
    queryset = MemberTransferRequest.objects.all()
    table_schema_name = "transfers"
    closed_statuses = [
        MemberTransferRequest.Status.COMPLETED,
        MemberTransferRequest.Status.REJECTED,
        MemberTransferRequest.Status.CANCELLED,
    ]
    open_statuses = [
        MemberTransferRequest.Status.PENDING,
        MemberTransferRequest.Status.ACCEPTED,
    ]

    def get_serializer_class(self):
        if self.action == "create":
            return MemberTransferRequestCreateSerializer
        if self.action == "accept":
            return MemberTransferAcceptSerializer
        if self.action == "reject":
            return MemberTransferRejectSerializer
        if self.action == "cancel":
            return MemberTransferCancelSerializer
        if self.action == "list" or self.action in {"incoming", "outgoing", "history"}:
            return MemberTransferRequestListSerializer
        return MemberTransferRequestDetailSerializer

    def get_queryset(self):
        queryset = MemberTransferRequest.objects.select_related(
            "member",
            "member__assembly",
            "from_assembly",
            "from_assembly__zone",
            "from_assembly__zone__region",
            "to_assembly",
            "to_assembly__zone",
            "to_assembly__zone__region",
            "requested_by",
            "reviewed_by",
            "completed_by",
        ).prefetch_related("assembly_membership_changes")

        queryset = filter_transfer_queryset_for_user(queryset, self.request.user)

        status_filter = self.request.query_params.get("status")
        member_filter = self.request.query_params.get("member")

        if status_filter:
            statuses = [value.strip() for value in status_filter.split(",") if value.strip()]
            queryset = queryset.filter(status__in=statuses)

        if member_filter:
            queryset = queryset.filter(member_id=member_filter)

        search = self.request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(member__first_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__member_key__icontains=search)
            )

        view = self.request.query_params.get("view")
        if view == "incoming":
            queryset = filter_transfer_queryset_for_user(queryset, self.request.user, direction="incoming")
            queryset = queryset.filter(status__in=self.open_statuses)
        elif view == "outgoing":
            queryset = filter_transfer_queryset_for_user(queryset, self.request.user, direction="outgoing")
            queryset = queryset.filter(status__in=self.open_statuses)
        elif view == "history":
            queryset = queryset.filter(status__in=self.closed_statuses)

        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer = create_transfer_request(
            requested_by=request.user,
            **serializer.validated_data,
        )
        response_serializer = MemberTransferRequestDetailSerializer(
            transfer,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        transfer = self.get_object()
        if not can_view_transfer(request.user, transfer):
            self.permission_denied(request)

        serializer = self.get_serializer(transfer)
        return Response(serializer.data)

    def _list_response(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MemberTransferRequestListSerializer(
                page,
                many=True,
                context=self.get_serializer_context(),
            )
            return self.get_paginated_response(serializer.data)

        serializer = MemberTransferRequestListSerializer(
            queryset,
            many=True,
            context=self.get_serializer_context(),
        )
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def incoming(self, request):
        queryset = filter_transfer_queryset_for_user(
            self.get_queryset(),
            request.user,
            direction="incoming",
        )

        queryset = queryset.filter(status__in=self.open_statuses)

        return self._list_response(queryset)

    @action(detail=False, methods=["get"])
    def outgoing(self, request):
        queryset = filter_transfer_queryset_for_user(
            self.get_queryset(),
            request.user,
            direction="outgoing",
        )

        queryset = queryset.filter(status__in=self.open_statuses)

        return self._list_response(queryset)

    @action(detail=False, methods=["get"])
    def history(self, request):
        queryset = self.get_queryset().filter(
            status__in=self.closed_statuses
        )
        return self._list_response(queryset)

    @action(detail=True, methods=["post"])
    def accept(self, request, pk=None):
        transfer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer = accept_transfer_request(
            transfer=transfer,
            reviewed_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        response_serializer = MemberTransferRequestDetailSerializer(
            transfer,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        transfer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer = reject_transfer_request(
            transfer=transfer,
            reviewed_by=request.user,
            rejection_reason=serializer.validated_data["rejection_reason"],
            notes=serializer.validated_data.get("notes", ""),
        )
        response_serializer = MemberTransferRequestDetailSerializer(
            transfer,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        transfer = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        transfer = cancel_transfer_request(
            transfer=transfer,
            cancelled_by=request.user,
            notes=serializer.validated_data.get("notes", ""),
        )
        response_serializer = MemberTransferRequestDetailSerializer(
            transfer,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data)


class AssemblyMembershipViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = AssemblyMembershipSerializer
    pagination_class = DataTablePagination

    def get_queryset(self):
        queryset = AssemblyMembership.objects.select_related(
            "member",
            "assembly",
            "assembly__zone",
            "assembly__zone__region",
            "created_by",
            "updated_by",
            "transfer",
        )
        queryset = filter_membership_queryset_for_user(queryset, self.request.user)

        member_filter = self.request.query_params.get("member")
        if member_filter:
            queryset = queryset.filter(member_id=member_filter)

        filters = {
            "status": "status",
            "assembly": "assembly_id",
            "end_reason": "end_reason",
            "joined_from": "joined_on__gte",
            "joined_to": "joined_on__lte",
            "ended_from": "ended_on__gte",
            "ended_to": "ended_on__lte",
        }
        for parameter, field in filters.items():
            value = self.request.query_params.get(parameter)
            if value:
                queryset = queryset.filter(**{field: value})

        search = self.request.query_params.get("search", "").strip()
        if search:
            from django.db.models import Q

            queryset = queryset.filter(
                Q(member__first_name__icontains=search)
                | Q(member__last_name__icontains=search)
                | Q(member__member_key__icontains=search)
            )

        return queryset
