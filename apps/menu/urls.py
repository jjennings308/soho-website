from django.urls import path
from . import views
from .views import EventDayMenuView, WeeklySpecialsView

app_name = 'menu'

urlpatterns = [
    path('', views.full, name='full'),
    path('promotions/', views.promotions, name='promotions'),
    path('event-day/', EventDayMenuView.as_view(), name='event_day_menu'),
    path('specials/', WeeklySpecialsView.as_view(), name='weekly_specials'),
    path('<slug:slug>/', views.menu_detail, name='menu_detail'),
    path('api/menu-item-data/<int:pk>/', views.menu_item_data, name='menu_item_data'),
]
