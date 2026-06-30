from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from apps.provenance.models import DataAccess
from apps.provenance.permissions import (
    get_user_claim,
    get_user_conversation,
    get_user_data_access,
    get_user_file_claim,
)
from apps.provenance.serializers import serialize_claim_detail, serialize_data_access
from apps.provenance.services import resolve_claim_provenance_detail


@login_required
@require_GET
def data_access_detail(request, data_access_id):
    data_access = get_user_data_access(request, data_access_id)
    return JsonResponse(serialize_data_access(data_access))


@login_required
@require_GET
def conversation_data_access_lookup(request, conversation_id):
    conversation = get_user_conversation(request, conversation_id)
    tool_call_id = (request.GET.get("tool_call_id") or "").strip()
    if not tool_call_id:
        return HttpResponseBadRequest("tool_call_id is required.")

    data_access = get_object_or_404(
        DataAccess.objects.select_related("integration"),
        conversation=conversation,
        tool_call_id=tool_call_id,
    )
    return JsonResponse(serialize_data_access(data_access))


@login_required
@require_GET
def claim_detail(request, claim_id):
    claim = get_user_claim(request, claim_id)
    accept = request.headers.get("Accept", "")
    wants_html = "text/html" in accept and "application/json" not in accept

    if wants_html:
        detail = resolve_claim_provenance_detail(claim)
        if detail is None:
            raise Http404
        return render(
            request,
            "components/provenance_sql_detail.html",
            {"detail": detail},
        )

    return JsonResponse(serialize_claim_detail(claim))


@login_required
@require_GET
def file_claim_detail(request, file_id, claim_key):
    claim = get_user_file_claim(request, file_id, claim_key)
    return JsonResponse(serialize_claim_detail(claim))
