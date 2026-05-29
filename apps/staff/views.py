import re
import shutil
from io import StringIO
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.core.management import call_command
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View


def _prepare_newsletter_html(html, base_url):
    """Make newsletter HTML safe for email clients."""
    # Relative media URLs → absolute so email clients can load images
    html = html.replace('src="/media/', f'src="{base_url}media/')
    html = html.replace('href="/media/', f'href="{base_url}media/')

    # CKEditor5 wraps resized images in <figure style="width:X%">.
    # Email clients ignore figure styles, so move width onto the img tag.
    def unwrap_figure(m):
        figure_attrs = m.group(1)
        content = m.group(2)
        w = re.search(r'width\s*:\s*([\d.]+%)', figure_attrs)
        width_style = f'width:{w.group(1)};' if w else ''
        content = re.sub(
            r'<img\b',
            f'<img style="{width_style}max-width:100%;height:auto;"',
            content,
            count=1,
        )
        return content

    html = re.sub(r'<figure\b([^>]*)>(.*?)</figure>', unwrap_figure, html, flags=re.DOTALL | re.IGNORECASE)
    return html

from apps.core.models import ColorScheme, EventInquiry, Review, SitePopup, SiteSettings
from apps.events.models import EventDay
from apps.media.models import MediaCategory, MediaItem
from apps.members.models import Newsletter, SoHoMember
from apps.menu.models import Menu

from .forms import ColorSchemeForm, EventForm, MediaItemEditForm, MediaItemUploadForm, NewsletterForm, PopupForm, SiteSettingsForm


class StaffRequiredMixin(LoginRequiredMixin):
    login_url = '/staff/login/'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.is_staff:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


# ── Auth ──────────────────────────────────────────────────────────────────────

class StaffLoginView(LoginView):
    template_name = 'staff/login.html'
    redirect_authenticated_user = True

    def get_success_url(self):
        return '/staff/'


class StaffLogoutView(LogoutView):
    next_page = '/staff/login/'


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardView(StaffRequiredMixin, View):
    def get(self, request):
        menu_mode = EventDay.get_current_menu_mode()
        today_events = EventDay.get_todays_events()
        upcoming = (
            EventDay.objects
            .filter(date__gt=timezone.localdate(), is_active=True)
            .order_by('date', 'game_time')[:5]
        )
        site = SiteSettings.load()
        subscriber_count = SoHoMember.objects.filter(is_active=True, is_email_subscribed=True).count()
        draft_count = Newsletter.objects.filter(sent_at__isnull=True).count()
        unpublished_count = MediaItem.objects.filter(owner_type='staff', is_published=False).count()
        new_inquiry_count = EventInquiry.objects.filter(status='new').count()
        active_popup = SitePopup.get_active()
        promo_menus = Menu.objects.filter(menu_type='promo').select_related('color_scheme').order_by('title')

        specials_menus = []
        for m in Menu.objects.filter(menu_type='weekly_specials').order_by('-valid_from'):
            days = (timezone.now() - m.updated_at).days
            if days <= 7:
                badge_class, badge_label = 'sp-pill--green', f'Updated {days}d ago'
            elif days <= 14:
                badge_class, badge_label = 'sp-pill--gold', f'Updated {days}d ago'
            else:
                badge_class, badge_label = 'sp-pill--red', f'Stale — {days}d ago'
            specials_menus.append({
                'menu': m,
                'badge_class': badge_class,
                'badge_label': badge_label,
            })

        return render(request, 'staff/dashboard.html', {
            'menu_mode': menu_mode,
            'today_events': today_events,
            'upcoming': upcoming,
            'site': site,
            'subscriber_count': subscriber_count,
            'draft_count': draft_count,
            'unpublished_count': unpublished_count,
            'new_inquiry_count': new_inquiry_count,
            'active_popup': active_popup,
            'promo_menus': promo_menus,
            'specials_menus': specials_menus,
        })


# ── Menu Mode ─────────────────────────────────────────────────────────────────

