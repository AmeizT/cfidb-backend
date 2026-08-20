import json
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.forms.models import model_to_dict
from apps.reports.models.audit import AuditLog


class AuditLogMixin:
    """
    Generic audit logging for any model.
    Ensures JSON-serializable `new_data` for Decimal, datetime, FileFields, ForeignKeys.
    """

    def log_audit(self, user=None, action=None, old_data=None, description=None):
        if not action:
            raise ValueError("Audit action must be explicitly provided.")

        # Skip anonymous users
        if not user or getattr(user, "is_anonymous", True):
            return

        if not description:
            model_name = self.__class__.__name__
            desc_action = str(action).capitalize()
            description = f"{desc_action} performed on {model_name} (ID: {self.pk})"

        new_data_json = self._serialize_instance()

        AuditLog.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(self.__class__),
            object_id=self.pk,
            action=action,
            old_data=old_data,
            new_data=new_data_json,
            description=description
        )

    def _serialize_instance(self):
        """
        JSON-safe serialization of the model:
        - FileFields -> file name
        - ForeignKeys -> PK
        - All others -> as-is (Decimal, datetime handled by DjangoJSONEncoder)
        """
        data = {}
        for field in self._meta.fields:
            value = getattr(self, field.name)

            if isinstance(field, models.FileField):
                data[field.name] = value.name if value else None
            elif isinstance(field, models.ForeignKey):
                data[field.name] = value.pk if value else None
            else:
                data[field.name] = value

        return json.loads(json.dumps(data, cls=DjangoJSONEncoder))

    def _capture_old_data(self):
        """
        Returns previous instance state (JSON-safe) or None if new.
        """
        if not self.pk:
            return None
        try:
            old_instance = self.__class__.objects.get(pk=self.pk)
            return old_instance._serialize_instance()
        except self.__class__.DoesNotExist:
            return None



# import json
# from django.contrib.contenttypes.models import ContentType
# from django.core.serializers.json import DjangoJSONEncoder
# from django.db import models
# from apps.reports.models import AuditLog

# class AuditLogMixin:

#     def _serialize_instance(self, instance):
#         """
#         Convert model instance into JSON-safe dictionary.
#         """

#         data = {}

#         for field in instance._meta.fields:
#             value = getattr(instance, field.name)

#             if isinstance(field, models.FileField):
#                 data[field.name] = value.name if value else None

#             elif isinstance(field, models.ForeignKey):
#                 data[field.name] = value.pk if value else None

#             else:
#                 data[field.name] = value

#         return json.loads(json.dumps(data, cls=DjangoJSONEncoder))

#     def _capture_old_data(self):
#         if not self.pk:
#             return None

#         try:
#             old_instance = self.__class__.objects.get(pk=self.pk)
#             return self._serialize_instance(old_instance)
#         except self.__class__.DoesNotExist:
#             return None

#     def log_audit(self, user=None, action=None, old_data=None):
#         if action is None:
#             raise ValueError("Audit action must be explicitly provided.")

#         AuditLog.objects.create(
#             user=user,
#             content_type=ContentType.objects.get_for_model(self.__class__),
#             object_id=self.pk,
#             action=action,
#             old_data=old_data,
#             new_data=self._serialize_instance(self),
#         )



