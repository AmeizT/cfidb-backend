import django_filters

class SoftDeleteFilterSet(django_filters.FilterSet):
    is_deleted = django_filters.BooleanFilter()