class MenuModeView(StaffRequiredMixin, View):
    def get(self, request):
        site = SiteSettings.load()
        menu_mode = EventDay.get_current_menu_mode()
        return render(request, 'staff/menu_mode.html', {
            'site': site,
            'menu_mode': menu_mode,
        })

    def post(self, request):
        site = SiteSettings.load()
        action = request.POST.get('action')
        if action == 'force_full':
            site.force_full_menu = True
            site.force_game_day_mode = False
        elif action == 'force_game_day':
            site.force_full_menu = False
            site.force_game_day_mode = True
        elif action == 'auto':
            site.force_full_menu = False
            site.force_game_day_mode = False
        site.save(update_fields=['force_full_menu', 'force_game_day_mode'])
        return redirect('staff:menu_mode')


# ── Events ────────────────────────────────────────────────────────────────────

class EventListView(StaffRequiredMixin, View):
    def get(self, request):
        upcoming = (
            EventDay.objects
            .filter(date__gt=timezone.localdate())
            .order_by('date', 'game_time')
        )
        past = (
            EventDay.objects
            .filter(date__lt=timezone.localdate())
            .order_by('-date', 'game_time')[:20]
        )
        return render(request, 'staff/events/list.html', {
            'upcoming': upcoming,
            'past': past,
        })


class EventAddView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'staff/events/form.html', {'form': EventForm(), 'title': 'Add Event'})

    def post(self, request):
        form = EventForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('staff:events')
        return render(request, 'staff/events/form.html', {'form': form, 'title': 'Add Event'})


class EventEditView(StaffRequiredMixin, View):
    def get(self, request, pk):
        event = get_object_or_404(EventDay, pk=pk)
        return render(request, 'staff/events/form.html', {
            'form': EventForm(instance=event),
            'event': event,
            'title': 'Edit Event',
        })

    def post(self, request, pk):
        event = get_object_or_404(EventDay, pk=pk)
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            return redirect('staff:events')
        return render(request, 'staff/events/form.html', {
            'form': form,
            'event': event,
            'title': 'Edit Event',
        })


class EventToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(EventDay, pk=pk)
        event.is_active = not event.is_active
        event.save(update_fields=['is_active'])
        return redirect('staff:events')


class EventDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        event = get_object_or_404(EventDay, pk=pk)
        event.delete()
        return redirect('staff:events')


# ── Media Library ─────────────────────────────────────────────────────────────

MEDIA_PAGE_SIZE = 48  # items per page in the library grid


class MediaLibraryView(StaffRequiredMixin, View):
    def get(self, request):
        qs = MediaItem.objects.filter(owner_type='staff').select_related('category')

        # Filters
        category_slug = request.GET.get('category', '')
        pub_filter    = request.GET.get('pub', '')
        search        = request.GET.get('q', '').strip()

        if category_slug == 'none':
            qs = qs.filter(category__isnull=True)
        elif category_slug:
            qs = qs.filter(category__slug=category_slug)
        if pub_filter == 'published':
            qs = qs.filter(is_published=True)
        elif pub_filter == 'hidden':
            qs = qs.filter(is_published=False)
        if search:
            qs = qs.filter(name__icontains=search)

        qs = qs.order_by('category__display_order', 'category__name', 'display_order', 'name')

        # Simple pagination
        try:
            page = max(1, int(request.GET.get('page', 1)))
        except (ValueError, TypeError):
            page = 1
        total   = qs.count()
        offset  = (page - 1) * MEDIA_PAGE_SIZE
        items   = qs[offset: offset + MEDIA_PAGE_SIZE]
        pages   = max(1, (total + MEDIA_PAGE_SIZE - 1) // MEDIA_PAGE_SIZE)

        categories = MediaCategory.objects.order_by('display_order', 'name')

        return render(request, 'staff/media/list.html', {
            'items':         items,
            'categories':    categories,
            'category_slug': category_slug,
            'pub_filter':    pub_filter,
            'search':        search,
            'page':          page,
            'pages':         pages,
            'total':         total,
        })


class MediaUploadView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'staff/media/upload.html', {'form': MediaItemUploadForm()})

    def post(self, request):
        form = MediaItemUploadForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.owner_type   = 'staff'
            item.media_type   = 'image'
            item.is_approved  = True
            item.uploaded_by  = request.user
            item.save()
            messages.success(request, f'"{item.name}" uploaded successfully.')
            return redirect('staff:media_library')
        return render(request, 'staff/media/upload.html', {'form': form})


class MediaImportView(StaffRequiredMixin, View):
    def post(self, request):
        out = StringIO()
        call_command('import_media_files', stdout=out)
        lines = [l for l in out.getvalue().strip().splitlines() if l.strip()]
        messages.success(request, lines[-1] if lines else 'Import complete.')
        return redirect('staff:media_library')


class MediaToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(MediaItem, pk=pk, owner_type='staff')
        item.is_published = not item.is_published
        item.save(update_fields=['is_published'])
        # Return to the same page the user was on
        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER') or reverse('staff:media_library')
        return redirect(next_url)


class MediaDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        from django.conf import settings
        from django.db.models import ProtectedError
        item = get_object_or_404(MediaItem, pk=pk, owner_type='staff')
        try:
            # Move file to deleted archive before removing the DB record.
            # The import command skips gallery/deleted/ so re-importing won't
            # resurrect these files. Staff can review them there before a
            # permanent wipe.
            if item.file:
                src = Path(settings.MEDIA_ROOT) / item.file.name
                if src.exists():
                    deleted_dir = Path(settings.MEDIA_ROOT) / 'gallery' / 'deleted'
                    deleted_dir.mkdir(parents=True, exist_ok=True)
                    dest = deleted_dir / src.name
                    # Avoid overwriting a file with the same name
                    if dest.exists():
                        dest = deleted_dir / f"{src.stem}_{item.pk}{src.suffix}"
                    shutil.move(str(src), str(dest))
            item.delete()
            messages.success(request, f'"{item.name}" moved to deleted archive and removed from library.')
        except ProtectedError as exc:
            # Build a human-readable list of what's referencing this item
            refs = ', '.join(
                f"{obj._meta.verbose_name} #{obj.pk}"
                for obj in list(exc.protected_objects)[:5]
            )
            messages.error(
                request,
                f'Cannot delete "{item.name}" — it is used by: {refs}. '
                'Remove those assignments first, then delete.'
            )
        next_url = request.POST.get('next') or reverse('staff:media_library')
        return redirect(next_url)


class MediaEditView(StaffRequiredMixin, View):
    def _ctx(self, form, item, back_url):
        return {'form': form, 'item': item, 'back_url': back_url}

    def get(self, request, pk):
        item = get_object_or_404(MediaItem, pk=pk, owner_type='staff')
        back_url = request.GET.get('next') or reverse('staff:media_library')
        return render(request, 'staff/media/edit.html', self._ctx(MediaItemEditForm(instance=item), item, back_url))

    def post(self, request, pk):
        item = get_object_or_404(MediaItem, pk=pk, owner_type='staff')
        back_url = request.POST.get('next') or reverse('staff:media_library')
        form = MediaItemEditForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, f'"{item.name}" updated.')
            return redirect(back_url)
        return render(request, 'staff/media/edit.html', self._ctx(form, item, back_url))


# ── Newsletter ────────────────────────────────────────────────────────────────

class NewsletterListView(StaffRequiredMixin, View):
    def get(self, request):
        newsletters = Newsletter.objects.order_by('-created_at')
        return render(request, 'staff/newsletter/list.html', {'newsletters': newsletters})


class NewsletterComposeView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'staff/newsletter/compose.html', {'form': NewsletterForm()})

    def post(self, request):
        form = NewsletterForm(request.POST)
        if form.is_valid():
            newsletter = form.save()
            return redirect('staff:newsletter_detail', pk=newsletter.pk)
        return render(request, 'staff/newsletter/compose.html', {'form': form})


class NewsletterDetailView(StaffRequiredMixin, View):
    def get(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk)
        subscriber_count = SoHoMember.objects.filter(is_active=True, is_email_subscribed=True).count()
        return render(request, 'staff/newsletter/detail.html', {
            'newsletter': newsletter,
            'subscriber_count': subscriber_count,
        })


class NewsletterEditView(StaffRequiredMixin, View):
    def get(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk, sent_at__isnull=True)
        return render(request, 'staff/newsletter/compose.html', {
            'form': NewsletterForm(instance=newsletter),
            'newsletter': newsletter,
            'title': 'Edit Draft',
        })

    def post(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk, sent_at__isnull=True)
        form = NewsletterForm(request.POST, instance=newsletter)
        if form.is_valid():
            form.save()
            return redirect('staff:newsletter_detail', pk=newsletter.pk)
        return render(request, 'staff/newsletter/compose.html', {
            'form': form,
            'newsletter': newsletter,
            'title': 'Edit Draft',
        })


