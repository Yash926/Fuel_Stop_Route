from django.urls import path
from . import views

urlpatterns = [
    path("", views.frontend, name="index"),
    path("route/", views.route_view, name="route"),
]
