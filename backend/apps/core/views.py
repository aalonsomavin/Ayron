from django.http import JsonResponse
from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def health(request):
    return JsonResponse({"status": "ok"})


def htmx_partial(request):
    count = int(request.POST.get("count", 0)) + 1
    return render(request, "core/partials/counter.html", {"count": count})