class NewsletterSendView(StaffRequiredMixin, View):
    def post(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk)
        if not newsletter.is_draft:
            return redirect('staff:newsletter_detail', pk=pk)

        members = list(
            SoHoMember.objects.filter(is_active=True, is_email_subscribed=True)
        )

        if members:
            base_url = request.build_absolute_uri('/')
            for member in members:
                unsubscribe_url = request.build_absolute_uri(
                    reverse('members:unsubscribe', kwargs={'token': member.unsubscribe_token})
                )
                html_body = render_to_string('members/emails/newsletter.html', {
                    'newsletter': newsletter,
                    'member': member,
                    'unsubscribe_url': unsubscribe_url,
                })
                html_body = _prepare_newsletter_html(html_body, base_url)
                msg = EmailMessage(
                    subject=newsletter.subject,
                    body=html_body,
                    from_email=None,
                    to=[member.email],
                )
                msg.content_subtype = 'html'
                msg.send(fail_silently=True)

        newsletter.sent_at = timezone.now()
        newsletter.recipient_count = len(members)
        newsletter.sent_by = request.user
        newsletter.save(update_fields=['sent_at', 'recipient_count', 'sent_by'])

        return redirect('staff:newsletter_detail', pk=pk)


class NewsletterCopyView(StaffRequiredMixin, View):
    def post(self, request, pk):
        original = get_object_or_404(Newsletter, pk=pk)
        copy = Newsletter.objects.create(
            subject=f'Copy of {original.subject}',
            body=original.body,
        )
        return redirect('staff:newsletter_edit', pk=copy.pk)


class NewsletterDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk, sent_at__isnull=True)
        newsletter.delete()
        return redirect('staff:newsletter')


# ── Event Inquiries ───────────────────────────────────────────────────────────

class InquiryListView(StaffRequiredMixin, View):
    def get(self, request):
        status_filter = request.GET.get('status', '')
        qs = EventInquiry.objects.all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        counts = {
            'total': EventInquiry.objects.count(),
            'new': EventInquiry.objects.filter(status='new').count(),
            'contacted': EventInquiry.objects.filter(status='contacted').count(),
            'closed': EventInquiry.objects.filter(status='closed').count(),
        }
        return render(request, 'staff/inquiries/list.html', {
            'inquiries': qs,
            'status_filter': status_filter,
            'counts': counts,
        })


class InquiryStatusView(StaffRequiredMixin, View):
    def post(self, request, pk):
        inquiry = get_object_or_404(EventInquiry, pk=pk)
        status = request.POST.get('status')
        if status in ('new', 'contacted', 'closed'):
            inquiry.status = status
            inquiry.save(update_fields=['status'])
        return redirect(request.META.get('HTTP_REFERER', 'staff:inquiries'))


class InquiryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        inquiry = get_object_or_404(EventInquiry, pk=pk)
        inquiry.delete()
        return redirect('staff:inquiries')


# ── Popups ────────────────────────────────────────────────────────────────────

class StaffSettingsView(StaffRequiredMixin, View):
    def _get_settings(self):
        return SiteSettings.objects.first()

    def get(self, request):
        site = self._get_settings()
        return render(request, 'staff/settings.html', {
            'form': SiteSettingsForm(instance=site),
            'color_schemes': ColorScheme.objects.order_by('-is_default', 'name'),
        })

    def post(self, request):
        site = self._get_settings()
        form = SiteSettingsForm(request.POST, instance=site)
        if form.is_valid():
            form.save()
            from django.contrib import messages
            messages.success(request, 'Settings saved.')
            return redirect('staff:settings')
        return render(request, 'staff/settings.html', {
            'form': form,
            'color_schemes': ColorScheme.objects.order_by('-is_default', 'name'),
        })


class ColorSchemeAddView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'staff/color_scheme_form.html', {'form': ColorSchemeForm(), 'title': 'Add Color Scheme'})

    def post(self, request):
        form = ColorSchemeForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('staff:settings')
        return render(request, 'staff/color_scheme_form.html', {'form': form, 'title': 'Add Color Scheme'})


