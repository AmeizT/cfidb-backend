from django.apps import AppConfig


class StrategyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.strategic'

    def ready(self):
        import apps.strategic.signals
