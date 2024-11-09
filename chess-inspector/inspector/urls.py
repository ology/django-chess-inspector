from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path('', lambda req: redirect('/game/')),
    path('accounts/', include('django.contrib.auth.urls')),
    path("game/", include("game.urls")),
    path("admin/", admin.site.urls),
]