class ColorSchemeEditView(StaffRequiredMixin, View):
    def get(self, request, pk):
        scheme = get_object_or_404(ColorScheme, pk=pk)
        return render(request, 'staff/color_scheme_form.html', {'form': ColorSchemeForm(instance=scheme), 'scheme': scheme, 'title': f'Edit — {scheme.name}'})

    def post(self, request, pk):
        scheme = get_object_or_404(ColorScheme, pk=pk)
        form = ColorSchemeForm(request.POST, instance=scheme)
        if form.is_valid():
            form.save()
            return redirect('staff:settings')
        return render(request, 'staff/color_scheme_form.html', {'form': form, 'scheme': scheme, 'title': f'Edit — {scheme.name}'})


class ColorSchemeDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        get_object_or_404(ColorScheme, pk=pk).delete()
        return redirect('staff:settings')


class PopupListView(StaffRequiredMixin, View):
    def get(self, request):
        popups = SitePopup.objects.all()
        return render(request, 'staff/popup/list.html', {'popups': popups})


class PopupAddView(StaffRequiredMixin, View):
    def _ctx(self, form):
        return {'form': form, 'title': 'Add Popup', 'color_schemes': ColorScheme.objects.order_by('-is_default', 'name')}

    def get(self, request):
        return render(request, 'staff/popup/form.html', self._ctx(PopupForm()))

    def post(self, request):
        form = PopupForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('staff:popups')
        return render(request, 'staff/popup/form.html', self._ctx(form))


class PopupEditView(StaffRequiredMixin, View):
    def _ctx(self, form, popup):
        return {'form': form, 'popup': popup, 'title': 'Edit Popup', 'color_schemes': ColorScheme.objects.order_by('-is_default', 'name')}

    def get(self, request, pk):
        popup = get_object_or_404(SitePopup, pk=pk)
        return render(request, 'staff/popup/form.html', self._ctx(PopupForm(instance=popup), popup))

    def post(self, request, pk):
        popup = get_object_or_404(SitePopup, pk=pk)
        form = PopupForm(request.POST, request.FILES, instance=popup)
        if form.is_valid():
            form.save()
            return redirect('staff:popups')
        return render(request, 'staff/popup/form.html', self._ctx(form, popup))


class PopupToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        popup = get_object_or_404(SitePopup, pk=pk)
        if popup.is_active:
            popup.deactivate()
        else:
            popup.activate()
        return redirect('staff:popups')


class PopupDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        popup = get_object_or_404(SitePopup, pk=pk)
        popup.delete()
        return redirect('staff:popups')


# ── Color Reference ───────────────────────────────────────────────────────────

class ColorReferenceView(StaffRequiredMixin, View):
    def get(self, request):
        backgrounds = [
            {'var': '--color-bg-primary',           'label': 'Page background'},
            {'var': '--color-bg-secondary',          'label': 'Cards / panels'},
            {'var': '--color-bg-tertiary',           'label': 'Section backgrounds'},
            {'var': '--color-bg-accent',             'label': 'CTA / buttons'},
            {'var': '--color-bg-surface-light',      'label': 'Light surface'},
            {'var': '--color-bg-surface-light-raised','label': 'Light surface raised'},
            {'var': '--color-footer-bg',             'label': 'Footer background'},
        ]
        texts = [
            {'var': '--color-text-primary',   'label': 'Main body text'},
            {'var': '--color-text-secondary', 'label': 'Supporting text'},
            {'var': '--color-text-tertiary',  'label': 'Text on light bg'},
            {'var': '--color-text-accent',    'label': 'Links / prices'},
            {'var': '--color-text-heading',   'label': 'Headings'},
            {'var': '--color-footer-text',    'label': 'Footer primary'},
            {'var': '--color-footer-muted',   'label': 'Footer muted'},
            {'var': '--color-footer-subtle',  'label': 'Footer subtle'},
        ]
        golds = [
            {'var': '--color-gold-primary',  'label': 'Sandy gold (brand)'},
            {'var': '--color-gold-bright',   'label': 'Gold bright / hover'},
            {'var': '--color-gold-deep',     'label': 'Gold deep / borders'},
            {'var': '--color-gold-light',    'label': 'Gold light / tint'},
            {'var': '--color-accent-red',       'label': 'Brand red'},
            {'var': '--color-accent-red-deep',  'label': 'Red deep / hover'},
            {'var': '--color-accent-red-light', 'label': 'Red light / tint'},
        ]
        combos = [
            {'bg': '--color-bg-primary',   'text': '--color-text-primary'},
            {'bg': '--color-bg-secondary', 'text': '--color-text-primary'},
            {'bg': '--color-bg-tertiary',  'text': '--color-text-tertiary'},
            {'bg': '--color-bg-accent',    'text': '--color-text-heading'},
            {'bg': '--color-footer-bg',    'text': '--color-footer-text'},
        ]
        return render(request, 'staff/colors.html', {
            'backgrounds': backgrounds,
            'texts': texts,
            'golds': golds,
            'combos': combos,
        })


