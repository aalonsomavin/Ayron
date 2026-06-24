from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .data import get_connected_sources


def _sources_list_context():
    sources = get_connected_sources()
    stats = {
        "total": len(sources),
        "connected": sum(1 for s in sources if s["status"] == "connected"),
        "syncing": sum(1 for s in sources if s["status"] == "syncing"),
        "error": sum(1 for s in sources if s["status"] == "error"),
    }
    return {
        "sources": sources,
        "stats": stats,
        "stat_chips": [
            {"tone": "neutral", "label": f"{stats['total']} fuentes"},
            {"tone": "success", "label": f"{stats['connected']} conectadas"},
            {"tone": "warning", "label": f"{stats['syncing']} sincronizando"},
            {"tone": "danger", "label": f"{stats['error']} con error"},
        ],
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
