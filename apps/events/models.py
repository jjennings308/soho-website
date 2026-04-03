from django.db import models
from django.utils import timezone


class EventDay(models.Model):
    """
    A calendar entry representing a day (or part of a day) where the venue
    operates under special conditions — game days, private parties, live music,
    holidays, etc.

    Limited menu mode:
        When limited_menu=True, the menu view filters to only items flagged
        available_game_day=True on their MenuItemCategoryAssignment record.

    Automatic activation:
        If game_time is set, limited menu mode activates
        `limited_menu_lead_hours` before game_time.
        If game_time is blank, limited menu mode is active all day.

    Manual overrides (on SiteSettings):
        force_game_day_mode  — forces limited menu on regardless of calendar
        force_full_menu      — forces full menu on regardless of calendar
        force_full_menu takes precedence over force_game_day_mode.
    """

    # ── Type ──────────────────────────────────────────────────────────────────
    TYPE_CHOICES = [
        ('game',          'Game Day'),
        ('private_party', 'Private Party'),
        ('live_music',    'Live Music'),
        ('holiday',       'Holiday'),
        ('other',         'Other'),
    ]

    # ── Team (relevant for game type only) ────────────────────────────────────
    TEAM_CHOICES = [
        ('pirates',  'Pittsburgh Pirates'),
        ('steelers', 'Pittsburgh Steelers'),
        ('penguins', 'Pittsburgh Penguins'),
        ('other',    'Other'),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    date = models.DateField(
        help_text="Date of the event."
    )
    event_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='game',
        help_text="Type of event. Controls labeling and future type-specific behavior."
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text=(
            "Optional display label shown on the site, e.g. 'Pirates vs. Cubs' "
            "or 'Private Event — Patio Reserved'. Leave blank to use the event "
            "type display name."
        )
    )

    # ── Game-specific fields ──────────────────────────────────────────────────
    team = models.CharField(
        max_length=20,
        choices=TEAM_CHOICES,
        blank=True,
        help_text="Relevant for game day events only."
    )
    game_time = models.TimeField(
        blank=True,
        null=True,
        help_text=(
            "Start time of the game or event. Used to calculate when limited "
            "menu mode activates (see limited_menu_lead_hours). Leave blank to "
            "activate limited menu all day."
        )
    )
    limited_menu_lead_hours = models.PositiveIntegerField(
        default=2,
        help_text=(
            "How many hours before game_time to activate limited menu mode. "
            "Default is 2 hours. Ignored if game_time is blank (all-day)."
        )
    )

    # ── Menu behavior ─────────────────────────────────────────────────────────
    limited_menu = models.BooleanField(
        default=True,
        help_text=(
            "Activate limited menu mode for this event. Uncheck for events "
            "that don't restrict the menu (e.g. live music with full service)."
        )
    )

    # ── Control ───────────────────────────────────────────────────────────────
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Uncheck to disable this event without deleting it — useful for "
            "cancelled or rescheduled games."
        )
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date', 'game_time']
        verbose_name = 'Event Day'
        verbose_name_plural = 'Event Days'
        indexes = [
            models.Index(fields=['date', 'is_active']),
        ]

    def __str__(self):
        label = self.display_label
        return f"{self.date} — {label}"

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def display_label(self):
        """
        Returns the label if set, otherwise falls back to the event type
        display name (and team name for game days).
        """
        if self.label:
            return self.label
        if self.event_type == 'game' and self.team:
            return f"{self.get_event_type_display()} — {self.get_team_display()}"
        return self.get_event_type_display()

    @property
    def is_limited_menu_active(self):
        """
        Returns True if limited menu mode should currently be active for
        this event, based on the current time and limited_menu_lead_hours.

        Does NOT check SiteSettings overrides — that logic lives in the view
        via EventDay.get_current_menu_mode().
        """
        if not self.is_active or not self.limited_menu:
            return False
        if self.game_time is None:
            return True
        now = timezone.localtime(timezone.now())
        if now.date() != self.date:
            return False
        from datetime import datetime, timedelta
        activation_dt = datetime.combine(
            self.date,
            self.game_time,
        ) - timedelta(hours=self.limited_menu_lead_hours)
        activation_dt = timezone.make_aware(activation_dt)
        return now >= activation_dt

    # ── Class methods ─────────────────────────────────────────────────────────

    @classmethod
    def get_current_menu_mode(cls):
        """
        Returns 'limited' or 'full' based on today's events and SiteSettings
        overrides.

        Resolution order:
            1. SiteSettings.force_full_menu      → 'full'
            2. SiteSettings.force_game_day_mode  → 'limited'
            3. Active EventDay with limited_menu_active today → 'limited'
            4. Default                            → 'full'

        Usage in views:
            from apps.events.models import EventDay
            menu_mode = EventDay.get_current_menu_mode()
            context['limited_menu'] = (menu_mode == 'limited')
        """
        # Import here to avoid circular import; SiteSettings is in apps.core
        try:
            from apps.core.models import SiteSettings
            settings = SiteSettings.load()
            if settings.force_full_menu:
                return 'full'
            if settings.force_game_day_mode:
                return 'limited'
        except Exception:
            pass

        today = timezone.localdate()
        events = cls.objects.filter(date=today, is_active=True, limited_menu=True)
        for event in events:
            if event.is_limited_menu_active:
                return 'limited'

        return 'full'

    @classmethod
    def get_todays_events(cls):
        """
        Returns all active EventDay records for today, ordered by game_time.
        Useful for displaying event notices on the home page or menu page.
        """
        today = timezone.localdate()
        return cls.objects.filter(date=today, is_active=True).order_by('game_time')
