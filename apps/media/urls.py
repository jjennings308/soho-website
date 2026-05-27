from django.urls import path

from .views import GalleryView

app_name = 'media'

urlpatterns = [
    path('', GalleryView.as_view(), name='gallery'),
]
