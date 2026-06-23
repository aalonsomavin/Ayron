from django.urls import path

from . import views

app_name = "dashboards"
urlpatterns = [
    path("saved/", views.saved_dashboards_list, name="saved_list"),
]
