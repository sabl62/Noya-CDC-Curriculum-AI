"""Chat usage limits: daily/monthly quotas, per-minute rate limit, counting rules.

Numbers are injected through env vars so the tests stay correct even if
.env sets real limits, and so nothing numeric has to match a hard-coded
default twice.
"""

import json
import os
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import UsageCounter, User
from .usage_limits import (
    DEFAULT_RATE_LIMIT,
    UsageLimitExceeded,
    normalize_plan,
    plan_limits,
    rate_limit_per_minute,
)

# Isolates every test from whatever the developer's .env happens to contain.
BASE_ENV = {
    'USAGE_FREE_DAILY_LIMIT': '15',
    'USAGE_FREE_MONTHLY_LIMIT': '300',
    'USAGE_PAID_DAILY_LIMIT': '150',
    'USAGE_PAID_MONTHLY_LIMIT': '1000',
    'USAGE_RATE_LIMIT_PER_MINUTE': '5',
}


def with_env(**overrides):
    env = dict(BASE_ENV)
    env.update({key: str(value) for key, value in overrides.items()})
    return patch.dict(os.environ, env)


def consume(response):
    """Drain a streaming SSE response (and therefore run the generator)."""
    if getattr(response, 'streaming_content', None) is not None:
        return b''.join(response.streaming_content)
    return getattr(response, 'content', b'')


class FakeChatService:
    """Deterministic stand-in for the real AI service."""

    def __init__(self, complete_event=None):
        self.complete_event = complete_event or {
            'type': 'complete',
            'response': 'Gravity is the force that pulls objects together.',
            'source': 'Textbook — Science — Gravitation',
        }

    def chat(self, message, user=None, personal_context='', context=None):
        yield {'type': 'status', 'stage': 'cache', 'message': 'Searching the textbook...'}
        yield dict(self.complete_event)

    def generate_title(self, message):
        return 'Practice chat'


class PlanLimitTests(TestCase):
    def test_default_free_and_paid_numbers(self):
        self.assertEqual(plan_limits('free'), {'plan': 'free', 'daily': 15, 'monthly': 300})
        self.assertEqual(plan_limits('paid'), {'plan': 'paid', 'daily': 150, 'monthly': 1000})

    def test_plan_normalization(self):
        self.assertEqual(normalize_plan('Paid'), 'paid')
        self.assertEqual(normalize_plan(' pro '), 'free')
        self.assertEqual(normalize_plan(None), 'free')
        self.assertEqual(plan_limits(None)['plan'], 'free')

    def test_env_overrides_are_read_at_call_time(self):
        with with_env(USAGE_FREE_DAILY_LIMIT='7'):
            self.assertEqual(plan_limits('free')['daily'], 7)

    def test_invalid_env_value_falls_back_to_default(self):
        with with_env(USAGE_FREE_DAILY_LIMIT='not-a-number'):
            self.assertEqual(plan_limits('free')['daily'], 15)
        with with_env(USAGE_FREE_DAILY_LIMIT='0'):
            self.assertEqual(plan_limits('free')['daily'], 15)

    def test_rate_limit_defaults_to_five(self):
        with with_env():
            self.assertEqual(rate_limit_per_minute(), DEFAULT_RATE_LIMIT)
        with with_env(USAGE_RATE_LIMIT_PER_MINUTE='9'):
            self.assertEqual(rate_limit_per_minute(), 9)


class ChatLimitTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.env = with_env()
        self.env.start()
        self.addCleanup(self.env.stop)

        self.client = APIClient()
        self.user = User.objects.create_user(
            username='quota_user', password='pass1234', plan_tier='free'
        )
        self.client.force_authenticate(self.user)

        ai_patcher = patch('api.views.get_ai_service', return_value=FakeChatService())
        self.mock_ai = ai_patcher.start()
        self.addCleanup(ai_patcher.stop)

    def set_response(self, **event_fields):
        """Swap in a different complete event; no args = a normal real answer."""
        if event_fields:
            self.mock_ai.return_value = FakeChatService({'type': 'complete', **event_fields})
        else:
            self.mock_ai.return_value = FakeChatService()

    def chat(self):
        response = self.client.post(
            '/api/chat/',
            {'message': 'What is gravity?', 'context': {'grade': '10'}, 'model': 'deepseek-v3'},
            format='json',
        )
        if response.status_code == 200:
            consume(response)
        return response

    def counter(self):
        return UsageCounter.objects.get(key=f'u:{self.user.pk}')

    def assertNoNumbersLeaked(self, response):
        payload = response.json()
        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            set(payload), {'error', 'limit_type', 'plan'},
            '429 body must only say which limit hit — never how many',
        )
        self.assertFalse(
            any(character.isdigit() for character in json.dumps(payload)),
            f'limit numbers leaked to the client: {payload}',
        )
        return payload


