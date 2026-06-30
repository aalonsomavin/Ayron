from django.urls import path

from . import views

app_name = "chat"
urlpatterns = [
    path("", views.conversation_list, name="list"),
    path("new/", views.conversation_new, name="new"),
    path("start/", views.conversation_start, name="start"),
    path("draft/", views.conversation_draft, name="draft"),
    path("upload/", views.upload_staging_file, name="upload_staging"),
    path("upload/<uuid:file_id>/discard/", views.discard_staging_file, name="discard_staging"),
    path("<uuid:conversation_id>/provenance/data-access/", views.provenance_data_access, name="provenance_data_access"),
    path("<uuid:conversation_id>/", views.conversation_detail, name="detail"),
    path("<uuid:conversation_id>/send/", views.send_message, name="send"),
    path("<uuid:conversation_id>/upload/", views.upload_file, name="upload"),
    path("<uuid:conversation_id>/stop/", views.stop_conversation, name="stop"),
    path("<uuid:conversation_id>/retry/", views.retry_message, name="retry"),
    path("<uuid:conversation_id>/events/", views.events_replay, name="events"),
    path("<uuid:conversation_id>/clarification/wizard/", views.clarification_wizard, name="clarification_wizard"),
    path("<uuid:conversation_id>/clarification/step/", views.clarification_step, name="clarification_step"),
    path("<uuid:conversation_id>/clarification/submit/", views.clarification_submit, name="clarification_submit"),
    path("<uuid:conversation_id>/stream/", views.event_stream, name="stream"),
    path("<uuid:conversation_id>/rename/", views.conversation_rename, name="rename"),
    path("<uuid:conversation_id>/delete/", views.conversation_delete, name="delete"),
]
