from apps.integrations.models import Integration

from .data_access import DATA_ACCESS_TOOL_SPECS

DEMO_INTEGRATION_SLUG = "mexar-demo"


def get_integration_by_slug(slug: str) -> Integration | None:
    return Integration.objects.filter(slug=slug, is_active=True).first()


def get_demo_integration() -> Integration | None:
    return get_integration_by_slug(DEMO_INTEGRATION_SLUG)


def get_integration_for_data_access_tool(tool_name: str) -> Integration | None:
    spec = DATA_ACCESS_TOOL_SPECS.get(tool_name)
    if not spec:
        return None
    slug = spec.get("integration_slug")
    if not slug:
        return None
    return get_integration_by_slug(slug)
