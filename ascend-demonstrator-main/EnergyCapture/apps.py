from django.apps import AppConfig


class EnergyCaptureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'EnergyCapture'

    def ready(self):
        from . import signals