from django.urls import path

from . import views

app_name = "core"
urlpatterns = [
    path("", views.home, name="home"),
    path("health", views.health, name="health"),
    path("htmx/counter/", views.htmx_partial, name="htmx_counter"),
]
