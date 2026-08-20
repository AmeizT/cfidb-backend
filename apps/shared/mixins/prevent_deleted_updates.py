from rest_framework.exceptions import ValidationError

class PreventDeletedUpdatesMixin:
    def perform_update(self, serializer):
        instance = serializer.instance

        if getattr(instance, "is_deleted", False):
            raise ValidationError(
                "Restore this record before editing it."
            )

        return super().perform_update(serializer) # type: ignore