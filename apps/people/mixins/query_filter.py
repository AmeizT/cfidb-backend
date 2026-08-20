class ChurchScopedQueryMixin:
    def get_queryset(self):
        queryset = super().get_queryset()

        user = getattr(self.request, "user", None)

        if getattr(user, "church", None):
            queryset = queryset.filter(
                assembly=user.church
            )

        return queryset