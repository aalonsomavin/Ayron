from django.contrib import admin

from .models import AgentEvent, Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("role", "content", "created_at")


class AgentEventInline(admin.TabularInline):
    model = AgentEvent
    extra = 0
    readonly_fields = ("event_type", "sequence_number", "payload", "created_at")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "user", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("title", "user__username")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [MessageInline, AgentEventInline]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role",)
    readonly_fields = ("created_at",)


@admin.register(AgentEvent)
class AgentEventAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "event_type", "sequence_number", "created_at")
    list_filter = ("event_type",)
    readonly_fields = ("created_at",)
