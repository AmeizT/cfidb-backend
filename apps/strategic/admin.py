from django.contrib import admin
from apps.strategic.models import Strategy, StrategyLegacy

admin.site.register(Strategy)
admin.site.register(StrategyLegacy)
