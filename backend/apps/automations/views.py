from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .data import get_automations


def _automations_list_context():
    automations = get_automations()
    stats = {
        "total": len(automations),
        "active": sum(1 for a in automations if a["is_active"]),
    }
    return {
        "automations": automations,
        "stats": stats,
        "stat_chips": [
            {"tone": "neutral", "label": f"{stats['total']} automatizaciones"},
            {"tone": "success", "label": f"{stats['active']} activas"},
        ],
    }


@login_required
def automations_list(request):
    context = _automations_list_context()
    template = (
        "automations/partials/list_view.html"
        if request.headers.get("HX-Request")
        else "automations/list.html"
    )
    return render(request, template, context)
