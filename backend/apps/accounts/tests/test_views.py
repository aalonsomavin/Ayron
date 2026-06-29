import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
def test_login_page_loads(client):
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "ay-login-root" in content
    assert "Inicia sesión" in content


@pytest.mark.django_db
def test_logout_redirects(client):
    user = User.objects.create_user(username="testuser", password="testpass123")
    client.force_login(user)
    response = client.post(reverse("accounts:logout"), follow=True)
    assert response.status_code == 200
