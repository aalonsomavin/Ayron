from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from apps.agent.tools.document import preview_html_for_file as docx_preview_html_for_file
from apps.agent.tools.html_report import build_export_html, preview_html_for_file as html_preview_html_for_file
from apps.files.models import File
from apps.files.pdf import PdfGenerationError, html_to_pdf
from apps.files.services import (
    _file_kind,
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


def _preview_for_file(file_obj: File) -> str:
    if file_obj.format_key == "html":
        return html_preview_html_for_file(file_obj.content_json, file_obj.preview_html)
    return docx_preview_html_for_file(file_obj.content_json, file_obj.preview_html)


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

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    name = body.get("name", "")
    try:
        file_obj = rename_dashboard_file(file_obj, name)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

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
    return JsonResponse(payload)


@require_POST
def file_unsave(request, file_id):
    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    unsave_dashboard(request.user, file_id)
    payload = serialize_file_for_ui(file_obj, user=request.user)
    payload["saved"] = False
    return JsonResponse(payload)


@require_POST
def file_pin(request, file_id):
    import json

    file_obj = _get_user_file(request, file_id)
    if _file_kind(file_obj.content_json) != "dashboard":
        raise Http404("Dashboard not found")

    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    pinned = body.get("pinned", True)
    try:
        saved = set_dashboard_pinned(request.user, file_id, pinned)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    return JsonResponse(serialize_saved_dashboard(saved))


@login_required
def saved_dashboards_list(request):
    saved_qs = list_saved_dashboards(request.user)
    saved_items = [serialize_saved_dashboard(item) for item in saved_qs]
    pinned_items = [item for item in saved_items if item.get("pinned")]
    pinned_count = len(pinned_items)
    total_count = len(saved_items)
    if total_count == 1:
        count_label = "1 dashboard"
    else:
        count_label = f"{total_count} dashboards"
    if pinned_count == 1:
        count_label += " · 1 fijado"
    elif pinned_count > 1:
        count_label += f" · {pinned_count} fijados"

    return render(
        request,
        "dashboards/saved.html",
        {
            "saved_items": saved_items,
            "pinned_items": pinned_items,
            "count_label": count_label,
            "has_saved": total_count > 0,
        },
    )
