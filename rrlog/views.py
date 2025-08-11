from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import datetime
import re

from rrdxa import settings

from rrlog.auth import basic_auth, auth_required
from rrlog.upload import log_upload
from rrlog.utils import namedtuplefetchall, band_sort
from rrlog.summary import get_summary, post_summary

q_log = """
select * from log_v
{}
order by start {} limit {}
"""

q_log_dupecheck = """
select *, row_number() over (partition by call, band, major_mode, mode, submode order by start) from log_v
{}
order by start {} limit {}
"""

q_events = """
select event, cabrillo_name, vhf,
month_str(e.start), start_str(e.start), stop_str(e.stop),
count(u)
from event e left join upload u on e.event_id = u.event_id
where e.start >= now() - '2 year'::interval
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
    and qsos > 0
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

def render_with_username_cookie(request, page, context, username):
    response = render(request, page, context)
    if username:
        response.set_cookie('username', username)
    return response

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

        cursor.execute(q_log.format('where rroperator is not null', 'desc', 250), [])
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
        elif key == 'year' and re.match(r'\d{4}$', param):
            quals.append("start >= %s and start < %s")
            params += [f"{param}-01-01", f"{int(param)+1}-01-01"]
        elif key == 'month' and re.match(r'\d{4}-\d{1,2}$', param):
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
        cursor.execute(q_log.format(where, 'desc', 500), params)
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

q_members_list = """
select string_agg(replace(rrcall, '/', '%%2F'), ',') from rrcalls;
"""

# materialized because it takes 26s to execute (2024-05-04, will get worse over the year) (4s on new server; 2024-05-29)
q_rrdxa60_top_matview = """
create materialized view rrdxa.rrdxa60_top as
select call, count(distinct (rroperator, band)),
    count(*) filter (where rroperator in ('DA0RR', 'DL60RRDXA')) as da0rr
from (
    -- all operators that have worked a member
    select operator as call, rroperator, band
        from log_v
        where start between '2024-01-01' and '2025-01-01' and rroperator is not null
    union
    -- all DX calls of member QSOs
    select basecall(call), rrcalls.rroperator, band
        from log
        join rrcalls on basecall(log.station_callsign) = rrcalls.rrcall
        where start between '2024-01-01' and '2025-01-01'
)
group by 1
having count(distinct (rroperator, band)) >= 60
order by 2 desc;
"""

q_worked = """
select start, start_str, station_callsign, operator, call, string_agg(distinct rroperator, ' ') rroperator, any_value(country) country, band, any_value(freq) freq, any_value(major_mode) major_mode, any_value(mode) mode from (
    -- QSOs from this operator to other members
    select start::date, start_str, station_callsign, operator, call, rroperator, country, band, freq, major_mode, mode
        from log_v
        where operator = %s and start between %s and %s and rroperator is not null
    union all
    -- QSOs from members to this basecall
    select start::date, start_str, log_v.call, basecall, station_callsign, rrcalls.rroperator, null as country, band, freq, major_mode, mode
        from log_v join rrcalls on basecall(log_v.station_callsign) = rrcalls.rrcall
        where log_v.basecall = %s and start between %s and %s
)
group by start, start_str, station_callsign, operator, call, band
order by start, start_str, station_callsign, operator, call, band
"""

def v_rrdxa60(request):
    top_calls, members_list = [], ''
    call, qsos, bands, worked = None, None, set(), []
    da0rr = False
    bandpoints = 0

    #today = datetime.date.today()
    #year = today.year
    year = 2024

    if 'call' in request.GET:
        call = request.GET['call'].upper()

        with connection.cursor() as cursor:
            params = [call, f"{year}-01-01", f"{year+1}-01-01"]
            cursor.execute(q_worked, params * 2)
            qsos = namedtuplefetchall(cursor)

            #cursor.execute(q_worked_bands, params * 3)
            #bands = [x[0] for x in cursor.fetchall()]

            # compute crosstab of worked members
            #cursor.execute(q_worked, params * 2)
            wkd = {'DA0RR': {}}
            for row in qsos:
                if row.rroperator not in wkd:
                    wkd[row.rroperator] = {}
                if row.band not in wkd[row.rroperator]:
                    wkd[row.rroperator][row.band] = 1
                    bandpoints += 1
                    if row.rroperator in ('DA0RR', 'DL60RRDXA'):
                        da0rr = True
                    bands.add(row.band)
            bands = band_sort(bands)

            for operator in sorted(wkd):
                worked.append({
                    'operator': operator,
                    'bands': [(wkd[operator][band] if band in wkd[operator] else '') for band in bands],
                })

    else:
        with connection.cursor() as cursor:
            #params = [f"{year}-01-01", f"{year+1}-01-01"] * 2
            #cursor.execute(q_rrdxa60_top, params)
            cursor.execute("select * from rrdxa60_top where da0rr > 0")
            top_calls = namedtuplefetchall(cursor)

            cursor.execute(q_members_list, [])
            members_list = cursor.fetchone()[0]

    context = {
        'title': f"Worked All RRDXA60",
        'top_calls': top_calls,
        'top_calls_len': len(top_calls),
        'members_list': members_list,
        'call': call,
        'bands': bands,
        'worked': worked,
        'bandpoints': bandpoints,
        'da0rr': da0rr,
        'qsos': qsos,
    }
    return render(request, 'rrlog/rrdxa60.html', context)

q_challenge = """
select rank() over (order by score desc, qsos desc), * from (
select operator as call,
    sum(qsos / n_operators) as qsos,
    count(*) filter (where qsos >= 60 or vhf and qsos >= 30) as multis,
    sum(qsos / n_operators) * count(*) filter (where qsos >= 60 or vhf and qsos >= 30) as score,
    array_agg(u.id order by e.start, event) as upload_ids,
    array_agg(station_callsign order by e.start, event) as station_callsigns,
    array_agg(qsos / n_operators order by e.start, event) as event_qsos,
    array_agg(event order by e.start, event) as events,
    array_agg(vhf order by e.start, event) as event_vhf
from upload_operators u
    join event e on u.event_id = e.event_id
    join rrcalls rr on u.operator = rr.rrcall -- limit to RRDXA members
where e.start between %s and %s
group by 1
)
order by score desc, qsos desc, call
"""

def v_challenge(request, year=2024):
    with connection.cursor() as cursor:
        cursor.execute(q_challenge, [f"{year}-01-01", f"{year+1}-01-01"])
        entries = namedtuplefetchall(cursor)

    # psycopg2 doesn't understand tuples in arrays, so we select separate
    # arrays above and zip them together here
    for entry in entries:
        entry.events[:] = [{"upload_id": x[0], "station_callsign": x[1], "qsos": x[2], "event": x[3], "vhf": x[4]} \
                for x in zip(entry.upload_ids, entry.station_callsigns, entry.event_qsos, entry.events, entry.event_vhf)]

    context = {
        'title': f"RRDXA 6x60 Contest Challenge {year}",
        'year': year,
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
 to_char(schedule.start, 'HH24:MI') start,
 schedule.days,
 to_char(schedule.stop, 'HH24:MI') stop,
 schedule.vhf,
 coalesce(to_char('2023-12-01'::date + schedule.month * '1month'::interval, 'FMMonth'), 'Other') as month_str
from schedule
order by month, (week+8) % 8, dow, start"""

