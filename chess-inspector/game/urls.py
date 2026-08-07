from django.urls import path

from . import views

app_name = "game"
urlpatterns = [
    # Bare index (no game_id): lands on the most recently active game in
    # the shared lobby, or starts a new one if there isn't one yet. Kept
    # as its own pattern (rather than making game_id optional some other
    # way) so {% url 'game:index' %} with no args still works anywhere
    # that genuinely doesn't know/care which game it's linking to.
    path("", views.index, name="index"),
    path("new/", views.new_game, name="new_game"),
    path("<int:game_id>/", views.index, name="index"),
    path("<int:game_id>/probability/", views.probability, name="probability"),
    path("<int:game_id>/pgn/", views.pgn, name="pgn"),
    path("<int:game_id>/fen/", views.fen, name="fen"),
    path("<int:game_id>/clear/", views.clear_pgn, name="clear"),
    path("login/", views.login_page, name="login_page"),
]
