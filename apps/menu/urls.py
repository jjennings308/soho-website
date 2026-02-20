from django.urls import path
from . import views

app_name = 'menu'

urlpatterns = [
    path('', views.index, name='index'),
    path('food', views.food, name='food'),
    path('drinks', views.drinks, name='drinks'),
    path('full', views.full, name='full'),
]