import hashlib
import hmac
import json
import os
from datetime import datetime, timezone as datetime_timezone

import httpx
from rest_framework import permissions, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import FileResponse, StreamingHttpResponse
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Subquery
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from .models import ChatMessage, ChatSession, KnowledgeBaseEntry, SemanticAnswerCache, CacheLookupEvent
from .serializers import (
    UserSerializer,
    ChatMessageSerializer,
    ChatSessionSerializer,
    ChatSessionListSerializer,
    KnowledgeBaseEntrySerializer,
    SemanticAnswerCacheSerializer,
    CacheLookupEventSerializer,
)
from .chapter_pdf_context import (
    PDF_FILENAMES,
    get_page_range_for_selection,
    get_pdf_path,
    get_textbook_pages,
)
from .semantic_cache import (
    embed_text,
    educational_fingerprint,
    extract_topic,
    get_semantic_cache_service,
    infer_intent,
    normalize_query,
    scope_filters,
)
from .content_processor import (
    CONTENT_PROCESSOR_SYSTEM_PROMPT,
    build_content_processor_prompt,
    build_entries_from_processed_payload,
    extract_json_object,
    normalize_processed_payload,
    save_processed_entries,
)

User = get_user_model()
ai_service = None

BILLING_PLANS = {
    'pro': {
        'id': 'pro',
        'name': 'Noya Pro',
        'price': 'Monthly subscription',
        'description': 'Unlimited live RAG answers, priority responses, and a polished pro experience.',
        'features': [
            'Unlimited live answers',
            'Priority grounded responses',
            'Saved chats and billing support',
        ],
        'price_id_env': 'STRIPE_PRICE_ID',
    }
}


def get_ai_service():
    global ai_service
    if ai_service is None:
        from .ai_service import AIService
        ai_service = AIService()
    return ai_service


def clamp_session_title(value, fallback='New Chat'):
    title = str(value or fallback).strip() or fallback
    return title[:197] + '...' if len(title) > 200 else title


def _clip_context_text(value, limit=900):
    text = " ".join(str(value or "").split())
    return text[:limit] + "..." if len(text) > limit else text


def build_conversation_context(session, limit=8):
    if not session:
        return ""

    recent_messages = list(session.messages.order_by("-created_at")[:limit])
    recent_messages.reverse()
    if not recent_messages:
        return ""

    lines = [
        "Recent conversation from this same chat session.",
        "Use it only to understand follow-up references and the student's current intent.",
    ]
    for index, chat in enumerate(recent_messages, start=1):
        subject = (chat.context or {}).get("subject") or session.subject or ""
        grade = (chat.context or {}).get("grade") or session.grade or "10"
        lines.append(
            f"Turn {index} | grade={grade} | subject={subject}\n"
            f"Student: {_clip_context_text(chat.message, 450)}\n"
            f"Assistant: {_clip_context_text(chat.response, 900)}"
        )
    return "\n\n".join(lines)


def _frontend_base_url(request=None):
    env_url = os.getenv('FRONTEND_URL', '').rstrip('/')
    if env_url:
        return env_url
    if request is not None:
        origin = request.headers.get('Origin', '').rstrip('/')
        if origin:
            return origin
    return 'http://localhost:5173'


def _stripe_signature_valid(payload: bytes, signature_header: str, secret: str) -> bool:
    if not secret:
        return True
    if not signature_header:
        return False

    parts = {}
    for item in signature_header.split(','):
        key, _, value = item.partition('=')
        if key and value:
            parts.setdefault(key, []).append(value)

    timestamp = (parts.get('t') or [''])[0]
    expected = hmac.new(
        secret.encode('utf-8'),
        f'{timestamp}.{payload.decode("utf-8")}'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in parts.get('v1', []))


def _resolve_billing_user(event_object):
    metadata = event_object.get('metadata') or {}
    user_id = metadata.get('user_id') or event_object.get('client_reference_id')
    if not user_id:
        return None
    return User.objects.filter(id=user_id).first()


