from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.full, name='full'),
    path('promotions/', views.promotions, name='promotions'),
    path('<slug:slug>/', views.menu_detail, name='menu_detail'),
    path('api/menu-item-data/<int:pk>/', views.menu_item_data, name='menu_item_data'),
]
