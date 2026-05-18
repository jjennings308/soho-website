from django.views.generic import ListView

from .models import GalleryCategory, GalleryItem


class GalleryView(ListView):
    model = GalleryItem
    template_name = 'gallery/index.html'
    context_object_name = 'items'
    paginate_by = 8

    def get_queryset(self):
        qs = GalleryItem.objects.filter(is_published=True).select_related('category')
        slug = self.request.GET.get('category', '').strip()
        if slug:
            qs = qs.filter(category__slug=slug)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['categories'] = GalleryCategory.objects.filter(is_published=True).order_by('display_order', 'name')
        ctx['active_category'] = self.request.GET.get('category', '')
        return ctx