def _set_user_billing_state(user, *, plan_tier=None, provider='', customer_id='', subscription_id='', status_value='', expires_at=None):
    update_fields = ['billing_provider', 'billing_customer_id', 'billing_subscription_id', 'billing_status']
    if plan_tier is not None:
        user.plan_tier = plan_tier
        update_fields.append('plan_tier')
    user.billing_provider = provider
    user.billing_customer_id = customer_id or user.billing_customer_id
    user.billing_subscription_id = subscription_id or user.billing_subscription_id
    user.billing_status = status_value or user.billing_status
    if expires_at is not None:
        user.billing_expires_at = expires_at
        update_fields.append('billing_expires_at')
    user.save(update_fields=list(dict.fromkeys(update_fields)))


# ============ AUTH VIEWS ============

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            import uuid
            user.referral_code = user.username[:12] + uuid.uuid4().hex[:4]
            ref_code = request.data.get('ref', '')
            if ref_code:
                referrer = User.objects.filter(referral_code=ref_code).first()
                if referrer:
                    user.referred_by = referrer
            user.save(update_fields=['referral_code', 'referred_by'])
            return Response({
                'user': UserSerializer(user).data,
                'message': 'User created successfully'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                from rest_framework_simplejwt.tokens import RefreshToken
                token = RefreshToken(refresh_token)
                token.blacklist()
        except Exception:
            pass
        return Response({'message': 'Logged out successfully'})

class CurrentUserView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)

    def patch(self, request):
        if request.user.is_authenticated:
            serializer = UserSerializer(request.user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)


class BillingPlansView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'currency': 'USD',
            'billing_enabled': bool(os.getenv('STRIPE_SECRET_KEY', '').strip()),
            'plans': list(BILLING_PLANS.values()),
        })


class BillingCheckoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        plan_id = str(request.data.get('plan', 'pro')).lower()
        plan = BILLING_PLANS.get(plan_id)
        if not plan:
            return Response({'error': 'Unknown billing plan.'}, status=status.HTTP_400_BAD_REQUEST)

        secret = os.getenv('STRIPE_SECRET_KEY', '').strip()
        price_id = os.getenv(plan['price_id_env'], '').strip()
        if not secret or not price_id:
            return Response({
                'provider': 'stripe',
                'checkout_url': None,
                'status': 'billing_setup_pending',
                'plan': plan,
            }, status=status.HTTP_200_OK)

        frontend_url = _frontend_base_url(request)
        payload = {
            'mode': 'subscription',
            'success_url': f'{frontend_url}/?billing=success',
            'cancel_url': f'{frontend_url}/pricing?billing=cancel',
            'client_reference_id': str(request.user.id),
            'line_items[0][price]': price_id,
            'line_items[0][quantity]': '1',
            'metadata[user_id]': str(request.user.id),
            'metadata[username]': request.user.username,
            'subscription_data[metadata][user_id]': str(request.user.id),
            'subscription_data[metadata][username]': request.user.username,
        }
        if request.user.email:
            payload['customer_email'] = request.user.email

        try:
            response = httpx.post(
                'https://api.stripe.com/v1/checkout/sessions',
                data=payload,
                headers={'Authorization': f'Bearer {secret}'},
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()
            return Response({
                'provider': 'stripe',
                'checkout_url': data.get('url'),
                'session_id': data.get('id'),
                'plan': plan,
            })
        except Exception as exc:
            return Response({'error': f'Billing checkout failed: {exc}'}, status=status.HTTP_502_BAD_GATEWAY)


class BillingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'plan_tier': getattr(request.user, 'plan_tier', 'free'),
            'billing_provider': getattr(request.user, 'billing_provider', ''),
            'billing_status': getattr(request.user, 'billing_status', 'inactive'),
            'billing_expires_at': getattr(request.user, 'billing_expires_at', None),
        })


class BillingWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        secret = os.getenv('STRIPE_WEBHOOK_SECRET', '').strip()
        raw_body = request.body or b''
        signature = request.headers.get('Stripe-Signature', '')

        if secret and not _stripe_signature_valid(raw_body, signature, secret):
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = json.loads(raw_body.decode('utf-8'))
        except Exception:
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = event.get('type', '')
        event_object = (event.get('data') or {}).get('object') or {}
        user = _resolve_billing_user(event_object)

        if not user:
            return Response({'received': True, 'ignored': True})

        if event_type in {'checkout.session.completed', 'customer.subscription.created', 'customer.subscription.updated'}:
            subscription_status = str(event_object.get('status') or 'active').lower()
            expires_at = event_object.get('current_period_end')
            expires_at_value = datetime.fromtimestamp(expires_at, tz=datetime_timezone.utc) if expires_at else None
            _set_user_billing_state(
                user,
                plan_tier='paid' if subscription_status in {'active', 'trialing'} else 'free',
                provider='stripe',
                customer_id=str(event_object.get('customer') or ''),
                subscription_id=str(event_object.get('subscription') or event_object.get('id') or ''),
                status_value=subscription_status,
                expires_at=expires_at_value,
            )
        elif event_type in {'customer.subscription.deleted', 'invoice.payment_failed'}:
            _set_user_billing_state(
                user,
                plan_tier='free',
                provider='stripe',
                customer_id=str(event_object.get('customer') or ''),
                subscription_id=str(event_object.get('id') or ''),
                status_value='inactive',
            )

        return Response({'received': True})

# ============ CHAT/AI VIEWS ============

class ChatSessionView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        last_message = ChatMessage.objects.filter(session=OuterRef('pk')).order_by('-created_at')
        sessions = (
            ChatSession.objects
            .filter(user=request.user)
            .annotate(
                last_message_text=Subquery(last_message.values('message')[:1]),
                last_message_created_at=Subquery(last_message.values('created_at')[:1]),
            )[:50]
        )
        serializer = ChatSessionListSerializer(sessions, many=True)
        return Response(serializer.data)

    def post(self, request):
        title = clamp_session_title(request.data.get('title', ''))
        subject = request.data.get('subject', '')
        grade = request.data.get('grade', '10')
        language = request.data.get('language', 'english')

        session = ChatSession.objects.create(
            user=request.user,
            title=title,
            subject=subject,
            grade=grade,
            language=language
        )
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        session_id = request.data.get('session_id')
        if session_id:
            ChatSession.objects.filter(id=session_id, user=request.user).delete()
        return Response({'message': 'Session deleted'})

class ChatSessionDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        try:
            session = ChatSession.objects.get(id=session_id, user=request.user)
            serializer = ChatSessionSerializer(session)
            return Response(serializer.data)
        except ChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


