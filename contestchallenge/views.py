from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import json
import datetime
import re

from rrdxa import settings

from rrlog.utils import namedtuplefetchall, band_sort

q_challenge = """
with raw as (
    select u.id as upload_id, u.station_callsign, u.operator, qsos / n_operators as qsos,
        e.event, e.event ~ '^(CQ-WW|CQ-WPX|WW-?DIGI|(DARC-)?WAEDC|(DARC-)?WAG)' as big,
        row_number() over (partition by operator, e.event ~ '^(CQ-WW|CQ-WPX|WW-?DIGI|(DARC-)?WAEDC|(DARC-)?WAG)' order by qsos desc, u.id) as extra_contests
    from upload_operators u
        join event e on u.event_id = e.event_id
        join rrcalls rr on u.operator = rr.rrcall -- limit to RRDXA members
    where e.start >= %s and e.start < %s
        and u.qsos / n_operators >= 60
),
ten_contests as (
    select *, row_number() over (partition by operator order by qsos desc, upload_id) from raw
        where big or extra_contests <= 4
        order by qsos desc, upload_id
)
select
    rank() over (order by count(*) * sum(qsos) desc),
    operator as call,
    count(*) as multis,
    sum(qsos) as qsos,
    count(*) * sum(qsos) as score,
    array_agg(upload_id) as upload_ids,
    array_agg(station_callsign) as station_callsigns,
    array_agg(event) as events,
    array_agg(qsos) as event_qsos,
    array_agg(big) as big
from ten_contests where row_number <= 10
group by operator
order by count(*) * sum(qsos) desc
"""

q_ukw_challenge = """
with raw as (
    select u.id as upload_id, u.station_callsign, u.operator, qsos / n_operators as qsos,
        e.event,
        row_number() over (partition by u.operator order by qsos desc, u.id)
    from upload_operators u
        join event e on u.event_id = e.event_id
        join rrcalls rr on u.operator = rr.rrcall -- limit to RRDXA members
    where e.start >= %s and e.start < %s
        and u.qsos / n_operators >= 30
        and e.vhf
)
select
    rank() over (order by count(*) * sum(qsos) desc),
    operator as call,
    count(*) as multis,
    sum(qsos) as qsos,
    count(*) * sum(qsos) as score,
    array_agg(upload_id) as upload_ids,
    array_agg(station_callsign) as station_callsigns,
    array_agg(event) as events,
    array_agg(qsos) as event_qsos
from raw where row_number <= 5
group by operator
order by count(*) * sum(qsos) desc
"""

def v_contestchallenge(request, year=None):
    if year is None:
        today = datetime.date.today()
        year = today.year

    with connection.cursor() as cursor:
        cursor.execute(q_challenge, [f"{year}-01-01", f"{year+1}-01-01"])
        entries = namedtuplefetchall(cursor)
        cursor.execute(q_ukw_challenge, [f"{year}-01-01", f"{year+1}-01-01"])
        ukw_entries = namedtuplefetchall(cursor)

    # psycopg2 doesn't understand tuples in arrays, so we select separate
    # arrays above and zip them together here
    for entry in entries:
        entry.events[:] = [{"upload_id": x[0], "station_callsign": x[1], "qsos": x[2], "event": x[3], "big": x[4]} \
                for x in zip(entry.upload_ids, entry.station_callsigns, entry.event_qsos, entry.events, entry.big)]
    for entry in ukw_entries:
        entry.events[:] = [{"upload_id": x[0], "station_callsign": x[1], "qsos": x[2], "event": x[3]} \
                for x in zip(entry.upload_ids, entry.station_callsigns, entry.event_qsos, entry.events)]

    context = {
        'title': f"RRDXA Contest Challenge {year}",
        'year': year,
        'entries': entries,
        'ukw_entries': ukw_entries,
    }
    return render(request, 'contestchallenge/challenge.html', context)
