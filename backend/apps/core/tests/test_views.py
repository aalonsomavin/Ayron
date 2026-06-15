import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestProtectedRoutes:
    def test_anonymous_redirected_on_home(self, client):
        response = client.get(reverse("core:home"))
        assert response.status_code == 302
        assert reverse("accounts:login") in response.url

    def test_logged_in_gets_200_on_home(self, client):
        user = User.objects.create_user(username="testuser", password="testpass123")
        client.force_login(user)
        response = client.get(reverse("core:home"))
        assert response.status_code == 200


@pytest.mark.django_db
class TestPublicRoutes:
    def test_anonymous_gets_200_on_health(self, client):
        response = client.get(reverse("core:health"))
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


@pytest.mark.django_db
class TestLogin:
    def test_login_success_redirects(self, client):
        User.objects.create_user(username="testuser", password="testpass123")
        response = client.post(
            reverse("accounts:login"),
            {"username": "testuser", "password": "testpass123"},
            follow=True,
        )
        assert response.status_code == 200
        assert reverse("core:home") in [r[0] for r in response.redirect_chain]

    def test_login_with_next_redirects_to_next(self, client):
        User.objects.create_user(username="testuser", password="testpass123")
        response = client.post(
            reverse("accounts:login") + "?next=/health",
            {"username": "testuser", "password": "testpass123", "next": "/health"},
        )
        assert response.status_code == 302
        assert response.url == "/health"