class ChatView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        message = request.data.get('message', '')
        context = request.data.get('context', {})
        session_id = request.data.get('session_id')
        user = request.user if request.user.is_authenticated else None

        session = None
        if user and user.is_authenticated and session_id:
            try:
                session = ChatSession.objects.get(id=session_id, user=user)
            except ChatSession.DoesNotExist:
                session = None

        if not session and user and user.is_authenticated:
            session = ChatSession.objects.create(
                user=user,
                title=clamp_session_title(context.get('subject', 'New Chat') if context else 'New Chat'),
                subject=context.get('subject', '') if context else '',
                grade=context.get('grade', '10') if context else '10',
                language='english'
            )

        def event_stream():
            try:
                conversation_context = build_conversation_context(session)
                service = get_ai_service()

                final_event = None

                for event in service.chat(
                    message=message,
                    user=user,
                    personal_context=conversation_context,
                    context=context
                ):
                    if event.get("type") == "complete":
                        final_event = event

                        # Save to database
                        if user and user.is_authenticated:
                            saved_context = dict(context or {})
                            saved_context['source'] = event.get('source', '')
                            ChatMessage.objects.create(
                                user=user,
                                session=session,
                                message=message,
                                response=event.get('response', ''),
                                context=saved_context
                            )

                            if session:
                                current_title = session.title.lower() if session.title else ''
                                is_generic = current_title in ['', 'new chat', 'english', 'math', 'mathematics', 'science', 'omaths', 'social', 'social studies']
                                if is_generic and message:
                                    try:
                                        new_title = service.generate_title(message)
                                        if new_title:
                                            session.title = clamp_session_title(new_title)
                                    except Exception as e:
                                        print(f"Title generation error: {e}")
                                        session.title = clamp_session_title(message, fallback='New Chat')
                                    session.save()

                        # Yield final event with session metadata
                        yield f"data: {json.dumps({
                            **event,
                            'session_id': session.id if session else None,
                            'session_title': session.title if session else None
                        })}\n\n"
                    else:
                        yield f"data: {json.dumps(event)}\n\n"

                if not final_event:
                    yield f"data: {json.dumps({'type': 'error', 'message': 'No response generated'})}\n\n"

            except Exception as e:
                import traceback
                with open("error.log", "w") as f:
                    f.write(traceback.format_exc())
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response


class CacheInspectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        message = request.data.get('message', '')
        context = request.data.get('context', {})
        plan_tier = getattr(request.user, 'plan_tier', 'free')
        decision = get_semantic_cache_service().inspect(
            message,
            context=context,
            user=request.user,
            plan_tier=plan_tier,
        )
        return Response({
            'decision': decision.decision,
            'confidence': decision.confidence,
            'source': decision.source,
            'answer_preview': decision.answer[:500] if decision.answer else '',
            'matched_cache_id': decision.matched_cache.id if decision.matched_cache else None,
            'matched_kb_id': decision.matched_kb.id if decision.matched_kb else None,
            'metadata': decision.metadata or {},
        })


class KnowledgeBaseEntryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entries = KnowledgeBaseEntry.objects.filter(is_active=True)
        subject = request.query_params.get('subject')
        grade = request.query_params.get('grade')
        chapter = request.query_params.get('chapter')
        if subject:
            entries = entries.filter(subject=subject)
        if grade:
            entries = entries.filter(grade=grade)
        if chapter:
            entries = entries.filter(chapter=chapter)
        entries = entries.order_by('-quality_score', '-usage_count')[:100]
        return Response(KnowledgeBaseEntrySerializer(entries, many=True).data)

    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)

        data = dict(request.data)
        context = {
            'grade': data.get('grade', '10'),
            'subject': data.get('subject', ''),
            'unit': data.get('unit', ''),
            'chapter': data.get('chapter', ''),
            'chapter_title': data.get('chapter_title', ''),
            'study_mode': data.get('question_type', ''),
        }
        seed_query = data.get('normalized_query') or data.get('topic') or data.get('chapter_title') or data.get('answer', '')[:240]
        normalized = normalize_query(seed_query)
        intent = data.get('intent') or infer_intent(seed_query, data.get('question_type', ''))
        topic = data.get('topic') or extract_topic(seed_query, context)
        scope = scope_filters(context)
        data['subject'] = scope['subject']
        data['grade'] = scope['grade']
        data['unit'] = scope['unit']
        data['chapter'] = scope['chapter']
        data['chapter_title'] = scope['chapter_title']
        data['topic'] = topic
        data['intent'] = intent
        data['question_type'] = data.get('question_type') or intent
        data['normalized_query'] = normalized
        data['query_fingerprint'] = educational_fingerprint(scope, intent, topic, normalized)
        data['embedding'] = embed_text(f"{scope.get('chapter_title', '')} {topic} {intent} {normalized} {data.get('answer', '')[:800]}")
        data.setdefault('quality_score', 0.9)
        data.setdefault('textbook_alignment_score', 0.9)
        data.setdefault('hallucination_risk_score', 0.08)
        data.setdefault('source_type', 'precomputed')

        serializer = KnowledgeBaseEntrySerializer(data=data)
        serializer.is_valid(raise_exception=True)
        entry = serializer.save()
        return Response(KnowledgeBaseEntrySerializer(entry).data, status=status.HTTP_201_CREATED)


