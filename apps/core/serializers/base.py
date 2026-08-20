from django.urls import reverse
from rest_framework import serializers


class HyperlinkedModelSerializer(serializers.ModelSerializer):
    """
    Base serializer that generates:
    - url: self-detail URL
    - links: related object URLs
    - actions: edit/delete/bulk-delete URLs
    - collection_actions: bulk delete/restore URLs
    Permissions are omitted since authenticated users have full access.
    """
    url = serializers.SerializerMethodField()
    links = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    collection_actions = serializers.SerializerMethodField()

    def _build_url(self, app_name, basename, action="detail", args=None, query=None):
        if not basename:
            return None

        view_name = f"{app_name}:{basename}-{action}" if app_name else f"{basename}-{action}"
        url = reverse(view_name, args=args or [])

        if query:
            params = "&".join([f"{k}={v}" for k, v in query.items()])
            url = f"{url}?{params}"

        return url

    def get_url(self, obj):
        cls = type(self)
        return self._build_url(
            getattr(cls, "app_name", None),
            getattr(cls, "basename", None),
            "detail",
            [obj.id],
        )

    def get_links(self, obj):
        links = {}
        for key, config in getattr(self, "related_routes", {}).items():
            app_name = config.get("app_name")
            basename = config.get("basename")
            lookup = config.get("lookup", "id")
            many = config.get("many", False)

            value = getattr(obj, lookup, None)
            if value is None:
                continue

            if many:
                links[key] = self._build_url(
                    app_name,
                    basename,
                    "list",
                    query={lookup.replace("_id", ""): value},
                )
            else:
                links[key] = self._build_url(app_name, basename, "detail", [value])

        return links

    def get_actions(self, obj):
        cls = type(self)
        app_name = getattr(cls, "app_name", None)
        basename = getattr(cls, "basename", None)

        return {
            "edit": self._build_url(app_name, basename, "detail", [obj.id]),
            "delete": self._build_url(app_name, basename, "detail", [obj.id]),
            "bulk_delete": self._build_url(app_name, basename, "bulk-delete"),
        }

    def get_collection_actions(self, obj):
        cls = type(self)
        app_name = getattr(cls, "app_name", None)
        basename = getattr(cls, "basename", None)

        return {
            "bulk_delete": self._build_url(app_name, basename, "bulk-delete"),
            "bulk_restore": self._build_url(app_name, basename, "bulk-restore"),
        }

    class Meta:
        abstract = True