from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View

from apps.core.models import SiteSettings
from apps.events.models import EventDay
from apps.gallery.models import GalleryCategory, GalleryItem
from apps.members.models import Newsletter, SoHoMember

from .forms import EventForm, GalleryUploadForm, NewsletterForm


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
            .filter(date__gte=timezone.localdate(), is_active=True)
            .order_by('date', 'game_time')[:5]
        )
        site = SiteSettings.load()
        subscriber_count = SoHoMember.objects.filter(is_active=True, is_email_subscribed=True).count()
        draft_count = Newsletter.objects.filter(sent_at__isnull=True).count()
        unpublished_count = GalleryItem.objects.filter(is_published=False).count()

        return render(request, 'staff/dashboard.html', {
            'menu_mode': menu_mode,
            'today_events': today_events,
            'upcoming': upcoming,
            'site': site,
            'subscriber_count': subscriber_count,
            'draft_count': draft_count,
            'unpublished_count': unpublished_count,
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
            .filter(date__gte=timezone.localdate())
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


# ── Gallery ───────────────────────────────────────────────────────────────────

class GalleryListView(StaffRequiredMixin, View):
    def get(self, request):
        items = GalleryItem.objects.select_related('category').order_by(
            'category__display_order', 'display_order'
        )
        return render(request, 'staff/gallery/list.html', {'items': items})


class GalleryUploadView(StaffRequiredMixin, View):
    def get(self, request):
        return render(request, 'staff/gallery/upload.html', {'form': GalleryUploadForm()})

    def post(self, request):
        form = GalleryUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('staff:gallery')
        return render(request, 'staff/gallery/upload.html', {'form': form})


class GalleryToggleView(StaffRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(GalleryItem, pk=pk)
        item.is_published = not item.is_published
        item.save(update_fields=['is_published'])
        return redirect('staff:gallery')


class GalleryDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        item = get_object_or_404(GalleryItem, pk=pk)
        item.delete()
        return redirect('staff:gallery')


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


class NewsletterSendView(StaffRequiredMixin, View):
    def post(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk)
        if not newsletter.is_draft:
            return redirect('staff:newsletter_detail', pk=pk)

        recipients = list(
            SoHoMember.objects.filter(is_active=True, is_email_subscribed=True)
            .values_list('email', flat=True)
        )

        if recipients:
            html_body = render_to_string('members/emails/newsletter.html', {'newsletter': newsletter})
            email = EmailMessage(
                subject=newsletter.subject,
                body=html_body,
                from_email=None,
                bcc=recipients,
            )
            email.content_subtype = 'html'
            email.send()

        newsletter.sent_at = timezone.now()
        newsletter.recipient_count = len(recipients)
        newsletter.sent_by = request.user
        newsletter.save(update_fields=['sent_at', 'recipient_count', 'sent_by'])

        return redirect('staff:newsletter_detail', pk=pk)


class NewsletterDeleteView(StaffRequiredMixin, View):
    def post(self, request, pk):
        newsletter = get_object_or_404(Newsletter, pk=pk, sent_at__isnull=True)
        newsletter.delete()
        return redirect('staff:newsletter')