class SemanticAnswerCacheView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        entries = SemanticAnswerCache.objects.filter(is_active=True)
        subject = request.query_params.get('subject')
        grade = request.query_params.get('grade')
        decision_limit = int(request.query_params.get('limit', 100))
        if subject:
            entries = entries.filter(subject=subject)
        if grade:
            entries = entries.filter(grade=grade)
        entries = entries.order_by('-quality_score', '-usage_count')[:min(decision_limit, 200)]
        return Response(SemanticAnswerCacheSerializer(entries, many=True).data)


class CacheMetricsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        recent = CacheLookupEvent.objects.order_by('-created_at')[:1000]
        counts = {}
        total_latency = 0
        total = 0
        for event in recent:
            counts[event.decision] = counts.get(event.decision, 0) + 1
            total_latency += event.latency_ms
            total += 1
        return Response({
            'events_sampled': total,
            'decision_counts': counts,
            'cache_hit_rate': round((counts.get('CACHE_HIT', 0) + counts.get('KNOWLEDGE_BASE_HIT', 0)) / total, 4) if total else 0,
            'ai_required_rate': round(counts.get('AI_REQUIRED', 0) / total, 4) if total else 0,
            'avg_decision_latency_ms': round(total_latency / total, 2) if total else 0,
            'recent_events': CacheLookupEventSerializer(recent[:30], many=True).data,
        })


class ContentProcessorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_staff:
            return Response({'error': 'Staff access required'}, status=status.HTTP_403_FORBIDDEN)

        subject = request.data.get('subject', '')
        grade = request.data.get('grade', '10')
        chapter = request.data.get('chapter', '')
        topic = request.data.get('topic', '')
        raw_textbook_content = request.data.get('raw_textbook_content', '')
        unit = request.data.get('unit', '')
        chapter_title = request.data.get('chapter_title', topic)
        save = bool(request.data.get('save', True))

        if not raw_textbook_content.strip():
            return Response({'error': 'raw_textbook_content is required'}, status=status.HTTP_400_BAD_REQUEST)

        service = get_ai_service()
        prompt = build_content_processor_prompt(subject, grade, chapter, topic, raw_textbook_content)
        raw_response = service._generate_with_gemini(prompt, CONTENT_PROCESSOR_SYSTEM_PROMPT)
        payload = normalize_processed_payload(extract_json_object(raw_response), {
            'subject': subject,
            'grade': grade,
            'chapter': chapter,
            'topic': topic,
        })
        entries = build_entries_from_processed_payload(payload, {
            'subject': subject,
            'grade': grade,
            'unit': unit,
            'chapter': chapter,
            'chapter_title': chapter_title,
        })

        saved_count = 0
        saved_ids = []
        if save:
            saved_count, saved_ids = save_processed_entries(entries)

        return Response({
            'processed': payload,
            'entry_count': len(entries),
            'saved_count': saved_count,
            'saved_ids': saved_ids,
        }, status=status.HTTP_201_CREATED if save else status.HTTP_200_OK)


