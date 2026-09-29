"""Chat usage quotas and rate limiting for Noya.

Business rules:

============  ==============  ==============
Plan          Daily chats     Monthly chats
============  ==============  ==============
free          15              300
paid          150             1000
============  ==============  ==============

Both plans are additionally capped at 5 chat requests per minute so one
client can never hammer the AI providers.

* A chat only counts when it produced an answer that was **neither a cache
  hit nor a failed AI generation**.
* Blocked requests never consume quota.
* When a quota is used up it stays blocked for 24h (daily) / 30 days
  (monthly) measured from the moment the limit was reached, then resets.
* The exact numbers are intentionally never sent to clients — they only
  receive ``daily`` / ``monthly`` / ``rate`` as the limit that stopped them.

All numbers are env-tunable (see .env.example) which also keeps tests fast.
"""

from __future__ import annotations

import os
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import UsageCounter

DAILY_RESET = timedelta(hours=24)
MONTHLY_RESET = timedelta(days=30)
RATE_RESET = timedelta(minutes=1)

_PERIODS = (('daily', DAILY_RESET), ('monthly', MONTHLY_RESET))

DEFAULT_LIMITS = {
    'free': {'daily': 15, 'monthly': 300},
    'paid': {'daily': 150, 'monthly': 1000},
}
DEFAULT_RATE_LIMIT = 5


class UsageLimitExceeded(Exception):
    """Raised before a chat starts when a quota or the rate limit blocks it."""

    def __init__(self, limit_type: str, plan: str):
        self.limit_type = limit_type  # 'daily' | 'monthly' | 'rate'
        self.plan = plan
        messages = {
            'daily': 'Daily limit reached.',
            'monthly': 'Monthly limit reached.',
            'rate': 'Too many requests.',
        }
        super().__init__(messages.get(limit_type, 'Usage limit reached.'))

    @property
    def payload(self) -> dict:
        """Response body — deliberately carries no numbers."""
        return {
            'error': str(self),
            'limit_type': self.limit_type,
            'plan': self.plan,
        }


def _int_env(name: str, default: int) -> int:
    try:
        value = int(str(os.getenv(name, '') or '').strip() or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def normalize_plan(plan_tier) -> str:
    return 'paid' if str(plan_tier or 'free').strip().lower() == 'paid' else 'free'


def plan_limits(plan_tier) -> dict:
    plan = normalize_plan(plan_tier)
    defaults = DEFAULT_LIMITS[plan]
    return {
        'plan': plan,
        'daily': _int_env(f'USAGE_{plan.upper()}_DAILY_LIMIT', defaults['daily']),
        'monthly': _int_env(f'USAGE_{plan.upper()}_MONTHLY_LIMIT', defaults['monthly']),
    }


def rate_limit_per_minute() -> int:
    return _int_env('USAGE_RATE_LIMIT_PER_MINUTE', DEFAULT_RATE_LIMIT)


def identity_for(request, user=None):
    """Stable key for a caller: authenticated users by id, guests by IP."""
    if user is not None and getattr(user, 'is_authenticated', False):
        return f'u:{user.pk}', user
    forwarded = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    ip = forwarded or str(request.META.get('REMOTE_ADDR') or 'unknown').strip()
    return f'ip:{ip}', None


def _refresh_period(counter: UsageCounter, prefix: str, reset_window: timedelta, now) -> None:
    """Clear an expired lock, or roll over an expired counting window."""
    reached_at = getattr(counter, f'{prefix}_limit_reached_at')
    window_start = getattr(counter, f'{prefix}_window_start')
    count = getattr(counter, f'{prefix}_count')

    if reached_at is not None and now >= reached_at + reset_window:
        # Cooldown finished — the user gets a fresh quota.
        reached_at = None
        window_start = None
        count = 0
    elif reached_at is None and window_start is not None and now >= window_start + reset_window:
        # Window elapsed without hitting the limit — start a new one.
        window_start = None
        count = 0

    setattr(counter, f'{prefix}_count', count)
    setattr(counter, f'{prefix}_window_start', window_start)
    setattr(counter, f'{prefix}_limit_reached_at', reached_at)


class ChatUsageGuard:
    """Reservation for one chat request; ``record()`` charges it to quota."""

    def __init__(self, key: str, plan: str, limits: dict):
        self.key = key
        self.plan = plan
        self.limits = limits
        self._recorded = False

    def record(self) -> None:
        """Charge one counted chat (non-cache, successful answer).

        Idempotent per request and safe to call from inside the SSE stream.
        """
        if self._recorded:
            return
        self._recorded = True

        now = timezone.now()
        with transaction.atomic():
            counter = (
                UsageCounter.objects
                .select_for_update()
                .filter(key=self.key)
                .first()
            )
            if counter is None:
                return

            for prefix, reset_window in _PERIODS:
                _refresh_period(counter, prefix, reset_window, now)

                window_attr = f'{prefix}_window_start'
                if getattr(counter, window_attr) is None:
                    setattr(counter, window_attr, now)

                count = getattr(counter, f'{prefix}_count') + 1
                setattr(counter, f'{prefix}_count', count)

                reached_attr = f'{prefix}_limit_reached_at'
                if count >= self.limits[prefix] and getattr(counter, reached_attr) is None:
                    # The limit was reached *now* — lock it for the full window.
                    setattr(counter, reached_attr, now)

            counter.save()


def reserve_chat_request(request, user=None) -> ChatUsageGuard:
    """Pre-flight a chat request: rate limit first, then daily/monthly quota.

    Consumes one per-minute slot. Raises :class:`UsageLimitExceeded` when the
    caller is blocked — the caller should answer with HTTP 429 and the
    exception's ``payload``.
    """
    key, key_user = identity_for(request, user)
    limits = plan_limits(getattr(key_user, 'plan_tier', 'free') if key_user else 'free')
    now = timezone.now()
    blocked = None

    with transaction.atomic():
        counter, _created = (
            UsageCounter.objects
            .select_for_update()
            .get_or_create(key=key, defaults={'user': key_user})
        )
        if key_user and counter.user_id is None:
            counter.user = key_user

        # 1) Per-minute rate limit — every attempt counts (overload guard).
        if counter.minute_window_start is None or now >= counter.minute_window_start + RATE_RESET:
            counter.minute_window_start = now
            counter.minute_count = 0

        if counter.minute_count >= rate_limit_per_minute():
            blocked = 'rate'
        else:
            counter.minute_count += 1

            # 2) Daily / monthly quotas.
            for prefix, reset_window in _PERIODS:
                _refresh_period(counter, prefix, reset_window, now)
                if getattr(counter, f'{prefix}_limit_reached_at') is not None:
                    blocked = prefix
                    break

        counter.save()

    if blocked:
        raise UsageLimitExceeded(blocked, limits['plan'])

    return ChatUsageGuard(key=key, plan=limits['plan'], limits=limits)
