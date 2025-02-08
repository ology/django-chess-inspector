from django.urls import path

from . import views

app_name = "game"
urlpatterns = [
    path("", views.index, name="index"),
    path("pgn/", views.pgn, name="pgn"),
    path("fen/", views.fen, name="fen"),
    path("clear/", views.clear_pgn, name="clear"),
    path("login/", views.login_page, name="login_page"),
]