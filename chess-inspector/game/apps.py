from django.apps import AppConfig

class GameConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'game'

def ready(self):
    from .views import ctrl
    ctrl.load_state()
