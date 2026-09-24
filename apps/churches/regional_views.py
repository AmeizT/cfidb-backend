from rest_framework import filters, generics
from apps.churches.services.regional_scope import scope_regional_queryset

from apps.churches.permissions import IsRegionalStaff
from apps.churches.regional_serializers import (
    RegionalChurchSerializer,
    RegionalUserSerializer,
)
from apps.churches.schemas import (
    get_regional_churches_table_schema,
    get_regional_directory_table_schemas,
    get_regional_users_table_schema,
)
from apps.churches.services import (
    get_regional_churches_queryset,
    get_regional_users_queryset,
)
from apps.shared.pagination import DataTablePagination


class RegionalTableSchemaMixin:
    def get_table_schema(self):
        raise NotImplementedError

    def get_table_schemas(self):
        return get_regional_directory_table_schemas(self.request.user)

    def add_table_schema(self, response):
        table_schema = self.get_table_schema()
        response.data["table_schema"] = table_schema
        response.data["table_schemas"] = self.get_table_schemas()
        return response

    def get_paginated_response(self, data):
        response = super().get_paginated_response(data)
        return self.add_table_schema(response)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        if "table_schema" not in response.data:
            self.add_table_schema(response)

        return response


class RegionalChurchesView(RegionalTableSchemaMixin, generics.ListAPIView):
    serializer_class = RegionalChurchSerializer
    permission_classes = [IsRegionalStaff]
    pagination_class = DataTablePagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "name",
        "code",
        "city",
        "province",
        "country",
        "country_code",
        "zone__name",
    ]
    ordering_fields = [
        "name",
        "code",
        "city",
        "province",
        "country",
        "country_code",
        "status",
        "created_at",
        "updated_at",
        "zone__name",
    ]
    ordering = ["name"]

    def get_queryset(self):
        return scope_regional_queryset(get_regional_churches_queryset(self.request.user), self.request.user)

    def get_table_schema(self):
        return get_regional_churches_table_schema(self.request.user)


class RegionalUsersView(RegionalTableSchemaMixin, generics.ListAPIView):
    serializer_class = RegionalUserSerializer
    permission_classes = [IsRegionalStaff]
    pagination_class = DataTablePagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = [
        "first_name",
        "last_name",
        "email",
        "church__name",
    ]
    ordering_fields = [
        "first_name",
        "last_name",
        "email",
        "created_at",
        "updated_at",
        "last_active",
        "church__name",
        "church__country",
        "church__zone__name",
    ]
    ordering = ["last_name", "first_name"]

    def get_queryset(self):
        return scope_regional_queryset(get_regional_users_queryset(self.request.user), self.request.user, "church__zone_id")

    def get_table_schema(self):
        return get_regional_users_table_schema(self.request.user)
