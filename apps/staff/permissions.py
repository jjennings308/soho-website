"""
Staff portal access tiers (see CLAUDE.md "Access tiers").

    Tier 2 — any is_staff user: read-only views of the dashboard, menu mode,
             events and menu items.
    Tier 1 — is_staff and in the "Staff Manager" group: everything in the
             portal except the superuser-only settings pages.
    Superuser — everything, including Site Settings and color schemes.

Each view declares its level with StaffRequiredMixin.staff_access.
"""
from django.utils.functional import SimpleLazyObject

MANAGER_GROUP = 'Staff Manager'

# staff_access levels
STAFF = 'staff'          # Tier 2 may view (GET); changes need a manager
MANAGER = 'manager'      # Tier 1 only, for every method
SUPERUSER = 'superuser'  # superusers only


def is_manager(user):
    """Tier 1 or above. Cached on the user object for the request."""
    if not (user.is_authenticated and user.is_staff):
        return False
    if user.is_superuser:
        return True
    if not hasattr(user, '_is_staff_manager'):
        user._is_staff_manager = user.groups.filter(name=MANAGER_GROUP).exists()
    return user._is_staff_manager


def has_access(user, level, method):
    if not (user.is_authenticated and user.is_staff):
        return False
    if level == SUPERUSER:
        return user.is_superuser
    if level == STAFF and method in ('GET', 'HEAD', 'OPTIONS'):
        return True
    return is_manager(user)


def staff_access(request):
    """Context processor: `staff_is_manager` for hiding controls by tier."""
    return {'staff_is_manager': SimpleLazyObject(lambda: is_manager(request.user))}
