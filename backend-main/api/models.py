from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class User(AbstractUser):
    """Custom User model with additional fields"""
    PLAN_CHOICES = [
        ('free', 'Free'),
        ('paid', 'Paid'),
    ]

    bio = models.TextField(blank=True)
    grade = models.CharField(max_length=10, blank=True)
    school = models.CharField(max_length=200, blank=True)
    plan_tier = models.CharField(max_length=20, choices=PLAN_CHOICES, default='free')
    billing_provider = models.CharField(max_length=40, blank=True, default='')
    billing_customer_id = models.CharField(max_length=128, blank=True, default='', db_index=True)
    billing_subscription_id = models.CharField(max_length=128, blank=True, default='', db_index=True)
    billing_status = models.CharField(max_length=32, blank=True, default='inactive', db_index=True)
    billing_expires_at = models.DateTimeField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    referral_code = models.CharField(max_length=20, blank=True, default='', db_index=True)
    referred_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Fix conflicting related names
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to.',
        related_name='api_user_set',
        related_query_name='api_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='api_user_set',
        related_query_name='api_user',
    )

    def __str__(self):
        return self.username

class ChatSession(models.Model):
    """Model for grouping chat messages into conversations"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='chat_sessions'
    )
    title = models.CharField(max_length=200, blank=True, default='')
    subject = models.CharField(max_length=50, blank=True, default='')
    grade = models.CharField(max_length=10, blank=True, default='10')
    language = models.CharField(max_length=20, blank=True, default='english')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.title or 'Untitled'}"

class ChatMessage(models.Model):
    """Model for storing AI chat history"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='chat_messages'
    )
    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True,
        blank=True
    )
    message = models.TextField()
    response = models.TextField()
    context = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username}: {self.message[:50]}"


class EducationalContentBase(models.Model):
    """Shared educational metadata for reusable textbook-grounded answers."""
    SOURCE_CHOICES = [
        ('precomputed', 'Precomputed'),
        ('semantic_cache', 'Semantic Cache'),
        ('rag', 'RAG'),
        ('ai_generated', 'AI Generated'),
        ('manual', 'Manual'),
    ]

    QUESTION_TYPE_CHOICES = [
        ('explain', 'Explain'),
        ('definition', 'Definition'),
        ('exam_notes', 'Exam Notes'),
        ('important_questions', 'Important Questions'),
        ('summary', 'Summary'),
        ('quiz', 'Quiz'),
        ('solved_exercise', 'Solved Exercise'),
        ('derivation', 'Derivation'),
        ('formula', 'Formula'),
        ('page_explanation', 'Page Explanation'),
        ('faq', 'FAQ'),
        ('general', 'General'),
    ]

    subject = models.CharField(max_length=50, db_index=True)
    grade = models.CharField(max_length=10, default='10', db_index=True)
    unit = models.CharField(max_length=50, blank=True, default='', db_index=True)
    chapter = models.CharField(max_length=50, blank=True, default='', db_index=True)
    chapter_title = models.CharField(max_length=255, blank=True, default='')
    topic = models.CharField(max_length=255, blank=True, default='', db_index=True)
    learning_objective = models.CharField(max_length=255, blank=True, default='')
    question_type = models.CharField(max_length=40, choices=QUESTION_TYPE_CHOICES, default='general', db_index=True)
    difficulty = models.CharField(max_length=30, blank=True, default='easy', db_index=True)
    intent = models.CharField(max_length=80, blank=True, default='', db_index=True)
    normalized_query = models.TextField(blank=True, default='')
    query_fingerprint = models.CharField(max_length=64, blank=True, default='', db_index=True)
    embedding = models.JSONField(default=list, blank=True)
    answer = models.TextField()
    source_type = models.CharField(max_length=40, choices=SOURCE_CHOICES, default='semantic_cache', db_index=True)
    source_reference = models.CharField(max_length=255, blank=True, default='')
    quality_score = models.FloatField(default=0.0, db_index=True)
    student_feedback_score = models.FloatField(default=0.0)
    textbook_alignment_score = models.FloatField(default=0.0)
    hallucination_risk_score = models.FloatField(default=0.0)
    usage_count = models.PositiveIntegerField(default=0, db_index=True)
    hit_count = models.PositiveIntegerField(default=0)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        indexes = [
            models.Index(fields=['grade', 'subject', 'unit', 'chapter', 'question_type']),
            models.Index(fields=['subject', 'intent', 'quality_score']),
            models.Index(fields=['query_fingerprint', 'is_active']),
        ]


class KnowledgeBaseEntry(EducationalContentBase):
    """Precomputed/reviewable textbook knowledge served before live AI."""

    class Meta(EducationalContentBase.Meta):
        verbose_name_plural = 'Knowledge base entries'

    def __str__(self):
        return f"KB {self.grade} {self.subject} {self.chapter}: {self.question_type}"


class SemanticAnswerCache(EducationalContentBase):
    """Learned semantic answer cache populated from strong AI responses."""
    created_from_model = models.CharField(max_length=100, blank=True, default='')

    class Meta(EducationalContentBase.Meta):
        verbose_name_plural = 'Semantic answer cache'

    def __str__(self):
        return f"Cache {self.grade} {self.subject} {self.chapter}: {self.intent}"


class CacheLookupEvent(models.Model):
    """Audit trail for cache/routing decisions."""
    DECISION_CHOICES = [
        ('CACHE_HIT', 'Cache Hit'),
        ('KNOWLEDGE_BASE_HIT', 'Knowledge Base Hit'),
        ('RETRIEVAL_HIT', 'Retrieval Hit'),
        ('AI_REQUIRED', 'AI Required'),
        ('AI_FALLBACK', 'AI Fallback'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    message = models.TextField()
    normalized_query = models.TextField(blank=True, default='')
    subject = models.CharField(max_length=50, blank=True, default='', db_index=True)
    grade = models.CharField(max_length=10, blank=True, default='10', db_index=True)
    unit = models.CharField(max_length=50, blank=True, default='')
    chapter = models.CharField(max_length=50, blank=True, default='')
    plan_tier = models.CharField(max_length=20, blank=True, default='free', db_index=True)
    decision = models.CharField(max_length=40, choices=DECISION_CHOICES, db_index=True)
    confidence = models.FloatField(default=0.0)
    matched_cache = models.ForeignKey(SemanticAnswerCache, on_delete=models.SET_NULL, null=True, blank=True)
    matched_kb = models.ForeignKey(KnowledgeBaseEntry, on_delete=models.SET_NULL, null=True, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=['created_at', 'decision']),
            models.Index(fields=['plan_tier', 'subject', 'decision']),
        ]
