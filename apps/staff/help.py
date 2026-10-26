"""
Staff portal help: topic list for /staff/help/ and the short tip shown at the
top of each portal page (staff/partials/_page_tip.html).

The full help text lives in templates/staff/help.html, one <section> per topic
id below. Keep the two in sync when adding a topic or a portal page.
"""
from .permissions import MANAGER, STAFF, SUPERUSER

# (topic id, title, minimum tier) in the order shown on the help page.
TOPICS = [
    ('getting-around', 'Getting around the portal', STAFF),
    ('dashboard', 'Dashboard', STAFF),
    ('menu-mode', 'Menu mode (full vs. limited menu)', STAFF),
    ('events', 'Events calendar', STAFF),
    ('menu-items', 'Menu items and photos', STAFF),
    ('menus-explained', 'How menus work', STAFF),
    ('inquiries', 'Event inquiries', MANAGER),
    ('media', 'Media library (photos)', MANAGER),
    ('newsletter', 'Newsletter', MANAGER),
    ('popups', 'Site popups', MANAGER),
    ('reviews', 'Reviews', MANAGER),
    ('colors', 'Color reference', STAFF),
    ('settings', 'Site settings and color schemes', SUPERUSER),
    ('menu-import', 'Import / export (menu and events spreadsheets)', MANAGER),
]

# url_name → (topic id, one-line tip). Every portal page should have an entry.
PAGE_TIPS = {
    'dashboard': ('dashboard', "Today's status at a glance — menu mode, events, and anything waiting on you."),
    'menu_mode': ('menu-mode', 'Automatic follows the events calendar. Use a Force option only to override it, and switch back to Automatic afterwards.'),
    'events': ('events', 'Home games switch the site to the limited menu automatically. Away games stay on the full menu unless you turn limited menu on.'),
    'event_add': ('events', 'Set a game time so the limited menu starts a couple of hours before kickoff; leave it blank for all day.'),
    'event_edit': ('events', 'Untick “Limited menu” for events that keep full service; untick “Active” to hide an event without deleting it.'),
    'menu_item_list': ('menu-items', 'Find an item by name or filter, then use Images to choose which photos it shows.'),
    'menu_item_images': ('menu-items', 'Pick photos from the media library and mark one as the item’s main (primary) photo.'),
    'inquiries': ('inquiries', 'New private-event requests arrive here and by email. Mark them Contacted once you have reached out, Closed when done. Likely spam is filed under Spam.'),
    'media_library': ('media', 'New photos start hidden. Click Show on a photo to publish it to the public gallery.'),
    'media_upload': ('media', 'Give each photo a clear name and a short description (alt text) for visitors using screen readers.'),
    'media_edit': ('media', 'Name and category are for finding photos; the caption is what visitors see in the gallery.'),
    'newsletter': ('newsletter', 'Drafts can be edited until they are sent. Use Duplicate on a sent newsletter to start a new one.'),
    'newsletter_compose': ('newsletter', 'Write and save as a draft first — nothing is sent until you press Send Now on the next page.'),
    'newsletter_edit': ('newsletter', 'Write and save as a draft first — nothing is sent until you press Send Now on the next page.'),
    'newsletter_detail': ('newsletter', 'Check the preview carefully. Send Now goes to every confirmed subscriber and cannot be undone.'),
    'popups': ('popups', 'Only one popup can be live at a time — activating one switches the others off.'),
    'popup_add': ('popups', 'Popups start switched off. Save, then activate it from the list when you are ready.'),
    'popup_edit': ('popups', 'Changes to the live popup show on the site straight away.'),
    'reviews': ('reviews', 'Imported reviews arrive Hidden. Make the ones to show Active; the first three Featured appear on the homepage.'),
    'colors': ('colors', 'The site’s named theme colors, for reference when choosing banner and panel colors.'),
    'settings': ('settings', 'Changes here affect the whole site immediately.'),
    'color_scheme_add': ('settings', 'Color schemes style promo menus and popups. Only one can be the default.'),
    'color_scheme_edit': ('settings', 'Changing a scheme restyles every promo menu and popup that uses it.'),
    'menu_import': ('menu-import', 'Export a file (Whole menu covers the menu on one sheet; Events is the calendar), edit it in Excel or Google Sheets, save as CSV and upload it here. Nothing is saved until you confirm the preview.'),
    'menu_import_preview': ('menu-import', 'Check every highlighted change. Confirm saves the whole file at once; any error means nothing is saved.'),
}
