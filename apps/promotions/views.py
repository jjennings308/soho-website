from django.shortcuts import render
from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome to SOHO Website Promotions")

def list(request):
    return render(request, 'promotions/list.html')
