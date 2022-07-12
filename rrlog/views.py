from django.shortcuts import render
#from django.template import loader
from django.http import HttpResponse

def index(request):
    return HttpResponse("Hello, world. You're at the log index.")

def v_call(request, call):
    context = { 'call': call }
    return render(request, 'rrlog/call.html', context)
