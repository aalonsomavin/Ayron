from django.contrib import admin

from apps.provenance.models import DataAccess, DataClaim, ProvenanceLink


class ProvenanceLinkInline(admin.TabularInline):
    model = ProvenanceLink
    extra = 0
    readonly_fields = ("id",)
    raw_id_fields = ("data_access",)


@admin.register(DataClaim)
class DataClaimAdmin(admin.ModelAdmin):
    list_display = ("claim_key", "surface", "label", "conversation", "artifact_file", "artifact_version")
    list_filter = ("surface",)
    search_fields = ("claim_key", "label")
    readonly_fields = ("id",)
    raw_id_fields = ("conversation", "message", "artifact_file")
    inlines = [ProvenanceLinkInline]


@admin.register(ProvenanceLink)
class ProvenanceLinkAdmin(admin.ModelAdmin):
    list_display = ("claim", "data_access", "transformation", "ordinal")
    readonly_fields = ("id",)
    raw_id_fields = ("claim", "data_access")


@admin.register(DataAccess)
class DataAccessAdmin(admin.ModelAdmin):
    list_display = ("tool_call_id", "access_kind", "conversation", "executed_at")
    list_filter = ("access_kind",)
    search_fields = ("tool_call_id",)
    readonly_fields = ("id", "executed_at")
    raw_id_fields = ("conversation", "message", "integration", "file", "agent_event")
