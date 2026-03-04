from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    context = {
        "hero_banner": {
            "title": "Welcome to Soho",
            "content": "Craft cocktails and seasonal plates.",
            "style" : "background-color: var(--color-bg-primary); color: var(--color-text-primary);",
        }
    }
    return render(request, "core/home.html", context)


def about(request):
    return render(request, 'core/about.html')

def contact(request):
    return render(request, 'core/contact.html')
