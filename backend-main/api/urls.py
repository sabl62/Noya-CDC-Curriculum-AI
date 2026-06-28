from django.http import HttpResponse
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    RegisterView,
    LogoutView,
    CurrentUserView,
    BillingPlansView,
    BillingCheckoutView,
    BillingStatusView,
    BillingWebhookView,
    ChatView,
    ChatHistoryView,
    ChatSessionView,
    ChatSessionDetailView,
    TextbookPDFView,
    TextbookPagesView,
    health_check,
    RAGStatusView,
    InitializeRAGView,
    SearchCurriculumView,
    SystemCheckView,
    CacheInspectView,
    KnowledgeBaseEntryView,
    SemanticAnswerCacheView,
    CacheMetricsView,
    ContentProcessorView,
    AnalyticsTrackView,
    ReferralInfoView,
    UsageStatsView,
)

urlpatterns = [
    # Health check
    path('ping/', health_check, name='health_check'),
    
    # Auth endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/user/', CurrentUserView.as_view(), name='current_user'),

    # Billing
    path('billing/plans/', BillingPlansView.as_view(), name='billing_plans'),
    path('billing/checkout/', BillingCheckoutView.as_view(), name='billing_checkout'),
    path('billing/status/', BillingStatusView.as_view(), name='billing_status'),
    path('billing/webhook/', BillingWebhookView.as_view(), name='billing_webhook'),
    
    # SIKSYA AI Chat
    path('chat/', ChatView.as_view(), name='chat'),
    path('chat/history/', ChatHistoryView.as_view(), name='chat_history'),
    path('chat/clear/', ChatHistoryView.as_view(), name='chat_clear'),
    path('chat/sessions/', ChatSessionView.as_view(), name='chat_sessions'),
    path('chat/sessions/<int:session_id>/', ChatSessionDetailView.as_view(), name='chat_session_detail'),

    # Textbook reader
    path('textbooks/<str:subject>/pdf/', TextbookPDFView.as_view(), name='textbook_pdf'),
    path('textbooks/pages/', TextbookPagesView.as_view(), name='textbook_pages'),
    
    # Analytics
    path('analytics/track/', AnalyticsTrackView.as_view(), name='analytics_track'),

    # Referral
    path('referral/info/', ReferralInfoView.as_view(), name='referral_info'),

    # Usage Stats
    path('usage/stats/', UsageStatsView.as_view(), name='usage_stats'),

    # RAG System
    path('system/check/', SystemCheckView.as_view(), name='system_check'),
    path('rag/status/', RAGStatusView.as_view(), name='rag_status'),
    path('rag/init/', InitializeRAGView.as_view(), name='rag_init'),
    path('rag/search/', SearchCurriculumView.as_view(), name='rag_search'),

    # Semantic cache and precomputed knowledge layer
    path('cache/inspect/', CacheInspectView.as_view(), name='cache_inspect'),
    path('cache/knowledge/', KnowledgeBaseEntryView.as_view(), name='cache_knowledge'),
    path('cache/answers/', SemanticAnswerCacheView.as_view(), name='cache_answers'),
    path('cache/metrics/', CacheMetricsView.as_view(), name='cache_metrics'),
    path('cache/process-content/', ContentProcessorView.as_view(), name='cache_process_content'),
]
