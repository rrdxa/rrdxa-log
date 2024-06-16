from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection

def index(request):
    context = {
        'title': 'RRDXAi Cluster',
    }
    return render(request, 'cluster/index.html', context)
