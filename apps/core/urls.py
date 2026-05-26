from django.urls import path
from . import views
from .views import EventInquiryView, HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about', views.about, name='about'),
    path('contact', views.contact, name='contact'),
    path('test', views.theme_test, name='theme_test'),
    path('online-delivery/', views.online_delivery, name='online_delivery'),
    path('event-inquiry/', EventInquiryView.as_view(), name='event_inquiry'),
    path('privacy/', views.privacy, name='privacy'),
    path('terms/', views.terms, name='terms'),
    path('accessibility/', views.accessibility, name='accessibility'),
    path('reviews/', views.reviews, name='reviews'),
]
