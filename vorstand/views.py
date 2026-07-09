from datetime import date

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib.auth.models import User

from rrlog.auth import auth_required
from rrmember.models import Vereinsmitglied

@auth_required
def v_index(request):
    user = get_object_or_404(User, username=request.username)
    message = ""

    if not user.groups.filter(name='vorstand').exists():
        return render(request, 'rrlog/generic.html', { 'message': "Dieser Bereich ist nur für Vorstandsmitglieder" }, status=401)

    if 'jahresbeitrag' in request.POST:
        mitglied = Vereinsmitglied.objects.get(member_no=request.POST['jahresbeitrag'])
        mitglied.zahle_jahresbeitrag()
        message = f"Beitrag bis {mitglied.bezahlt_bis} bezahlt"

    verein = Vereinsmitglied.objects.all().order_by('call')

    today = date.today()
    this_year = date(today.year, 12, 31)
    last_year = date(today.year-1, 12, 31)

    context = {
            "verein": verein,
            "this_year": this_year,
            "last_year": last_year,
            "message": message,
            }
    return render(request, 'vorstand/vorstand.html', context)