@method_decorator(xframe_options_exempt, name='dispatch')
class TextbookPDFView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, subject):
        pdf_path = get_pdf_path(subject)
        if not pdf_path:
            return Response({'error': 'Textbook PDF not found'}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(open(pdf_path, 'rb'), content_type='application/pdf')
        response['Content-Disposition'] = f'inline; filename="{PDF_FILENAMES.get((subject or "").lower(), "textbook.pdf")}"'
        return response


class TextbookPagesView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        subject = request.query_params.get('subject', '')
        unit = request.query_params.get('unit')
        chapter = request.query_params.get('chapter')
        title = request.query_params.get('title', '')

        page_range = get_page_range_for_selection(subject, unit=unit, chapter=chapter, title=title)
        if not page_range:
            return Response({'error': 'Chapter page range not found'}, status=status.HTTP_404_NOT_FOUND)

        start_page, end_page = page_range
        include_text = str(request.query_params.get('include_text', 'false')).lower() in {'1', 'true', 'yes'}
        pages = get_textbook_pages(subject, start_page, end_page) if include_text else []
        return Response({
            'subject': subject,
            'unit': unit,
            'chapter': chapter,
            'title': title,
            'start_page': start_page,
            'end_page': end_page,
            'pages': pages,
        })

class ChatHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        session_id = request.query_params.get('session_id')
        limit = int(request.query_params.get('limit', 50))

        if session_id:
            messages = ChatMessage.objects.filter(
                user=request.user, 
                session_id=session_id
            ).order_by('created_at')[:limit]
        else:
            messages = ChatMessage.objects.filter(user=request.user).order_by('-created_at')[:limit]

        return Response(ChatMessageSerializer(messages, many=True).data)

    def delete(self, request):
        session_id = request.query_params.get('session_id')
        if session_id:
            ChatMessage.objects.filter(user=request.user, session_id=session_id).delete()
            ChatSession.objects.filter(id=session_id, user=request.user).delete()
        else:
            ChatMessage.objects.filter(user=request.user).delete()
            ChatSession.objects.filter(user=request.user).delete()
        return Response({'message': 'Chat history cleared'})

# ============ HEALTH CHECK ============

@api_view(['GET'])
def health_check(request):
    return Response({'status': 'ok'})

# ============ RAG VIEWS ============

class SystemCheckView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            check_result = get_ai_service().system_check()
            return Response(check_result)
        except Exception as e:
            return Response({'error': str(e), 'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RAGStatusView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        try:
            rag_status = get_ai_service().get_rag_status()
            return Response(rag_status)
        except Exception as e:
            return Response({'error': str(e), 'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class InitializeRAGView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        force = request.data.get('force_rebuild', False)
        try:
            result = get_ai_service().initialize_rag(force_rebuild=force)
            return Response(result)
        except Exception as e:
            return Response({'error': str(e), 'status': 'error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SearchCurriculumView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        query = request.query_params.get('query', '')
        grade = request.query_params.get('grade', None)
        subject = request.query_params.get('subject', None)
        top_k = int(request.query_params.get('top_k', 5))

        if not query:
            return Response({'error': 'Query required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .rag_service import get_rag_service
            rag = get_rag_service()

            if not rag.initialized:
                return Response({'error': 'RAG not initialized'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            results = rag.retrieve(query, grade, subject, top_k)
            return Response({'query': query, 'results': results})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AnalyticsTrackView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        event = request.data.get('event', '')
        data = request.data.get('data', {})
        user = request.user if request.user.is_authenticated else None
        print(f"[Analytics] event={event} user={getattr(user, 'username', 'anon')} data={data}")
        return Response({'ok': True})


class ReferralInfoView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        referral_count = User.objects.filter(referred_by=request.user).count()
        return Response({
            'referral_code': request.user.referral_code or '',
            'referral_count': referral_count,
            'referral_url': f"{_frontend_base_url(request)}/signup?ref={request.user.referral_code}" if request.user.referral_code else '',
        })


class UsageStatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        total_messages = ChatMessage.objects.filter(user=request.user).count()
        total_sessions = ChatSession.objects.filter(user=request.user).count()
        today = timezone.localdate()
        today_messages = ChatMessage.objects.filter(user=request.user, created_at__date=today).count()
        return Response({
            'total_messages': total_messages,
            'total_sessions': total_sessions,
            'today_messages': today_messages,
            'plan_tier': request.user.plan_tier,
        })
