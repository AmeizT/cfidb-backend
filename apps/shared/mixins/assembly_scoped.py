class AssemblyScopedQueryMixin:
    def get_queryset(self):
        queryset = super().get_queryset() # type: ignore

        user = getattr(self.request, "user", None) # type: ignore

        if getattr(user, "church", None):
            queryset = queryset.filter(
                assembly=user.church # type: ignore
            )

        return queryset
    

