from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .data import get_connected_sources


def _sources_list_context():
    sources = get_connected_sources()
    return {
        "sources": sources,
        "source_count": len(sources),
    }


@login_required
def sources_list(request):
    context = _sources_list_context()
    template = (
        "sources/partials/list_view.html"
        if request.headers.get("HX-Request")
        else "sources/list.html"
    )
    return render(request, template, context)