def v_events(request):
    username = None

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
            cursor.execute("insert into event (event, start, stop, author, vhf) values (%s, %s, %s, %s, %s)",
                           [request.POST['event'], request.POST['start'], request.POST['end'], username, is_vhf])
            connection.commit()

    with connection.cursor() as cursor:
        cursor.execute(q_events, [0, 1000])
        events = namedtuplefetchall(cursor)
        cursor.execute(q_schedules)
        schedules = namedtuplefetchall(cursor)

    today = str(datetime.date.today())

    context = {
        'today': today,
        'events': events,
        'schedules': schedules,
    }
    return render_with_username_cookie(request, 'rrlog/events.html', context, username)

q_event = """
with uploads as (
select station_callsign,
    id as upload_id,
    nullif(operators, station_callsign) operators,
    contest,
    qsos,
    claimed_score,
    max(claimed_score) over (order by qsos rows unbounded preceding) previous_score,
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
    and qsos > 0
)
(select * from uploads order by coalesce(claimed_score, previous_score) desc nulls last, qsos desc nulls last)
union all
select count(*)::text, -1, null, null, sum(qsos), sum(claimed_score), null, null, null, null, null, null, null, null, null, null from uploads
"""

def v_event(request, event):
    with connection.cursor() as cursor:
        cursor.execute(q_event, [event])
        entries = namedtuplefetchall(cursor)

        cursor.execute("select event, start_str(start) start, stop_str(stop) stop, vhf from event where event = %s", [event])
        event_data = namedtuplefetchall(cursor)

    if not event_data:
        return render(request, 'rrlog/generic.html', { 'message': "No such event" }, status=404)

    context = {
        'title': event,
        'event': event_data[0],
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
{}
order by id desc limit 1000"""

@auth_required
def v_upload(request):
    username = request.username

    # actual page
    message = None
    if request.method == 'POST' and 'logfile' in request.FILES:
        upload_id, contest, message = log_upload(connection, request, username)

        if upload_id and contest:
            return redirect('edit', upload_id=upload_id)

    elif request.method == 'POST' and 'delete' in request.POST:
        upload_id = request.POST['delete']
        with connection.cursor() as cursor:
            q_delete = "delete from upload where id = %s"
            params = [upload_id]
            if username not in settings.RRDXA_ADMINS:
                q_delete += " and uploader = %s"
                params.append(username)
            cursor.execute(q_delete, params)
            message = f"Upload {upload_id} deleted"

    with connection.cursor() as cursor:
        # get list of all uploads (including this one)
        if username not in settings.RRDXA_ADMINS:
            qual, params = "where uploader = %s", [username]
        else:
            qual, params = "", []
        cursor.execute(q_upload_list.format(qual), params)
        uploads = namedtuplefetchall(cursor)

    context = {
        'title': f"Log Upload",
        'message': message,
        'uploads': uploads,
        'uploader': username,
    }
    return render_with_username_cookie(request, 'rrlog/upload.html', context, username)

@auth_required
def v_download(request, upload_id):
    username = request.username

    with connection.cursor() as cursor:
        q_download = "select adif, filename from upload where id = %s"
        params = [upload_id]
        if username not in settings.RRDXA_ADMINS:
            q_download += " and uploader = %s"
            params.append(username)
        cursor.execute(q_download, params)
        adif, filename = cursor.fetchone()

    response = HttpResponse(adif, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response.set_cookie('username', username)
    return response

def v_summary(request, upload_id):
    # username cookie is not secure, we show extra controls based on it, but
    # still require authentication to actually use them
    username = None
    if 'username' in request.COOKIES:
        username = request.COOKIES['username']

    with connection.cursor() as cursor:
        cursor.execute(q_log_dupecheck.format('where upload = %s', 'asc', 10000), [upload_id])
        qsos = namedtuplefetchall(cursor)
        data, summary, subject = get_summary(cursor, upload_id)

    context = {
        'title': subject,
        'upload_id': upload_id,
        'data': data,
        'summary': summary,
        'qsos': qsos,
        'username': username,
        'edit': data and username in [data.uploader] + settings.RRDXA_ADMINS
    }
    return render(request, 'rrlog/summary.html', context)

@auth_required
def v_edit(request, upload_id):
    username = request.username

    if request.method == 'POST':
        with connection.cursor() as cursor:

            set_fields, params = [], []
            for field in 'station_callsign', 'operator', 'contest', 'operators', 'club', 'category_operator', 'category_assisted', 'category_band', 'category_mode', 'category_overlay', 'category_power', 'category_station', 'category_time', 'category_transmitter', 'location', 'grid_locator', 'soapbox', 'claimed_score', 'computed_score', 'event_id', 'exchange':
                if field in request.POST:
                    set_fields.append(field)
                    params.append(request.POST[field] or None)
            if set_fields:
                q_update = "update upload set " + \
                        ", ".join([f"{field} = %s" for field in set_fields]) + \
                        " where id = %s"
                params.append(upload_id)
                if username not in settings.RRDXA_ADMINS:
                    q_update += " and uploader = %s"
                    params.append(username)
                cursor.execute(q_update, params)

            if 'event_id' in request.POST and re.match(r'^\d+$', request.POST['event_id']):
                cursor.execute("select start, stop from event where event_id = %s", [request.POST['event_id']])
                start, stop = cursor.fetchone()
                if start and stop:
                    cursor.execute("""\
update upload set qsos =
    (select count(distinct (call, band, major_mode, mode, submode)) from log
     where start between %s and %s and upload = %s)
where id = %s""", [start, stop, upload_id, upload_id])

    with connection.cursor() as cursor:
        cursor.execute(q_log_dupecheck.format('where upload = %s', 'asc', 10000), [upload_id])
        qsos = namedtuplefetchall(cursor)
        data, summary, subject = get_summary(cursor, upload_id)

        # post to reflector when requested
        if request.POST.get('reflector'):
            post_summary(data, summary, subject)

        # get all events overlapping this upload
        cursor.execute("select *, start_str(start), stop_str(stop), event_id = %s as selected from event where %s <= stop and %s >= start",
                       [data.event_id, data.upload_start, data.upload_stop])
        eventlist = namedtuplefetchall(cursor)

    context = {
        'title': subject,
        'upload_id': upload_id,
        'data': data,
        'summary': summary,
        'qsos': qsos,
        'username': username,
        'eventlist': eventlist,
        'mail_checked': False,
    }
    return render(request, 'rrlog/edit.html', context)

def v_members(request):
    with connection.cursor() as cursor:
        cursor.execute(r"select call, callsigns from members where call ~ '\d' and public order by call")
        members = namedtuplefetchall(cursor)

        cursor.execute(q_members_list, [])
        members_list = cursor.fetchone()[0]


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
        'members_list': members_list,
        'members': members,
    }
    return render(request, 'rrlog/members.html', context)
