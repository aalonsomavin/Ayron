from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.agent.tools.document import preview_html_for_file as docx_preview_html_for_file
from apps.agent.tools.html_report import build_export_html, preview_html_for_file as html_preview_html_for_file
from apps.files.models import File, SavedDashboard
from apps.files.pdf import PdfGenerationError, html_to_pdf
from apps.files.services import (
    _file_kind,
    is_dashboard_saved,
    list_saved_dashboards,
    open_file_stream,
    rename_dashboard_file,
    save_dashboard,
    serialize_file_for_ui,
    serialize_saved_dashboard,
    set_dashboard_pinned,
    unsave_dashboard,
)


def _get_user_file(request, file_id):
    return get_object_or_404(File, id=file_id, uploaded_by=request.user)


def _dashboard_detail_item(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    saved = SavedDashboard.objects.filter(user=request.user, file=file_obj).first()
    if saved:
        return serialize_saved_dashboard(saved)

    from apps.files.services import _relative_date_label, _user_display_name

    item = serialize_file_for_ui(file_obj, user=request.user)
    item["saved"] = False
    item["pinned"] = False
    author = file_obj.uploaded_by
    item["author"] = _user_display_name(author)
    item["date_label"] = _relative_date_label(file_obj.updated_at or file_obj.created_at)
    return item


def _is_htmx(request) -> bool:
    return request.headers.get("HX-Request") == "true"


def _saved_list_query(request) -> str:
    return (request.POST.get("q") or request.GET.get("q") or "").strip()


def _saved_list_context(request, query: str | None = None):
    q = _saved_list_query(request) if query is None else query.strip()
    saved_qs = list_saved_dashboards(request.user, query=q)
    saved_items = [serialize_saved_dashboard(item) for item in saved_qs]
    pinned_items = [] if q else [item for item in saved_items if item.get("pinned")]
    pinned_count = len([item for item in saved_items if item.get("pinned")])
    total_count = len(saved_items)
    if q:
        count_label = f"{total_count} resultado{'s' if total_count != 1 else ''}" if total_count else "Sin resultados"
        all_label = count_label if total_count else "Todos"
    elif total_count == 1:
        count_label = "1 dashboard"
        all_label = "Todos"
    else:
        count_label = f"{total_count} dashboards"
        all_label = "Todos"
    if not q:
        if pinned_count == 1:
            count_label += " · 1 fijado"
        elif pinned_count > 1:
            count_label += f" · {pinned_count} fijados"
    has_any_saved = SavedDashboard.objects.filter(user=request.user).exists()
    return {
        "saved_items": saved_items,
        "pinned_items": pinned_items,
        "count_label": count_label,
        "all_label": all_label,
        "query": q,
        "has_saved": has_any_saved,
        "chat_list_url": reverse("chat:list"),
        "new_dashboard_draft": "Genera un dashboard interactivo con los datos disponibles.",
    }


def _render_saved_partial(request, query: str | None = None):
    return render(request, "dashboards/partials/saved_view.html", _saved_list_context(request, query))


def _htmx_refresh_saved_list(request):
    if _is_htmx(request) and request.headers.get("HX-Target") == "dashboards-view":
        return _render_saved_partial(request)
    return None


def _preview_for_file(file_obj: File) -> str:
    if file_obj.format_key == "html":
        return html_preview_html_for_file(file_obj.content_json, file_obj.preview_html)
    return docx_preview_html_for_file(file_obj.content_json, file_obj.preview_html)


def _render_artifact_save_button(request, file_id, saved: bool):
    return render(
        request,
        "components/artifact_save_button.html",
        {"file_id": file_id, "saved": saved},
    )


def _htmx_artifact_save_response(request, file_id, saved: bool):
    if _is_htmx(request) and request.headers.get("HX-Target") == "artifact-save":
        return _render_artifact_save_button(request, file_id, saved)
    return None


def file_save_button(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")
    saved = is_dashboard_saved(request.user, file_id)
    return _render_artifact_save_button(request, file_id, saved)


def file_download(request, file_id):
    file_obj = _get_user_file(request, file_id)
    stream = open_file_stream(file_obj)
    response = FileResponse(
        stream,
        as_attachment=True,
        filename=file_obj.original_name,
        content_type=file_obj.mime_type,
    )
    return response


def file_download_pdf(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if file_obj.format_key != "html":
        raise Http404("PDF export is only available for HTML reports")

    export_html = build_export_html(file_obj.content_json)
    try:
        pdf_bytes = html_to_pdf(export_html)
    except PdfGenerationError as exc:
        return HttpResponse(str(exc), status=503)

    pdf_name = file_obj.original_name
    if pdf_name.lower().endswith(".html"):
        pdf_name = pdf_name[:-5] + ".pdf"
    elif not pdf_name.lower().endswith(".pdf"):
        pdf_name = f"{pdf_name}.pdf"

    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{pdf_name}"'
    return response


def file_preview(request, file_id):
    file_obj = _get_user_file(request, file_id)
    preview_html = _preview_for_file(file_obj)
    if not preview_html:
        raise Http404("Preview not available")
    return HttpResponse(preview_html, content_type="text/html; charset=utf-8")


@require_POST
def file_rename(request, file_id):
    import json

    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    if request.content_type == "application/json":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        name = body.get("name", "")
    else:
        name = request.POST.get("name", "")

    try:
        file_obj = rename_dashboard_file(file_obj, name)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    if _is_htmx(request):
        saved = SavedDashboard.objects.filter(user=request.user, file=file_obj).first()
        if saved:
            item = serialize_saved_dashboard(saved)
            return render(request, "dashboards/saved_card.html", {"item": item})

    return JsonResponse(serialize_file_for_ui(file_obj, user=request.user))


@require_POST
def file_save(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    try:
        save_dashboard(request.user, file_obj)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    payload = serialize_file_for_ui(file_obj, user=request.user)
    payload["saved"] = True
    artifact_response = _htmx_artifact_save_response(request, file_id, True)
    if artifact_response:
        return artifact_response
    return JsonResponse(payload)


@require_POST
def file_unsave(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    unsave_dashboard(request.user, file_id)
    refreshed = _htmx_refresh_saved_list(request)
    if refreshed:
        return refreshed
    artifact_response = _htmx_artifact_save_response(request, file_id, False)
    if artifact_response:
        return artifact_response

    payload = serialize_file_for_ui(file_obj, user=request.user)
    payload["saved"] = False
    return JsonResponse(payload)


@require_POST
def file_pin(request, file_id):
    import json

    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    if request.content_type == "application/json":
        try:
            body = json.loads(request.body or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        pinned = body.get("pinned", True)
    else:
        pinned = request.POST.get("pinned", "true").lower() == "true"

    try:
        saved = set_dashboard_pinned(request.user, file_id, pinned)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    item = serialize_saved_dashboard(saved)
    refreshed = _htmx_refresh_saved_list(request)
    if refreshed:
        return refreshed
    if _is_htmx(request):
        return render(request, "dashboards/partials/pin_button.html", {"item": item})

    return JsonResponse(item)


@login_required
def saved_dashboard_preview(request, file_id):
    item = _dashboard_detail_item(request, file_id)
    preview_html = _preview_for_file(_get_user_file(request, file_id))
    if not preview_html:
        raise Http404("Preview not available")
    return render(
        request,
        "dashboards/partials/preview.html",
        {"preview_html": preview_html, "title": item["name"]},
    )


@login_required
def saved_dashboard_detail(request, file_id):
    item = _dashboard_detail_item(request, file_id)
    template = (
        "dashboards/partials/detail_view.html"
        if _is_htmx(request)
        else "dashboards/detail.html"
    )
    return render(request, template, {"item": item})


@login_required
def saved_dashboards_list(request):
    context = _saved_list_context(request)
    template = (
        "dashboards/partials/saved_view.html"
        if _is_htmx(request)
        else "dashboards/saved.html"
    )
    return render(request, template, context)
