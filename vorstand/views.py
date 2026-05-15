from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, FileResponse
from django.contrib.auth.models import User

from rrlog.auth import auth_required
from rrmember.models import Vereinsmitglied

@auth_required
def v_index(request):
    user = get_object_or_404(User, username=request.username)

    if not user.groups.filter(name='vorstand').exists():
        return render(request, 'rrlog/generic.html', { 'message': "Dieser Bereich ist nur für Vorstandsmitglieder" }, status=401)

    verein = Vereinsmitglied.objects.all().order_by('member_no')

    context = {
            "verein": verein,
            }
    return render(request, 'vorstand/vorstand.html', context)
