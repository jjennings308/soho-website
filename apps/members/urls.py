from django.urls import path

from .views import ConfirmView, SubscribeView, UnsubscribeView

app_name = 'members'

urlpatterns = [
    path('subscribe/', SubscribeView.as_view(), name='subscribe'),
    path('subscribe/confirm/<uuid:token>/', ConfirmView.as_view(), name='confirm'),
    path('unsubscribe/<uuid:token>/', UnsubscribeView.as_view(), name='unsubscribe'),
]
