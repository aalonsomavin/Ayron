from django.urls import path

from . import views

app_name = "automations"
urlpatterns = [
    path("", views.automations_list, name="list"),
]
