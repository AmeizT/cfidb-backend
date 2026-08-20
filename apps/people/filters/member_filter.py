import django_filters
from django.db.models import Q
from apps.people.models import Member

class MemberFilter(django_filters.FilterSet):
    fullname = django_filters.CharFilter(method="filter_fullname")
    first_name = django_filters.CharFilter(lookup_expr="iexact")
    last_name = django_filters.CharFilter(lookup_expr="iexact")
    member_key = django_filters.UUIDFilter()

    class Meta:
        model = Member
        fields = ["first_name", "last_name", "member_key"]

    def filter_fullname(self, queryset, name, value):
        """Filters members by full name or part of it (case insensitive)."""
        value = value.strip()
        parts = value.split()

        if len(parts) == 2:
            return queryset.filter(
                Q(first_name__icontains=parts[0]) & Q(last_name__icontains=parts[1])
            )
        else:
            # Search by either First Name or Last Name
            return queryset.filter(
                Q(first_name__icontains=value) | Q(last_name__icontains=value)
            )