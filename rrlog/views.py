from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import base64
from passlib.hash import phpass

import datetime
import re

from rrlog.upload import log_upload
from rrlog.utils import namedtuplefetchall
from rrlog.summary import get_summary

q_log = """
select log.*, dxcc.country,
to_char(start, 'DD.MM.YYYY') as start_str
from log
left join dxcc on log.dxcc = dxcc.dxcc
{} order by start desc limit 500
"""

q_events = """
select event,
to_char(lower(period), 'DD.MM.YYYY HH24:MI') as start_str, to_char(upper(period), 'DD.MM.YYYY HH24:MI') as stop_str,
count(*)
from event e join upload u on e.event_id = u.event_id
where lower(period) >= now() - '1 year'::interval
group by e.event_id
order by upper(period) desc
limit 30
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
        cursor.execute(q_events, [])
        events = namedtuplefetchall(cursor)

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

        cursor.execute(q_log.format(''), [])
        qsos = namedtuplefetchall(cursor)

    context = {
            'title': 'Logbook',
            'events': events,
            'current_month': f"{today.year}-{today.month:02}",
            'current_month_stats': current_month_stats,
            'previous_month': f"{today.year-1 if today.month==1 else today.year}-{12 if today.month==1 else today.month-1:02}",
            'previous_month_stats': previous_month_stats,
            'current_year': today.year,
            'current_year_stats': current_year_stats,
            'previous_year': today.year - 1,
            'previous_year_stats': previous_year_stats,
            'qsos': qsos,
            'urlpath': '/log/logbook/',
            }
    return render(request, 'rrlog/index.html', context)

def get_request_qsos(request, quals, params):
    for key in request.GET:
        param = request.GET[key]
        if key == 'call':
            quals.append("(station_callsign = %s or operator = %s or call = %s)")
            params += [param, param, param]
        elif key == 'dxcc':
            quals.append("log.dxcc = %s") # ambiguous column name
            params += [param]
        elif key == 'year' and re.match('\d{4}$', param):
            quals.append("start >= %s and start < %s")
            params += [f"{param}-01-01", f"{int(param)+1}-01-01"]
        elif key == 'month' and re.match('\d{4}-\d{1,2}$', param):
            quals.append("start >= %s and start < %s::timestamptz + '1 month'::interval")
            params += [f"{param}-01", f"{param}-01"]
        elif key in ('station_callsign', 'operator', 'call', 'country',
                     'band', 'major_mode', 'mode', 'submode', 'rsttx', 'rstrx',
                     'gridsquare', 'contest',
                     'upload'):
            quals.append(f"{key} = %s")
            params += [param]

    where = ('where ' + ' and '.join(quals)) if quals else ''

    with connection.cursor() as cursor:
        cursor.execute(q_log.format(where), params)
        qsos = namedtuplefetchall(cursor)

    return qsos

def generic_view(request, title, quals, params):
    qsos = get_request_qsos(request, quals, params)
    context = { 'title': title, 'qsos': qsos, 'show_main_link': True }
    return render(request, 'rrlog/log.html', context)

def v_logbook(request):
    return generic_view(request, "Logbook", [], [])

def v_dxcc(request, dxcc):
    return generic_view(request, f"Log entries from {dxcc}", ['country = %s'], [dxcc])

def v_grid(request, grid):
    return generic_view(request, f"Log entries from gridsquare {grid}", ['gridsquare = %s'], [grid])

def v_contest(request, contest):
    return generic_view(request, f"Log entries from {contest}", ['contest = %s'], [contest])

q_call_events = """
select station_callsign,
    id as upload_id,
    nullif(operators, station_callsign) operators,
    contest,
    qsos,
    claimed_score,
    category_assisted,
    category_band,
    category_mode,
    category_overlay,
    category_power,
    category_station,
    category_time,
    exchange,
    e.event
from upload u left join event e on u.event_id = e.event_id
where station_callsign = %s
    and category_operator is not null
order by u.start desc
"""

def v_call(request, call):
    with connection.cursor() as cursor:
        cursor.execute(q_call_events, [call])
        entries = namedtuplefetchall(cursor)
    qsos = get_request_qsos(request, ['(station_callsign = %s or operator = %s)'], [call, call])

    context = {
        'title': f"Logbook for {call}",
        'qsos': qsos,
        'entries': entries,
        'show_main_link': True
    }
    return render(request, 'rrlog/call.html', context)

q_event = """
with events as (
select station_callsign,
    id as upload_id,
    nullif(operators, station_callsign) operators,
    contest,
    qsos,
    claimed_score,
    category_assisted,
    category_band,
    category_mode,
    category_overlay,
    category_power,
    category_station,
    category_time,
    exchange
from upload u join event e on u.event_id = e.event_id
where e.event = %s
order by qsos desc nulls last, claimed_score desc nulls last
)
select * from events
union all
select null, null, null, null, sum(qsos), sum(claimed_score), null, null, null, null, null, null, null, null from events
"""

def v_event(request, event):
    with connection.cursor() as cursor:
        cursor.execute(q_event, [event])
        entries = namedtuplefetchall(cursor)

    context = {
        'title': event,
        'event': event,
        'entries': entries,
    }
    return render(request, 'rrlog/event.html', context)

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
qsos, to_char(start, 'DD.MM.YYYY') as start_str, to_char(stop, 'DD.MM.YYYY') as stop_str,
filename, category_operator,
station_callsign, operator, contest, event,
error
from upload u left join event e on u.event_id = e.event_id
where uploader = %s or %s in ('DF7CB', 'DF7EE', 'DK2DQ')
order by id desc limit 100"""

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

def v_download(request, upload_id):
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

    response = HttpResponse(adif, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def v_summary(request, upload_id):
    with connection.cursor() as cursor:
        cursor.execute(q_log.format('where upload = %s'), [upload_id])
        qsos = namedtuplefetchall(cursor)
        data, summary = get_summary(cursor, upload_id)

    context = {
        'title': f"{data.station_callsign} {data.contest} {data.category_operator}",
        'data': data,
        'summary': summary,
        'qsos': qsos,
    }
    return render(request, 'rrlog/summary.html', context)
