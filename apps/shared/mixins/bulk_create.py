from rest_framework.response import Response

class BulkCreateMixin:

    def create(self, request, *args, **kwargs):
        is_many = isinstance(request.data, list)

        serializer = self.get_serializer(data=request.data, many=is_many) # type: ignore
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer) # type: ignore

        return Response(serializer.data, status=201)