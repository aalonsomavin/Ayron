from django.urls import path

from apps.provenance import views

app_name = "provenance"

urlpatterns = [
    path(
        "data-access/<uuid:data_access_id>/",
        views.data_access_detail,
        name="data_access_detail",
    ),
    path(
        "conversations/<uuid:conversation_id>/data-access/",
        views.conversation_data_access_lookup,
        name="conversation_data_access_lookup",
    ),
    path(
        "claims/<uuid:claim_id>/",
        views.claim_detail,
        name="claim_detail",
    ),
    path(
        "files/<uuid:file_id>/claims/<slug:claim_key>/",
        views.file_claim_detail,
        name="file_claim_detail",
    ),
]
