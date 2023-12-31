from django.shortcuts import render
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import datetime
import re

from rrlog.auth import basic_auth
from rrlog.upload import log_upload
from rrlog.utils import namedtuplefetchall
from rrlog.summary import get_summary

q_log = """
select log.*, dxcc.country,
to_char(start, 'DD.MM.YYYY') as start_str,
rrcall, rroperator
from log
left join dxcc on log.dxcc = dxcc.dxcc
left join rrcalls on log.call = rrcalls.rrcall
{}
order by start desc limit {}
"""

q_events = """
select event, cabrillo_name, vhf,
month_str(e.start), start_str(e.start), stop_str(e.stop),
count(u)
from event e left join upload u on e.event_id = u.event_id
where e.start >= now() - '1 year'::interval
group by e.event_id
having count(u) >= %s
order by e.start desc
limit %s
"""

q_eventlist = """
select event_id, event,
month_str(start), start_str(start), stop_str(stop)
from event e
where start >= now() - '1 year'::interval
order by start desc
limit 100
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

def v_index(request):
    limit = 10

    with connection.cursor() as cursor:
        cursor.execute(q_events, [3, 30])
        events = namedtuplefetchall(cursor)

        today = datetime.date.today()
        date = f"{today.year}-{today.month:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', limit])
        current_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', limit])
        current_year_stats = namedtuplefetchall(cursor)

        cursor.execute(q_log.format('where rrcall is not null', 250), [])
        qsos = namedtuplefetchall(cursor)

    context = {
            'title': 'Logbook',
            'events': events,
            'current_month': f"{today.year}-{today.month:02}",
            'current_month_stats': current_month_stats,
            'current_year': today.year,
            'current_year_stats': current_year_stats,
            'qsos': qsos,
            'urlpath': '/log/logbook/',
            }
    return render(request, 'rrlog/index.html', context)

def v_mao(request):
    limit = 100

    with connection.cursor() as cursor:
        today = datetime.date.today()
        date = f"{today.year}-{today.month:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', limit])
        current_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1 if today.month==1 else today.year}-{12 if today.month==1 else today.month-1:02}-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 month', limit])
        previous_month_stats = namedtuplefetchall(cursor)

        date = f"{today.year}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', limit])
        current_year_stats = namedtuplefetchall(cursor)

        date = f"{today.year-1}-01-01"
        cursor.execute(q_operator_stats.format(''), [date, date, '1 year', limit])
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
            'urlpath': '/log/logbook/',
            }
    return render(request, 'rrlog/mao.html', context)

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
        cursor.execute(q_log.format(where, 500), params)
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
    category_operator,
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

q_rrdxa60_top = """
select call, count(distinct (rroperator, band)) from (
    select coalesce(operator, station_callsign) as call, rroperator, band
        from log
        join rrcalls on log.call = rrcalls.rrcall
        where start between %s and %s
    union
    select call, rroperator, band
        from log
        join rrcalls on log.station_callsign = rrcalls.rrcall
        where start between %s and %s
)
group by 1
having count(distinct (rroperator, band)) >= 60
order by 2 desc;
"""

q_worked = """
select rroperator, band
    from log
    join rrcalls on log.call = rrcalls.rrcall
    where coalesce(operator, station_callsign) = %s and start between %s and %s
union
select rroperator, band
    from log
    join rrcalls on log.station_callsign = rrcalls.rrcall
    where call = %s and start between %s and %s
"""

def v_rrdxa60(request):
    top_calls = []
    call, qsos, bands, worked = None, None, None, []
    da0rr = False
    bandpoints = 0

    today = datetime.date.today()
    year = today.year

    if 'call' in request.GET:
        call = request.GET['call'].upper()

        with connection.cursor() as cursor:
            params = [call, f"{year}-01-01", f"{year+1}-01-01"]
            cursor.execute(q_log.format(f"where call = %s and start between %s and %s", 1000), params)
            qsos = namedtuplefetchall(cursor)

            cursor.execute("select distinct band from log where call = %s and start between %s and %s order by 1", params)
            bands = [x[0] for x in cursor.fetchall()]

            # compute crosstab of worked members
            cursor.execute(q_worked, params * 2)
            wkd = {'DA0RR': {}}
            for operator, band in cursor.fetchall():
                if operator not in wkd:
                    wkd[operator] = {}
                wkd[operator][band] = 1
                bandpoints += 1
                if operator == 'DA0RR': da0rr = True
            for operator in wkd:
                worked.append({
                    'operator': operator,
                    'bands': [(wkd[operator][band] if band in wkd[operator] else '') for band in bands],
                })

    else:
        with connection.cursor() as cursor:
            params = [f"{year}-01-01", f"{year+1}-01-01"] * 2
            cursor.execute(q_rrdxa60_top, params)
            top_calls = namedtuplefetchall(cursor)

    context = {
        'title': f"Worked All RRDXA60",
        'top_calls': top_calls,
        'top_calls_len': len(top_calls),
        'call': call,
        'bands': bands,
        'worked': worked,
        'bandpoints': bandpoints,
        'da0rr': da0rr,
        'qsos': qsos,
    }
    return render(request, 'rrlog/rrdxa60.html', context)

q_challenge = """
select coalesce(operator, station_callsign) as call,
    sum(qsos) as qsos,
    count(*) filter (where qsos >= 60 or vhf and qsos >= 30) as multis,
    sum(qsos) * count(*) filter (where qsos >= 60 or vhf and qsos >= 30) as score,
    array_agg(event order by e.start, event) as events,
    array_agg(qsos order by e.start, event) as event_qsos,
    array_agg(u.id order by e.start, event) as event_upload_ids,
    array_agg(u.id order by e.start, event) as event_vhf
