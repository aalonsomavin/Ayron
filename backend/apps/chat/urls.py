from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.conversation_list, name="list"),
    path("new/", views.conversation_new, name="new"),
    path("start/", views.conversation_start, name="start"),
    path("<uuid:conversation_id>/", views.conversation_detail, name="detail"),
    path("<uuid:conversation_id>/send/", views.send_message, name="send"),
    path("<uuid:conversation_id>/stop/", views.stop_conversation, name="stop"),
    path("<uuid:conversation_id>/retry/", views.retry_message, name="retry"),
    path("<uuid:conversation_id>/events/", views.events_replay, name="events"),
    path("<uuid:conversation_id>/stream/", views.event_stream, name="stream"),
    path("<uuid:conversation_id>/rename/", views.conversation_rename, name="rename"),
    path("<uuid:conversation_id>/delete/", views.conversation_delete, name="delete"),
]
