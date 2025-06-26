from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection
import datetime
import json
import time

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
    response['Content-Disposition'] = f'attachment; filename="RRDXA_{data.call}.pdf"'
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

adif_ver = '3.1.4'

def encode(key, value):
    if value == None or value == "":
        return ""

    l = len(str(value))
    return f"<{key}:{l}>{str(value)}\n"

@auth_required
def v_mylog(request):
    data = member_data(request.username)

    with connection.cursor() as cursor:
        cursor.execute("""select
            adif,
            to_char(start, 'YYYYMMDD') as qso_date,
            to_char(start, 'hh24mi') as time_on,
            call,
            station_callsign,
            operator,
            dxcc,
            band, freq,
            mode, submode,
            rsttx as rst_sent,
            extx as stx_string,
            rstrx as rst_rcvd,
            exrx as srx_string,
            gridsquare,
            contest as contest_id
        from log where coalesce(operator, station_callsign) = %s order by start""", [data.call])

        adi = [f"Log for {data.call} at logbook.rrdxa.org\n",
               f"Generated {time.asctime()}\n",
               f"Contains {cursor.rowcount} QSOs\n",
               "\n",
               encode('adif_ver', adif_ver),
               "<eoh>\n"]

        for qso in cursor.fetchall():
            q = {}
            for col, field in enumerate(qso):
                fname = cursor.description[col].name

                # explode "adif" record
                if fname == "adif" and field:
                    js = json.loads(field)
                    q = {key.lower(): js[key] for key in js}
                else:
                    q[fname] = field

            adi.append("\n")
            for field in sorted(q.keys()):
                adi.append(encode(field, q[field]))
            adi.append("<eor>\n")

    response = HttpResponse("".join(adi), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{data.call}_rrdxa_logbook.adi"'
    return response