from upload u join event e on u.event_id = e.event_id
where e.start between %s and %s
group by 1
order by 4 desc, 2 desc
"""

def v_challenge(request, year=None):
    if year is None:
        today = datetime.date.today()
        year = today.year

    with connection.cursor() as cursor:
        cursor.execute(q_challenge, [f"{year}-01-01", f"{year+1}-01-01"])
        entries = namedtuplefetchall(cursor)

    # psycopg2 doesn't understand tuples in arrays, so we select 4 separate
    # arrays above and zip them together here
    for entry in entries:
        entry.events[:] = zip(entry.events, entry.event_qsos, entry.event_upload_ids, entry.event_vhf)

    context = {
        'title': f"RRDXA Challenge {year}",
        'entries': entries,
    }
    return render(request, 'rrlog/challenge.html', context)

q_schedules = """select 
 schedule.cabrillo_name,
 schedule.prefix, schedule.dateformat,
 schedule.day,
 schedule.month,
 schedule.week,
 schedule.dow,
 to_char(schedule.start, 'HH:MM') start,
 schedule.days,
 to_char(schedule.stop, 'HH:MM') stop
from schedule
order by month, (week+8) % 8, dow, start"""

def v_events(request):
    if request.method == 'POST':
        # authentication
        status, message = basic_auth(request)
        if not status:
            response = render(request, 'rrlog/generic.html', { 'message': message }, status=401)
            response['WWW-Authenticate'] = 'Basic realm="RRDXA Log Upload"'
            return response
        username = message

        with connection.cursor() as cursor:
            is_vhf = 'vhf' in request.POST
            cursor.execute("insert into event (event, cabrillo_name, start, stop, author, vhf) values (%s, %s, %s, %s, %s, %s)",
                           [request.POST['event'], request.POST['cabrillo_name'], request.POST['start'], request.POST['end'], username, is_vhf])
            connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(q_events, [0, 500])
        events = namedtuplefetchall(cursor)
        cursor.execute(q_schedules)
        schedules = namedtuplefetchall(cursor)

    today = str(datetime.date.today())

    context = {
        'today': today,
        'events': events,
        'schedules': schedules,
    }
    return render(request, 'rrlog/events.html', context)

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
    category_operator,
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
select count(*)::text, -1, null, null, sum(qsos), sum(claimed_score), null, null, null, null, null, null, null, null, null from events
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
start_str(ts) as ts_str,
qsos,
start_str(u.start), stop_str(u.stop),
filename, category_operator,
station_callsign, operator, contest, event,
error
from upload u left join event e on u.event_id = e.event_id
where uploader = %s or %s in ('DF7CB', 'DF7EE', 'DK2DQ')
order by id desc limit 100"""

def v_upload(request, filetype=None):
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

    with connection.cursor() as cursor:
        if filetype != 'adif':
            cursor.execute(q_eventlist, [])
            eventlist = namedtuplefetchall(cursor)
        else:
            eventlist = []

        # get list of all uploads (including this one)
        cursor.execute(q_upload_list, [uploader, uploader])
        uploads = namedtuplefetchall(cursor)

    if filetype is None:
        filetype = ''

    context = {
        'title': f"{filetype.title()} Log Upload",
        'filetype': filetype,
        'message': message,
        'eventlist': eventlist,
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
        cursor.execute(q_download, [upload_id, username, username])
        adif, filename = cursor.fetchone()

    response = HttpResponse(adif, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

def v_summary(request, upload_id):
    with connection.cursor() as cursor:
        cursor.execute(q_log.format('where upload = %s', 500), [upload_id])
        qsos = namedtuplefetchall(cursor)
        data, summary = get_summary(cursor, upload_id)

    context = {
        'title': f"{data.station_callsign} {data.contest} {data.category_operator}",
        'data': data,
        'summary': summary,
        'qsos': qsos,
    }
    return render(request, 'rrlog/summary.html', context)

def v_members(request):
    with connection.cursor() as cursor:
        cursor.execute("select call, callsigns from members where call ~ '\d' and not '{bbp_spectator}' <@ user_roles order by call")
        members = namedtuplefetchall(cursor)

    if 'csv' in request.GET:
        csv = ''
        for member in members:
            csv += member.call
            if member.callsigns:
                for call in member.callsigns:
                    csv += f",{call}"
            csv += "\n"

        response = HttpResponse(csv, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="rrdxa-members.csv"'
        return response

    context = {
        'title': "RRDXA members",
        'members': members,
    }
    return render(request, 'rrlog/members.html', context)
