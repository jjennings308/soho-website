from django.urls import path
from . import views
from .views import HomeView

app_name = 'core'

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('about', views.about, name='about'),
    path('contact', views.contact, name='contact'),
    path('test', views.theme_test, name='theme_test'),
]
