# core/utils.py

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
