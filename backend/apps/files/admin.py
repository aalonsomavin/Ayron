from django.contrib import admin

from apps.files.models import File


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "conversation", "uploaded_by", "version", "updated_at")
    list_filter = ("mime_type",)
    search_fields = ("original_name",)
    readonly_fields = ("id", "created_at", "updated_at", "size_bytes")
