import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="sourcesuser", password="pass")


@pytest.mark.django_db
class TestSourcesList:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("sources:list"))
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_authenticated_user_gets_page(self, client, user):
        client.force_login(user)
        response = client.get(reverse("sources:list"))
        assert response.status_code == 200
        assert "Fuentes de datos" in response.content.decode()

    def test_page_shows_table_and_mexar_sources(self, client, user):
        client.force_login(user)
        response = client.get(reverse("sources:list"))
        content = response.content.decode()
        assert "Ayron · Conexiones" in content
        assert "2 fuentes" in content
        assert "2 conectadas" in content
        assert "Fuente" in content
        assert "Estado" in content
        assert "Volumen" in content
        assert "Mexar Pharma — Producción" in content
        assert "Inteligencia de Mercado — Precios Competencia" in content
        assert "Conectada" in content
        assert "842k filas · 128 MB" in content

    def test_sources_read_from_integrations(self, client, user):
        from apps.integrations.models import Integration

        Integration.objects.all().delete()
        Integration.objects.create(
            slug="test-source",
            name="Test Source",
            type=Integration.Type.POSTGRES,
            config={
                "display": {
                    "subtitle": "test · PostgreSQL",
                    "structure_label": "3 tablas",
                    "volume_label": "1k filas",
                }
            },
            is_active=True,
        )
        client.force_login(user)
        response = client.get(reverse("sources:list"))
        content = response.content.decode()
        assert "Test Source" in content
        assert "3 tablas" in content

    def test_htmx_returns_partial(self, client, user):
        client.force_login(user)
        response = client.get(
            reverse("sources:list"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="sources-view"' in content
        assert "<html" not in content.lower()
