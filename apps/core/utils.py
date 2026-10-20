# core/utils.py

import time

from django.core.cache import cache

from apps.content.models import ContentSlot


def get_block_body(slug):
    try:
        return ContentSlot.objects.get(slug=slug).get_active_block()
    except ContentSlot.DoesNotExist:
        return None


def get_banner(slug):
    """
    Fetch an active Banner by slug and return the Banner instance,
    with content_group and images prefetched. Returns None if not found.
    """
    from apps.core.models import Banner

    return (
        Banner.objects
        .filter(slug=slug, is_active=True)
        .select_related('content_group')
        .prefetch_related('content_group__slots__blocks', 'images__media_item')
        .first()
    )


def get_panel_side(slug):
    """
    Fetch an active PanelSide by slug and return the PanelSide instance,
    with content_group and image prefetched. Returns None if not found.
    """
    from apps.core.models import PanelSide

    return (
        PanelSide.objects
        .filter(slug=slug, is_active=True)
        .select_related('content_group', 'image')
        .prefetch_related('content_group__slots__blocks')
        .first()
    )


HONEYPOT_FIELD = 'hp_check'  # deliberately not a name browsers autofill


def honeypot_tripped(request):
    """
    True if the hidden honeypot field (core/partials/_honeypot.html) was
    filled in. Real visitors never see it; naive bots fill every input.
    Callers should return their normal success response without acting,
    so bots get no signal.
    """
    return bool(request.POST.get(HONEYPOT_FIELD, '').strip())


def client_ip(request):
    """
    The visitor's IP. Behind nginx REMOTE_ADDR is always the proxy, so use
    the right-most X-Forwarded-For entry — the one nginx appended, which the
    client cannot spoof.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '')


_clock = time.time  # module-level so tests can patch it without touching the cache backend


def is_throttled(key, limit, window):
    """
    Record one hit against `key` and return True once more than `limit` hits
    have landed within a fixed `window` (seconds) starting at the first hit.

    Stores (count, reset_at) rather than using cache.incr(), because
    BaseCache.incr() re-saves with the default timeout and would keep
    extending the window. Not atomic — fine for spam limiting.
    """
    cache_key = f'throttle:{key}'
    now = _clock()
    count, reset_at = cache.get(cache_key) or (0, now + window)
    if reset_at <= now:
        count, reset_at = 0, now + window
    count += 1
    cache.set(cache_key, (count, reset_at), timeout=max(1, int(reset_at - now)))
    return count > limit
