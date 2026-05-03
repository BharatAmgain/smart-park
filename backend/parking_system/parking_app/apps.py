from django.apps import AppConfig


class ParkingAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parking_app'

    def ready(self):
        # Initialize on startup - without threading
        pass