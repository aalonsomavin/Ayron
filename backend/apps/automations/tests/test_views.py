import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="automationsuser", password="pass")


@pytest.mark.django_db
class TestAutomationsList:
    def test_anonymous_redirected_to_login(self, client):
        response = client.get(reverse("automations:list"))
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_authenticated_user_gets_page(self, client, user):
        client.force_login(user)
        response = client.get(reverse("automations:list"))
        assert response.status_code == 200
        assert "Automatizaciones" in response.content.decode()

    def test_page_shows_mock_automations(self, client, user):
        client.force_login(user)
        response = client.get(reverse("automations:list"))
        content = response.content.decode()
        assert "Ayron · Programación" in content
        assert "3 automatizaciones" in content
        assert "1 activas" in content
        assert "Resumen mensual de ventas por área terapéutica" in content
        assert "Monitoreo diario de precios vs competencia" in content
        assert "Pipeline CRM — oportunidades por vencer" in content
        assert "Mensual" in content
        assert "Diario" in content
        assert "Semanal" in content
        assert "Activa" in content
        assert "Inactiva" in content

    def test_action_buttons_are_disabled(self, client, user):
        client.force_login(user)
        response = client.get(reverse("automations:list"))
        content = response.content.decode()
        assert content.count('class="ay-automations-card__action-btn"') == 9
        assert content.count("disabled") >= 13

    def test_htmx_returns_partial(self, client, user):
        client.force_login(user)
        response = client.get(
            reverse("automations:list"),
            HTTP_HX_REQUEST="true",
        )
        assert response.status_code == 200
        content = response.content.decode()
        assert 'id="automations-view"' in content
        assert "<html" not in content.lower()
