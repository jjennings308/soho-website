from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome to SOHO Website")

def home(request):
    return render(request, 'core/home.html')

def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')
