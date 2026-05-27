def get_active_menus() -> dict:
    """
    Returns the correct food and drink menus based on current event mode.
    Always returns a dict — values may be None if no menu holds that role.
    Templates must handle None gracefully.

    Usage in views::

        menus = get_active_menus()
        context['food_menu']  = menus['food']
        context['drink_menu'] = menus['drinks']
        context['event_mode'] = menus['event_mode']
    """
    from apps.events.models import EventDay
    from apps.menu.models import Menu

    event_mode = EventDay.get_current_menu_mode() == 'limited'

    food_role   = 'event_food'   if event_mode else 'default_food'
    drinks_role = 'event_drinks' if event_mode else 'default_drinks'

    return {
        'food':       Menu.objects.filter(role=food_role).first(),
        'drinks':     Menu.objects.filter(role=drinks_role).first(),
        'event_mode': event_mode,
    }
