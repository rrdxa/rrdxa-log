from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import base64
from passlib.hash import phpass

import datetime

from rrlog.upload import log_upload
from rrlog.utils import namedtuplefetchall

q_log = """
select log.*, dxcc.country,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log
left join dxcc on log.dxcc = dxcc.dxcc
{} order by start desc limit 500
"""

q_operator_stats = """
select coalesce(operator, station_callsign) as operator,
  count(distinct start::date) as days_active,
  count(*) as qsos,
  count(contest) as contest_qsos,
  count(*) + count(contest) as score,
  count(distinct call) as calls,
  count(distinct (call, band, major_mode)) as calls_band_mode,
  count(distinct dxcc)                           filter (where dxcc between 1 and 900) as dxccs,
  count(distinct (dxcc, band, major_mode))       filter (where dxcc between 1 and 900) as dxccs_band_mode,
  count(distinct gridsquare) as grids,
  count(distinct (gridsquare, band, major_mode)) filter (where gridsquare is not null) as grids_band_mode
from log
where start >= %s::date and start < %s::date + %s::interval and band <> 'unknown' and major_mode <> 'unknown' {}
group by coalesce(operator, station_callsign)
order by score desc
limit %s
"""

def index(request):
    with connection.cursor() as cursor:
        cursor.execute(q_log.format(''), [])
        rows = namedtuplefetchall(cursor)

        today = datetime.date.today()
        date = f"{today.year}-{today.month:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', 20])
        current_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1 if today.month==1 else today.year}-{12 if today.month==1 else today.month-1:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', 20])
        previous_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', 20])
        current_year_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', 20])
        previous_year_stats = namedtuplefetchall(cursor)

    context = {
            'title': 'Logbook',
            'current_month': f"{today.year}-{today.month:02}",
            'current_month_stats': current_month_stats,
            'previous_month': f"{today.year-1 if today.month==1 else today.year}-{12 if today.month==1 else today.month-1:02}",
            'previous_month_stats': previous_month_stats,
            'current_year': today.year,
            'current_year_stats': current_year_stats,
            'previous_year': today.year - 1,
            'previous_year_stats': previous_year_stats,
            'qsos': rows
            }
    return render(request, 'rrlog/index.html', context)

def generic_view(request, title, where, arg):
    with connection.cursor() as cursor:
        cursor.execute(q_log.format(where), arg)
        rows = namedtuplefetchall(cursor)

    context = { 'title': title, 'qsos': rows }
    return render(request, 'rrlog/log.html', context)

def v_call(request, call):
    return generic_view(request, f"Log of {call}",
                        'where station_callsign = %s or operator = %s or call = %s',
                        [call, call, call])

def v_dxcc(request, dxcc):
    return generic_view(request, f"Log entries from {dxcc}", 'where country = %s', [dxcc])

def v_grid(request, grid):
    return generic_view(request, f"Log entries from gridsquare {grid}", 'where gridsquare = %s', [grid])

def v_contest(request, contest):
    return generic_view(request, f"Log entries from {contest}", 'where contest = %s', [contest])

def v_log(request, log):
    return generic_view(request, f"QSOs in upload {log}", 'where upload = %s', [log])

def v_month(request, year, month):
    with connection.cursor() as cursor:
        date = f"{year}-{month:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', 200])
        operators = namedtuplefetchall(cursor)

        by_mode = {}
        for major_mode in 'CW', 'PHONE', 'DIGI', 'FT8':
            cursor.execute(q_operator_stats.format(f" and major_mode = '{major_mode}'"), [date, date, '1 month', 200])
            by_mode[major_mode] = namedtuplefetchall(cursor)

    context = {
        'month': f"{year}-{month:02}",
        'prev_month': f"{year-1 if month == 1 else year}-{((month-2)%12)+1:02}",
        'next_month': f"{year+1 if month == 12 else year}-{(month%12)+1:02}",
        'year': year,
        'operators': operators,
        'cw_operators': by_mode['CW'],
        'phone_operators': by_mode['PHONE'],
        'digi_operators': by_mode['DIGI'],
        'ft8_operators': by_mode['FT8'],
    }
    return render(request, 'rrlog/month.html', context)

def v_year(request, year):
    with connection.cursor() as cursor:
        date = f"{year}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', 200])
        operators = namedtuplefetchall(cursor)

        by_mode = {}
        for major_mode in 'CW', 'PHONE', 'DIGI', 'FT8':
            cursor.execute(q_operator_stats.format(f" and major_mode = '{major_mode}'"), [date, date, '1 year', 200])
            by_mode[major_mode] = namedtuplefetchall(cursor)

    context = {
        'year': year,
        'prev_year': year - 1,
        'next_year': year + 1,
        'operators': operators,
        'cw_operators': by_mode['CW'],
        'phone_operators': by_mode['PHONE'],
        'digi_operators': by_mode['DIGI'],
        'ft8_operators': by_mode['FT8'],
    }
    return render(request, 'rrlog/year.html', context)

q_upload_list = """select uploader, id, ts,
to_char(ts, 'DD.MM.YYYY HH24:MI') as ts_str,
filename, station_callsign, operator, contest, qsos, error
from upload where uploader = %s or %s in ('DF7CB', 'DF7EE', 'DK2DQ') order by id desc"""

def basic_auth(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header:
        return False, "Login required"
    token_type, _, credentials = auth_header.partition(' ')
    if token_type.lower() != "basic":
        return False, "Only Basic auth supported"
    username, password = base64.b64decode(credentials).decode("utf-8").split(':')
    username = username.upper()

    with connection.cursor() as cursor:
        cursor.execute("select user_pass from wordpress_users where upper(user_login) = %s", [username])
        user_password = cursor.fetchone()
        if not user_password:
            print(f"user {username} not found in database")
            return False, "Login failed"
        if not phpass.verify(password, user_password[0]):
            print("wrong password")
            return False, "Login failed"

    return True, username

def v_upload(request):
    # authentication
    status, message = basic_auth(request)
    if not status:
        response = render(request, 'rrlog/generic.html', { 'message': message }, status=401)
        response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
        return response
    uploader = message

    # actual page
    message = None
    if request.method == 'POST' and 'logfile' in request.FILES:
        message = log_upload(connection, request, uploader)
    elif request.method == 'POST' and 'delete' in request.POST:
        id = request.POST['delete']
        with connection.cursor() as cursor:
            cursor.execute("delete from upload where id = %s and uploader = %s", [id, uploader])
            message = f"Upload {id} deleted"

    # get list of all uploads (including this one)
    with connection.cursor() as cursor:
        cursor.execute(q_upload_list, [uploader, uploader])
        uploads = namedtuplefetchall(cursor)

    context = {
        'title': 'Log Upload',
        'message': message,
        'uploads': uploads,
        'uploader': uploader,
    }
    return render(request, 'rrlog/upload.html', context)

q_download = """select adif, filename from upload where id = %s and (uploader = %s or %s in ('DF7CB', 'DF7EE', 'DK2DQ'))"""

def v_download(request, id):
    # authentication
    status, message = basic_auth(request)
    if not status:
        response = render(request, 'rrlog/generic.html', { 'message': message }, status=401)
        response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
        return response
    username = message

    with connection.cursor() as cursor:
        cursor.execute(q_download, [id, username, username])
        adif, filename = cursor.fetchone()

    response = HttpResponse(adif, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
