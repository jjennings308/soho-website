from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome to SOHO Website Menu")

def food(request):
    return render(request, 'menu/food.html')

def drinks(request):
    return render(request, 'menu/drinks.html')

def full(request):
    return render(request, 'menu/full.html')