class DailyQuotaTests(ChatLimitTestCase):
    @with_env(USAGE_FREE_DAILY_LIMIT='2', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_free_user_blocked_after_daily_limit(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 200)

        payload = self.assertNoNumbersLeaked(self.chat())
        self.assertEqual(payload['limit_type'], 'daily')
        self.assertEqual(payload['plan'], 'free')

    @with_env(USAGE_PAID_DAILY_LIMIT='2', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_paid_user_uses_paid_limits(self):
        self.user.plan_tier = 'paid'
        self.user.save(update_fields=['plan_tier'])

        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 200)

        payload = self.assertNoNumbersLeaked(self.chat())
        self.assertEqual(payload['limit_type'], 'daily')
        self.assertEqual(payload['plan'], 'paid')

    @with_env(USAGE_FREE_DAILY_LIMIT='1', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_daily_limit_resets_24h_after_it_was_reached(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 429)

        counter = self.counter()
        self.assertIsNotNone(counter.daily_limit_reached_at)

        # Not yet — still inside the 24h cooldown.
        counter.daily_limit_reached_at = timezone.now() - timedelta(hours=23)
        counter.save(update_fields=['daily_limit_reached_at'])
        self.assertEqual(self.chat().status_code, 429)

        # Cooldown finished: fresh quota, counters cleared — so this counts.
        counter.refresh_from_db()
        counter.daily_limit_reached_at = timezone.now() - timedelta(hours=25)
        counter.save(update_fields=['daily_limit_reached_at'])
        self.assertEqual(self.chat().status_code, 200)

        counter.refresh_from_db()
        self.assertEqual(counter.daily_count, 1)
        self.assertIsNotNone(counter.daily_limit_reached_at)
        self.assertEqual(self.chat().status_code, 429)

    @with_env(USAGE_FREE_DAILY_LIMIT='100', USAGE_FREE_MONTHLY_LIMIT='2',
              USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_monthly_limit_blocks_after_daily_quota_is_large(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 200)

        payload = self.assertNoNumbersLeaked(self.chat())
        self.assertEqual(payload['limit_type'], 'monthly')

    @with_env(USAGE_FREE_MONTHLY_LIMIT='100', USAGE_RATE_LIMIT_PER_MINUTE='2')
    def test_rate_limit_blocks_the_third_request(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 200)

        payload = self.assertNoNumbersLeaked(self.chat())
        self.assertEqual(payload['limit_type'], 'rate')

    @with_env(USAGE_RATE_LIMIT_PER_MINUTE='1', USAGE_FREE_DAILY_LIMIT='100')
    def test_rate_limit_counts_cache_hits_too(self):
        self.set_response(
            response='Cached answer.',
            source='Semantic Answer Cache',
            cached=True,
        )
        self.assertEqual(self.chat().status_code, 200)
        payload = self.assertNoNumbersLeaked(self.chat())
        self.assertEqual(payload['limit_type'], 'rate')


class CountingRulesTests(ChatLimitTestCase):
    @with_env(USAGE_FREE_DAILY_LIMIT='1', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_cache_hits_do_not_consume_quota(self):
        self.set_response(response='Cached answer.', source='Semantic Answer Cache', cached=True)

        for _ in range(3):
            self.assertEqual(self.chat().status_code, 200)

        counter = self.counter()
        self.assertEqual(counter.daily_count, 0)
        self.assertIsNone(counter.daily_limit_reached_at)

    @with_env(USAGE_FREE_DAILY_LIMIT='1', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_failed_ai_generation_does_not_consume_quota(self):
        self.set_response(
            response='The AI service is currently unavailable. Please try again in a few minutes.',
            source='Error',
            ai_failed=True,
        )

        for _ in range(3):
            self.assertEqual(self.chat().status_code, 200)

        counter = self.counter()
        self.assertEqual(counter.daily_count, 0)
        self.assertIsNone(counter.daily_limit_reached_at)

        # A real answer still has its full quota available.
        self.set_response()
        self.assertEqual(self.chat().status_code, 200)
        counter.refresh_from_db()
        self.assertEqual(counter.daily_count, 1)
        self.assertIsNotNone(counter.daily_limit_reached_at)
        self.assertEqual(self.chat().status_code, 429)

    @with_env(USAGE_FREE_DAILY_LIMIT='1', USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_blocked_requests_never_consume_quota(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 429)
        self.assertEqual(self.chat().status_code, 429)

        self.assertEqual(self.counter().daily_count, 1)

    @with_env(USAGE_FREE_DAILY_LIMIT='1', USAGE_PAID_DAILY_LIMIT='3',
              USAGE_RATE_LIMIT_PER_MINUTE='50')
    def test_counters_are_isolated_per_user(self):
        self.assertEqual(self.chat().status_code, 200)
        self.assertEqual(self.chat().status_code, 429)

        other_user = User.objects.create_user(
            username='other_quota_user', password='pass1234', plan_tier='paid'
        )
        other_client = APIClient()
        other_client.force_authenticate(other_user)

        for _ in range(3):
            response = other_client.post(
                '/api/chat/',
                {'message': 'Explain photosynthesis', 'context': {'grade': '10'}},
                format='json',
            )
            if response.status_code == 200:
                consume(response)
            self.assertEqual(response.status_code, 200)

        other_payload_blocked = None
        response = other_client.post(
            '/api/chat/', {'message': 'Again', 'context': {'grade': '10'}}, format='json'
        )
        if response.status_code == 200:
            consume(response)
        if response.status_code == 429:
            other_payload_blocked = response.json()

        self.assertIsNotNone(other_payload_blocked)
        self.assertEqual(other_payload_blocked['plan'], 'paid')
        self.assertFalse(any(c.isdigit() for c in json.dumps(other_payload_blocked)))


class AnonymousQuotaTests(TestCase):
    def setUp(self):
        super().setUp()
        self.env = with_env(USAGE_RATE_LIMIT_PER_MINUTE='1', USAGE_FREE_DAILY_LIMIT='100')
        self.env.start()
        self.addCleanup(self.env.stop)

        self.client = APIClient()
        ai_patcher = patch('api.views.get_ai_service', return_value=FakeChatService())
        ai_patcher.start()
        self.addCleanup(ai_patcher.stop)

    @with_env(USAGE_RATE_LIMIT_PER_MINUTE='1', USAGE_FREE_DAILY_LIMIT='100')
    def test_guests_are_tracked_by_ip(self):
        first = self.client.post(
            '/api/chat/', {'message': 'Hi', 'context': {'grade': '10'}}, format='json'
        )
        if first.status_code == 200:
            consume(first)
        self.assertEqual(first.status_code, 200)

        second = self.client.post(
            '/api/chat/', {'message': 'Hi again', 'context': {'grade': '10'}}, format='json'
        )
        if second.status_code == 200:
            consume(second)
        self.assertEqual(second.status_code, 429)
        self.assertEqual(second.json()['limit_type'], 'rate')


class GuardUnitTests(TestCase):
    def test_exception_payload_carries_no_numbers(self):
        exc = UsageLimitExceeded('daily', 'free')
        payload = exc.payload
        self.assertEqual(payload['limit_type'], 'daily')
        self.assertEqual(payload['plan'], 'free')
        self.assertFalse(any(character.isdigit() for character in json.dumps(payload)))

    def test_record_is_idempotent_per_request(self):
        from .usage_limits import ChatUsageGuard

        user = User.objects.create_user(username='guard_user', password='pass1234')
        counter = UsageCounter.objects.create(key=f'u:{user.pk}', user=user)
        guard = ChatUsageGuard(
            key=f'u:{user.pk}',
            plan='free',
            limits={'plan': 'free', 'daily': 15, 'monthly': 300},
        )
        guard.record()
        guard.record()

        counter.refresh_from_db()
        self.assertEqual(counter.daily_count, 1)
        self.assertEqual(counter.monthly_count, 1)
        self.assertIsNotNone(counter.daily_window_start)
        self.assertIsNotNone(counter.monthly_window_start)
