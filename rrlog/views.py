from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import base64
from passlib.hash import phpass

import datetime

from rrlog.log_upload import log_upload
from rrlog.utils import namedtuplefetchall

q_index = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log order by start desc limit 100
"""

q_operator_stats = """
select operator,
  count(*) as qsos,
  count(distinct call) as calls,
  count(distinct (band, call)) as band_calls,
  count(distinct call::varchar(2)) as cty,
  count(distinct (band, call::varchar(2))) as band_cty,
  count(distinct gridsquare) as grids,
  count(distinct (band, gridsquare)) as band_grids
from log where start >= %s::date and start < %s::date + %s::interval
group by operator
order by qsos desc
"""

def index(request):
    with connection.cursor() as cursor:
        cursor.execute(q_index, [])
        rows = namedtuplefetchall(cursor)

        today = datetime.date.today()
        date = f"{today.year}-{today.month:02}-01"
        cursor.execute(q_operator_stats, [date, date, '1 month'])
        current_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1 if today.month==1 else today.year}-{12 if today.month==1 else today.month-1:02}-01"
        cursor.execute(q_operator_stats, [date, date, '1 month'])
        previous_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year}-01-01"
        cursor.execute(q_operator_stats, [date, date, '1 year'])
        current_year_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1}-01-01"
        cursor.execute(q_operator_stats, [date, date, '1 year'])
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

q_call = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log where station_callsign = %s or operator = %s or call = %s order by start desc limit 100
"""

def v_call(request, call):
    with connection.cursor() as cursor:
        cursor.execute(q_call, [call, call, call])
        rows = namedtuplefetchall(cursor)

    context = { 'title': f"Log of {call}", 'qsos': rows }
    return render(request, 'rrlog/log.html', context)

q_cty = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log where cty = %s order by start desc limit 100
"""

def v_cty(request, cty):
    with connection.cursor() as cursor:
        cursor.execute(q_cty, [cty])
        rows = namedtuplefetchall(cursor)

    context = { 'title': f"Log entries from {cty}", 'qsos': rows }
    return render(request, 'rrlog/log.html', context)

q_grid = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log where gridsquare = %s order by start desc limit 100
"""

def v_grid(request, grid):
    with connection.cursor() as cursor:
        cursor.execute(q_grid, [grid])
        rows = namedtuplefetchall(cursor)

    context = { 'title': f"Log entries from {grid}", 'qsos': rows }
    return render(request, 'rrlog/log.html', context)

q_contest = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str
from log where contest = %s order by start desc limit 100
"""

def v_contest(request, contest):
    with connection.cursor() as cursor:
        cursor.execute(q_contest, [contest])
        rows = namedtuplefetchall(cursor)

    context = { 'title': contest, 'qsos': rows }
    return render(request, 'rrlog/log.html', context)

def v_month(request, year, month):
    with connection.cursor() as cursor:
        date = f"{year}-{month:02}-01"
        cursor.execute(q_operator_stats, [date, date, '1 month'])
        rows = namedtuplefetchall(cursor)

    context = {
        'month': f"{year}-{month:02}",
        'prev_month': f"{year-1 if month == 1 else year}-{((month-2)%12)+1:02}",
        'next_month': f"{year+1 if month == 12 else year}-{(month%12)+1:02}",
        'year': year,
        'operators': rows
    }
    return render(request, 'rrlog/month.html', context)

def v_year(request, year):
    with connection.cursor() as cursor:
        date = f"{year}-01-01"
        cursor.execute(q_operator_stats, [date, date, '1 year'])
        rows = namedtuplefetchall(cursor)

    context = {
        'year': year,
        'prev_year': year - 1,
        'next_year': year + 1,
        'operators': rows
    }
    return render(request, 'rrlog/year.html', context)

q_upload_list = """select uploader, id, ts,
to_char(ts, 'DD.MM.YYYY HH24:MI') as ts_str,
filename, station_callsign, operator, contest, qsos, error
from upload where uploader = %s order by id desc"""

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
    username = message

    # actual page
    message = None
    if request.method == 'POST' and 'logfile' in request.FILES:
        message = log_upload(connection, request, username)
    elif request.method == 'POST' and 'delete' in request.POST:
        id = request.POST['delete']
        with connection.cursor() as cursor:
            cursor.execute("delete from upload where id = %s and uploader = %s", [id, username])
            message = f"Upload {id} deleted"

    # get list of all uploads (including this one)
    with connection.cursor() as cursor:
        cursor.execute(q_upload_list, [username])
        uploads = namedtuplefetchall(cursor)

    context = {
        'title': 'Log Upload',
        'message': message,
        'uploads': uploads,
    }
    return render(request, 'rrlog/upload.html', context)

q_download = """select adif, filename from upload where id = %s and uploader = %s"""

def v_download(request, id):
    # authentication
    status, message = basic_auth(request)
    if not status:
        response = render(request, 'rrlog/generic.html', { 'message': message }, status=401)
        response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
        return response
    username = message

    with connection.cursor() as cursor:
        cursor.execute(q_download, [id, username])
        adif, filename = cursor.fetchone()

    return HttpResponse(adif, content_type='text/plain', headers={
        'Content-Disposition': f'attachment; filename="{filename}"',
        })
