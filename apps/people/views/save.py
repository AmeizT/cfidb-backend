# def perform_destroy(self, instance):
#         with transaction.atomic():
#             old_data = getattr(instance, "_capture_old_data", lambda: None)()
#             instance.is_deleted = True
#             instance.save()
#             description = (
#                 f"{instance.service_type} service soft deleted | "
#                 f"Headcount: {instance.headcount} | "
#                 f"New Converts: {instance.new_converts}"
#             )
#             instance.log_audit(user=self.request.user, action=AuditLog.Action.DELETE, old_data=old_data, description=description)

#     @action(detail=True, methods=['post'], url_path='restore')
#     def restore(self, request, pk=None):
#         instance = self.get_object()
#         with transaction.atomic():
#             old_data = getattr(instance, "_capture_old_data", lambda: None)()
#             instance.is_deleted = False
#             instance.save()
#             description = (
#                 f"{instance.service_type} service restored | "
#                 f"Headcount: {instance.headcount} | "
#                 f"New Converts: {instance.new_converts}"
#             )
#             instance.log_audit(user=self.request.user, action=AuditLog.Action.RESTORE, old_data=old_data, description=description)
#         serializer = self.get_serializer(instance)
#         return Response(serializer.data, status=status.HTTP_200_OK)

#     @action(detail=False, methods=['post'], url_path='bulk-delete')
#     def bulk_delete(self, request):
#         ids = request.data.get('ids', [])
#         if not isinstance(ids, list) or not ids:
#             return Response({"detail": "IDs must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)
#         with transaction.atomic():
#             instances = Attendance.objects.filter(id__in=ids)
#             for instance in instances:
#                 old_data = getattr(instance, "_capture_old_data", lambda: None)()
#                 instance.is_deleted = True
#                 instance.save()
#                 description = (
#                     f"{instance.service_type} service soft deleted | "
#                     f"Headcount: {instance.headcount} | "
#                     f"New Converts: {instance.new_converts}"
#                 )
#                 instance.log_audit(user=self.request.user, action=AuditLog.Action.DELETE, old_data=old_data, description=description)
#         return Response({"detail": f"{instances.count()} attendances soft deleted."}, status=status.HTTP_200_OK)

#     @action(detail=False, methods=['post'], url_path='bulk-restore')
#     def bulk_restore(self, request):
#         ids = request.data.get('ids', [])
#         if not isinstance(ids, list) or not ids:
#             return Response({"detail": "IDs must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)
#         with transaction.atomic():
#             instances = Attendance.objects.filter(id__in=ids)
#             for instance in instances:
#                 old_data = getattr(instance, "_capture_old_data", lambda: None)()
#                 instance.is_deleted = False
#                 instance.save()
#                 description = (
#                     f"{instance.service_type} service restored | "
#                     f"Headcount: {instance.headcount} | "
#                     f"New Converts: {instance.new_converts}"
#                 )
#                 instance.log_audit(user=self.request.user, action=AuditLog.Action.RESTORE, old_data=old_data, description=description)
#         return Response({"detail": f"{instances.count()} attendances restored."}, status=status.HTTP_200_OK)