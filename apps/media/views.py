from django.views.generic import ListView

from .models import MediaCategory, MediaItem


class GalleryView(ListView):
    """
    Public /gallery/ page.

    Shows all staff-owned, published, approved images grouped by category.
    Category tabs show only MediaCategory records where is_gallery_visible=True.
    Filtered by ?category=<slug>.
    """
    template_name    = 'media/gallery/index.html'
    context_object_name = 'items'
    paginate_by      = 8

    def get_queryset(self):
        qs = (
            MediaItem.objects
            .filter(
                owner_type  = 'staff',
                is_published = True,
                is_approved  = True,
                media_type   = 'image',
            )
            .select_related('category')
            .exclude(file='')
        )
        slug = self.request.GET.get('category', '').strip()
        if slug:
            qs = qs.filter(category__slug=slug)
        return qs.order_by('category__display_order', 'display_order', 'name')

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories']       = (
            MediaCategory.objects
            .filter(is_published=True, is_gallery_visible=True)
            .order_by('display_order', 'name')
        )
        ctx['active_category']  = self.request.GET.get('category', '')
        return ctx
