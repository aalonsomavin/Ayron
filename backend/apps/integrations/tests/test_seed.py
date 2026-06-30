import pytest

from apps.integrations.models import Integration


@pytest.mark.django_db
class TestMexarIntegrationSeed:
    def test_seed_creates_two_integrations(self):
        assert Integration.objects.filter(slug="mexar-demo", is_active=True).exists()
        assert Integration.objects.filter(slug="mexar-competencia", is_active=True).exists()

    def test_demo_integration_display_config(self):
        integration = Integration.objects.get(slug="mexar-demo")
        assert integration.name == "Mexar Pharma — Producción"
        assert integration.type == Integration.Type.POSTGRES
        assert integration.config["display"]["structure_label"] == "11 tablas"
        assert len(integration.schema_cache["tables"]) == 11
