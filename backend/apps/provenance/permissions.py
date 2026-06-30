from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404

from apps.chat.models import Conversation
from apps.files.models import File
from apps.provenance.models import DataAccess, DataClaim


def get_user_conversation(request, conversation_id):
    return get_object_or_404(Conversation, id=conversation_id, user=request.user)


def get_accessible_file(request, file_id):
    return get_object_or_404(
        File.objects.filter(
            Q(uploaded_by=request.user) | Q(conversation__user=request.user)
        ),
        id=file_id,
    )


def get_user_data_access(request, data_access_id):
    return get_object_or_404(
        DataAccess.objects.select_related("conversation", "integration"),
        id=data_access_id,
        conversation__user=request.user,
    )


def get_user_claim(request, claim_id):
    return get_object_or_404(
        DataClaim.objects.select_related("conversation", "artifact_file"),
        id=claim_id,
        conversation__user=request.user,
    )


def get_user_file_claim(request, file_id, claim_key):
    file_obj = get_accessible_file(request, file_id)
    claim = (
        DataClaim.objects.filter(
            artifact_file=file_obj,
            claim_key=claim_key,
            conversation__user=request.user,
        )
        .select_related("conversation", "artifact_file")
        .first()
    )
    if claim is None:
        raise Http404
    return claim
