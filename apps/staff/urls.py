from django.urls import path

from . import views

app_name = 'staff'

urlpatterns = [
    path('login/', views.StaffLoginView.as_view(), name='login'),
    path('logout/', views.StaffLogoutView.as_view(), name='logout'),
    path('', views.DashboardView.as_view(), name='dashboard'),

    # Menu mode
    path('menu-mode/', views.MenuModeView.as_view(), name='menu_mode'),

    # Events
    path('events/', views.EventListView.as_view(), name='events'),
    path('events/add/', views.EventAddView.as_view(), name='event_add'),
    path('events/<int:pk>/edit/', views.EventEditView.as_view(), name='event_edit'),
    path('events/<int:pk>/toggle/', views.EventToggleView.as_view(), name='event_toggle'),
    path('events/<int:pk>/delete/', views.EventDeleteView.as_view(), name='event_delete'),

    # Gallery
    path('gallery/', views.GalleryListView.as_view(), name='gallery'),
    path('gallery/upload/', views.GalleryUploadView.as_view(), name='gallery_upload'),
    path('gallery/<int:pk>/toggle/', views.GalleryToggleView.as_view(), name='gallery_toggle'),
    path('gallery/<int:pk>/delete/', views.GalleryDeleteView.as_view(), name='gallery_delete'),

    # Newsletter
    path('newsletter/', views.NewsletterListView.as_view(), name='newsletter'),
    path('newsletter/compose/', views.NewsletterComposeView.as_view(), name='newsletter_compose'),
    path('newsletter/<int:pk>/', views.NewsletterDetailView.as_view(), name='newsletter_detail'),
    path('newsletter/<int:pk>/send/', views.NewsletterSendView.as_view(), name='newsletter_send'),
    path('newsletter/<int:pk>/delete/', views.NewsletterDeleteView.as_view(), name='newsletter_delete'),
]
