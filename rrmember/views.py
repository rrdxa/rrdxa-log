from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection
import datetime

from rrlog.auth import auth_required
from rrlog.utils import namedtuplefetchall
from .certificate import certificate

def member_data(call):
    with connection.cursor() as cursor:
        cursor.execute("select call, first_name, display_name, member_no, admin from members where call = %s", [call])
        data = namedtuplefetchall(cursor)
        return data[0]

@auth_required
def v_index(request):
    data = member_data(request.username)

    with connection.cursor() as cursor:
        cursor.execute("select member_no, call, display_name, callsigns, wpid from members where public and member_no is not null order by member_no", [])
        member_list = namedtuplefetchall(cursor)

    context = {
            "call": data.call,
            "data": data,
            "member_list": member_list,
            }
    return render(request, 'rrmember/member.html', context)

@auth_required
def v_membership_certificate(request):
    data = member_data(request.username)
    today = str(datetime.date.today())

    if data.member_no is None:
        return render(request, 'rrlog/generic.html', { 'message': f"{data.call} does not have a Member No yet" }, status=404)

    pdf = certificate(data.call, data.display_name, today, data.member_no)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="RRDXA_{data.call}.pdf"'
    return response

def comma_join(l):
    if l is None:
        return ''
    return ','.join(l)

@auth_required
def v_list(request):
    with connection.cursor() as cursor:
        cursor.execute("select member_no, call, display_name, callsigns from members where public and member_no is not null order by member_no", [])
        member_list = namedtuplefetchall(cursor)

    csv = "member_no;call;name;extra_calls\n" + \
        ''.join([f"{m.member_no};{m.call};{m.display_name};{comma_join(m.callsigns)}\n" for m in member_list])
    response = HttpResponse(csv, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'inline; filename="RRDXA_members.txt"'
    return response
