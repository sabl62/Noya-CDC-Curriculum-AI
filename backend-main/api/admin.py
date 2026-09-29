from django.contrib import admin

from .models import CacheLookupEvent, ChatMessage, ChatSession, KnowledgeBaseEntry, Payment, SemanticAnswerCache, UsageCounter, User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "plan_tier", "grade", "is_staff", "date_joined")
    list_filter = ("plan_tier", "is_staff", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "subject", "grade", "updated_at")
    list_filter = ("subject", "grade")
    search_fields = ("title", "user__username")


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "session", "created_at")
    search_fields = ("message", "response", "user__username")


@admin.register(KnowledgeBaseEntry)
class KnowledgeBaseEntryAdmin(admin.ModelAdmin):
    list_display = ("id", "grade", "subject", "unit", "chapter", "question_type", "quality_score", "usage_count", "is_active")
    list_filter = ("grade", "subject", "question_type", "is_active")
    search_fields = ("topic", "chapter_title", "normalized_query", "answer")


@admin.register(SemanticAnswerCache)
class SemanticAnswerCacheAdmin(admin.ModelAdmin):
    list_display = ("id", "grade", "subject", "unit", "chapter", "intent", "quality_score", "hallucination_risk_score", "usage_count", "is_active")
    list_filter = ("grade", "subject", "intent", "is_active")
    search_fields = ("topic", "normalized_query", "answer")


@admin.register(CacheLookupEvent)
class CacheLookupEventAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "plan_tier", "subject", "decision", "confidence", "latency_ms")
    list_filter = ("decision", "plan_tier", "subject")
    search_fields = ("message", "normalized_query")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "provider", "plan", "amount", "currency", "status", "reference", "created_at")
    list_filter = ("provider", "status", "plan")
    search_fields = ("reference", "provider_reference", "provider_transaction_id", "user__username")
    readonly_fields = ("raw_response", "created_at", "updated_at")


@admin.register(UsageCounter)
class UsageCounterAdmin(admin.ModelAdmin):
    list_display = (
        "key", "user", "daily_count", "daily_limit_reached_at",
        "monthly_count", "monthly_limit_reached_at", "minute_count", "updated_at",
    )
    list_filter = ("daily_limit_reached_at", "monthly_limit_reached_at")
    search_fields = ("key", "user__username")
    readonly_fields = ("key", "user", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False
