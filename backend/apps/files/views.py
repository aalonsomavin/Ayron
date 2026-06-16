from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from apps.agent.tools.document import preview_html_for_file as docx_preview_html_for_file
from apps.agent.tools.html_report import build_export_html, preview_html_for_file as html_preview_html_for_file
from apps.files.models import File
from apps.files.pdf import PdfGenerationError, html_to_pdf
from apps.files.services import open_file_stream


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
