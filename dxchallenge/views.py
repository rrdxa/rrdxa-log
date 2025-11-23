from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import json
import datetime
import re

from rrdxa import settings

from rrlog.utils import namedtuplefetchall, band_sort

major_modes = ['CW', 'PHONE', 'DIGI', 'FT8', 'MIXED']

q_dxchallenge = """
select coalesce(major_mode::text, 'MIXED') as major_mode, rrmember, bandslots, dxccs, rank() over (partition by major_mode order by bandslots desc) from
(select major_mode, rrmember, count(distinct (band, dxcc)) as bandslots, array_agg(distinct dxcc) as dxccs
    from bandpoints
    where year = %s
        and (band = %s or %s is null)
    group by grouping sets ((1, 2), (2)));
"""

def v_dxchallenge(request, year=None):
    if year is None:
        today = datetime.date.today()
        year = today.year

    band = request.GET['band'] if 'band' in request.GET else None

    entries = {x: [] for x in major_modes}
    data = {x: {} for x in major_modes}
    with connection.cursor() as cursor:
        cursor.execute(q_dxchallenge, [year, band, band])
        for row in namedtuplefetchall(cursor):
            entries[row.major_mode].append({'call': row.rrmember, 'bandslots': row.bandslots, 'rank': row.rank})
            data[row.major_mode][row.rrmember] = row.dxccs

        cursor.execute("select distinct band from bandpoints where year = %s order by 1", [year])
        bands = [x[0] for x in cursor.fetchall()]

    context = {
        'title': f"RRDXA DX Challenge {year} {band or ''}",
        'year': year,
        'band': band,
        'bands': bands,
        'modes': major_modes,
        'entries': entries,
        'data': json.dumps(data),
    }
    return render(request, 'dxchallenge/dxchallenge.html', context)

