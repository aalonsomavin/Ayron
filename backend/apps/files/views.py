from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404

from apps.agent.tools.document import preview_html_for_file
from apps.files.models import File
from apps.files.services import open_file_stream


def _get_user_file(request, file_id):
    return get_object_or_404(File, id=file_id, uploaded_by=request.user)


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


def file_preview(request, file_id):
    file_obj = _get_user_file(request, file_id)
    preview_html = preview_html_for_file(file_obj.content_json, file_obj.preview_html)
    if not preview_html:
        raise Http404("Preview not available")
    return HttpResponse(preview_html, content_type="text/html; charset=utf-8")
