from django.db import transaction
from apps.reports.models import AuditLog
from rest_framework.request import Request
from apps.people.mixins.base import ViewSetMixinBase

class AuditMixin:
    def perform_create(self, serializer):
        with transaction.atomic():
            instances = serializer.save()
            if not isinstance(instances, list):
                instances = [instances]

            for instance in instances:
                was_created = serializer.context.get("was_created", True)
                old_data = getattr(instance, "_capture_old_data", lambda: None)()

                action = AuditLog.Action.CREATE if was_created else AuditLog.Action.UPDATE

                description = (
                    f"{instance.service_type} service | "
                    f"Headcount: {instance.headcount} | "
                    f"New Converts: {instance.total_new_converts}"
                )

                instance.log_audit(
                    user=self.request.user, # type: ignore
                    action=action,
                    old_data=old_data,
                    description=description
                )

    def perform_update(self, serializer):
        instance = serializer.instance
        old_data = getattr(instance, "_capture_old_data", lambda: None)()

        updated_instance = serializer.save()

        description = (
            f"{updated_instance.service_type} service updated | "
            f"Headcount: {updated_instance.headcount} | "
            f"New Converts: {updated_instance.total_new_converts}"
        )

        updated_instance.log_audit(
            user=self.request.user, # type: ignore
            action=AuditLog.Action.UPDATE,
            old_data=old_data,
            description=description
        )
