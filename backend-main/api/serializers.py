from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import ChatMessage, ChatSession, KnowledgeBaseEntry, SemanticAnswerCache, CacheLookupEvent

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    referral_code = serializers.CharField(read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'bio', 
                  'grade', 'school', 'plan_tier', 'billing_provider', 'billing_customer_id',
                  'billing_subscription_id', 'billing_status', 'billing_expires_at',
                  'profile_image', 'referral_code', 'created_at']
        read_only_fields = [
            'id', 'created_at', 'plan_tier', 'billing_provider', 'billing_customer_id',
            'billing_subscription_id', 'billing_status', 'billing_expires_at', 'referral_code',
        ]
    
    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'session', 'message', 'response', 'context', 'created_at']
        read_only_fields = ['id', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'subject', 'grade', 'language', 'messages', 'last_message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_last_message(self, obj):
        annotated_message = getattr(obj, 'last_message_text', None)
        if annotated_message:
            return {
                'message': annotated_message[:50] + '...' if len(annotated_message) > 50 else annotated_message,
                'created_at': getattr(obj, 'last_message_created_at', None)
            }
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'message': last_msg.message[:50] + '...' if len(last_msg.message) > 50 else last_msg.message,
                'created_at': last_msg.created_at
            }
        return None


class ChatSessionListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'subject', 'grade', 'language', 'last_message', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        annotated_message = getattr(obj, 'last_message_text', None)
        if annotated_message:
            return {
                'message': annotated_message[:50] + '...' if len(annotated_message) > 50 else annotated_message,
                'created_at': getattr(obj, 'last_message_created_at', None)
            }
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'message': last_msg.message[:50] + '...' if len(last_msg.message) > 50 else last_msg.message,
                'created_at': last_msg.created_at
            }
        return None


class KnowledgeBaseEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeBaseEntry
        fields = [
            'id', 'subject', 'grade', 'unit', 'chapter', 'chapter_title', 'topic',
            'learning_objective', 'question_type', 'difficulty', 'intent',
            'normalized_query', 'answer', 'source_type', 'source_reference',
            'quality_score', 'student_feedback_score', 'textbook_alignment_score',
            'hallucination_risk_score', 'usage_count', 'hit_count',
            'last_verified_at', 'metadata', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'usage_count', 'hit_count', 'created_at', 'updated_at']


class SemanticAnswerCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = SemanticAnswerCache
        fields = [
            'id', 'subject', 'grade', 'unit', 'chapter', 'chapter_title', 'topic',
            'question_type', 'difficulty', 'intent', 'normalized_query', 'answer',
            'source_type', 'source_reference', 'quality_score', 'student_feedback_score',
            'textbook_alignment_score', 'hallucination_risk_score', 'usage_count',
            'hit_count', 'last_verified_at', 'metadata', 'created_from_model',
            'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'usage_count', 'hit_count', 'created_at', 'updated_at']


class CacheLookupEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CacheLookupEvent
        fields = [
            'id', 'message', 'normalized_query', 'subject', 'grade', 'unit', 'chapter',
            'plan_tier', 'decision', 'confidence', 'latency_ms', 'metadata', 'created_at',
        ]
        read_only_fields = fields
