from django.shortcuts import render
from django.http import HttpResponse
from django.db import connection
from collections import namedtuple

from rrlog.log_upload import log_upload

def namedtuplefetchall(cursor):
    "Return all rows from a cursor as a namedtuple"
    desc = cursor.description
    nt_result = namedtuple('Result', [col[0] for col in desc])
    return [nt_result(*row) for row in cursor.fetchall()]

q_index = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str,
exists (select from call where log.call = call.call) as known_station
from log order by start desc limit 100
"""

def index(request):
    with connection.cursor() as cursor:
        cursor.execute(q_index, [])
        rows = namedtuplefetchall(cursor)

    context = { 'title': 'Logbook', 'qsos': rows }
    return render(request, 'rrlog/index.html', context)

q_call = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str,
exists (select from call where log.call = call.call) as known_station
from log where station_callsign = %s or operator = %s or call = %s order by start desc limit 100
"""

def v_call(request, call):
    with connection.cursor() as cursor:
        cursor.execute(q_call, [call, call, call])
        rows = namedtuplefetchall(cursor)

    context = { 'title': call, 'call': call, 'qsos': rows }
    return render(request, 'rrlog/call.html', context)

q_cty = """
select *,
to_char(start, 'DD.MM.YYYY HH24:MI') as start_str,
exists (select from call where log.call = call.call) as known_station
from log where cty = %s order by start desc limit 100
"""

def v_cty(request, cty):
    with connection.cursor() as cursor:
        cursor.execute(q_cty, [cty])
        rows = namedtuplefetchall(cursor)

    context = { 'title': cty, 'cty': cty, 'qsos': rows }
    return render(request, 'rrlog/cty.html', context)

q_contest = """
select *,
exists (select from station where qsos.callsign = station.call) as known_station
from qsos where contest = %s order by date desc, time desc limit 100
"""

def v_contest(request, contest):
    with connection.cursor() as cursor:
        cursor.execute(q_contest, [contest])
        rows = namedtuplefetchall(cursor)

    context = { 'contest': contest, 'qsos': rows }
    return render(request, 'rrlog/contest.html', context)

q_month = """
with data as
(select station,
  count(*) as qsos,
  count(distinct callsign) as calls,
  count(distinct callsign::varchar(2)) as cty,
  count(distinct (band, callsign::varchar(2))) as band_cty
from qsos where date >= %s::date and date < %s::date + '1month'::interval
group by station)
select *, qsos * band_cty as score from data
order by score desc
"""

def v_month(request, year, month):
    with connection.cursor() as cursor:
        date = f"{year}-{month:02}-01"
        cursor.execute(q_month, [date, date])
        rows = namedtuplefetchall(cursor)

    context = {
        'month': f"{year}-{month:02}",
        'prev_month': f"{year-1 if month == 1 else year}-{((month-2)%12)+1:02}",
        'next_month': f"{year+1 if month == 12 else year}-{(month%12)+1:02}",
        'year': year,
        'stations': rows
    }
    return render(request, 'rrlog/month.html', context)

q_year = """
with data as
(select station,
  count(*) as qsos,
  count(distinct callsign) as calls,
  count(distinct callsign::varchar(2)) as cty,
  count(distinct (band, callsign::varchar(2))) as band_cty
from qsos where date >= %s::date and date < %s::date + '1year'::interval
group by station)
select *, qsos * band_cty as score from data
order by score desc
"""

def v_year(request, year):
    with connection.cursor() as cursor:
        date = f"{year}-01-01"
        cursor.execute(q_year, [date, date])
        rows = namedtuplefetchall(cursor)

    context = {
        'year': year,
        'prev_year': year - 1,
        'next_year': year + 1,
        'stations': rows
    }
    return render(request, 'rrlog/year.html', context)

#def handle_uploaded_file(f):
#    data = 
#        for chunk in f.chunks():
#            destination.write(chunk)

def upload(request):
    #with connection.cursor() as cursor:
    #    date = f"{year}-01-01"
    #    cursor.execute(q_year, [date, date])
    #    rows = namedtuplefetchall(cursor)
    print("session is", request.session)

    message = None
    if request.method == 'POST' and 'logfile' in request.FILES:
        message = log_upload(connection, request, "DF7CB")

    context = {
        'title': 'Log Upload',
        'message': message
    }
    return render(request, 'rrlog/upload.html', context)

def v_login(request):
    message = None

    if 'username' in request.POST and 'password' in request.POST:
        username = request.POST['username']
        password = request.POST['password']
        print(username, password)

        with connection.cursor() as cursor:
            cursor.execute(q_index, [])
            rows = namedtuplefetchall(cursor)
            request.session['user'] = username

        #user = authenticate(request, username=username, password=password)
        #print(user)
        #request.session['user'] = username
        #if user is not None:
        #    message = user
        #    login(request, user)
        #else:
        #    message = 'not logged in'

    print("session is", request.session.keys())

    context = {
        'title': 'Login',
        'message': message
    }
    return render(request, 'rrlog/upload.html', context)

