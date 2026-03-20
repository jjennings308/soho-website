"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('ckeditor5/', include('django_ckeditor_5.urls')), 
    path('', include('apps.core.urls')),
    path('menu/', include('apps.menu.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # urls.py — temporary local preview only, remove before deploy
    from django.views.defaults import page_not_found, server_error, permission_denied, bad_request
    from django.http import HttpRequest

    def preview_404(request):
        return page_not_found(request, exception=Exception())

    def preview_500(request):
        return server_error(request)

    def preview_403(request):
        return permission_denied(request, exception=Exception())

    def preview_400(request):
        return bad_request(request, exception=Exception())

    urlpatterns += [
        path('preview/404/', preview_404),
        path('preview/500/', preview_500),
        path('preview/403/', preview_403),
        path('preview/400/', preview_400),
    ]