# ── Reviews ───────────────────────────────────────────────────────────────────

class ReviewListView(StaffRequiredMixin, View):
    def get(self, request):
        reviews = Review.objects.order_by('display_order', '-created_at')
        return render(request, 'staff/reviews/list.html', {'reviews': reviews})


class ReviewImportView(StaffRequiredMixin, View):
    def post(self, request):
        source = request.POST.get('source', '').strip()
        if source not in ('google', 'yelp'):
            messages.error(request, 'Unknown source.')
            return redirect('staff:reviews')

        out = StringIO()
        try:
            call_command('import_reviews', f'--source={source}', stdout=out)
            lines = [l for l in out.getvalue().strip().splitlines() if l.strip()]
            messages.success(request, lines[-1] if lines else 'Import complete.')
        except Exception as e:
            messages.error(request, f'Import failed: {e}')

        return redirect('staff:reviews')


class ReviewToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.is_active = not review.is_active
        review.save(update_fields=['is_active'])
        return redirect('staff:reviews')


class ReviewFeatureView(StaffRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.is_featured = not review.is_featured
        review.save(update_fields=['is_featured'])
        return redirect('staff:reviews')


class ReviewDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        review = get_object_or_404(Review, pk=pk)
        review.delete()
        messages.success(request, 'Review deleted.')
        return redirect('staff:reviews')


# ── Menu Items ────────────────────────────────────────────────────────────────

from django import forms as _dforms
from django.forms import inlineformset_factory


def _menu_item_image_formset():
    from apps.menu.models import MenuItem, MenuItemImage
    from apps.media.models import MediaItem

    class MenuItemImageForm(_dforms.ModelForm):
        media_item = _dforms.ModelChoiceField(
            queryset=MediaItem.objects.filter(owner_type='staff').order_by('name'),
            label='Image',
        )

        class Meta:
            model = MenuItemImage
            fields = ['media_item', 'display_order', 'is_primary']

    return inlineformset_factory(
        MenuItem, MenuItemImage,
        form=MenuItemImageForm,
        extra=1,
        can_delete=True,
    )


class MenuItemListView(StaffRequiredMixin, View):
    def get(self, request):
        from apps.menu.models import MenuItem

        qs = MenuItem.objects.prefetch_related('images').order_by('name')

        search = request.GET.get('q', '').strip()
        avail_filter = request.GET.get('avail', '')
        flag_filter = request.GET.get('flag', '')

        if search:
            qs = qs.filter(name__icontains=search)
        if avail_filter == 'available':
            qs = qs.filter(is_available=True)
        elif avail_filter == 'unavailable':
            qs = qs.filter(is_available=False)
        if flag_filter == 'featured':
            qs = qs.filter(is_featured=True)
        elif flag_filter == 'new':
            qs = qs.filter(is_new=True)
        elif flag_filter == 'chef':
            qs = qs.filter(is_chef_special=True)
        elif flag_filter == 'seasonal':
            qs = qs.filter(is_seasonal=True)

        total = qs.count()

        return render(request, 'staff/menu/item_list.html', {
            'items': qs,
            'total': total,
            'search': search,
            'avail_filter': avail_filter,
            'flag_filter': flag_filter,
        })


class MenuItemImagesView(StaffRequiredMixin, View):
    def _get_item(self, pk):
        from apps.menu.models import MenuItem
        return get_object_or_404(MenuItem, pk=pk)

    def get(self, request, pk):
        item = self._get_item(pk)
        formset = _menu_item_image_formset()(instance=item)
        return render(request, 'staff/menu/item_images.html', {
            'item': item, 'formset': formset,
        })

    def post(self, request, pk):
        item = self._get_item(pk)
        formset = _menu_item_image_formset()(request.POST, instance=item)
        if formset.is_valid():
            formset.save()
            messages.success(request, f'Images updated for "{item.name}".')
            return redirect('staff:menu_item_list')
        return render(request, 'staff/menu/item_images.html', {
            'item': item, 'formset': formset,
        })
