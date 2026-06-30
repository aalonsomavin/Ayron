import uuid

from django.db import models


class Integration(models.Model):
    class Type(models.TextChoices):
        POSTGRES = "postgres", "PostgreSQL"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=32, choices=Type.choices)
    config = models.JSONField(default=dict)
    schema_cache = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
