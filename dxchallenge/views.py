from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import json
import datetime
import re

from rrdxa import settings

from rrlog.utils import namedtuplefetchall, band_sort


q_dxchallenge = """
select *, rank() over (partition by major_mode order by bandslots desc) from
(select major_mode, rrmember, count(*) as bandslots, array_agg(distinct dxcc) as dxccs from bandpoints where year = %s group by 1, 2);
"""

def v_dxchallenge(request, year=None):
    if year is None:
        today = datetime.date.today()
        year = today.year

    entries = {"CW": [], "PHONE": [], "DIGI": [], "FT8": []}
    data = {"CW": {}, "PHONE": {}, "DIGI": {}, "FT8": {}}
    with connection.cursor() as cursor:
        cursor.execute(q_dxchallenge, [year])
        for row in namedtuplefetchall(cursor):
            entries[row.major_mode].append({'call': row.rrmember, 'bandslots': row.bandslots, 'rank': row.rank})
            data[row.major_mode][row.rrmember] = row.dxccs

    context = {
        'title': f"RRDXA DX Challenge {year}",
        'year': year,
        'modes': ['CW', 'PHONE', 'DIGI', 'FT8'],
        'entries': entries,
        'data': json.dumps(data),
    }
    return render(request, 'dxchallenge/dxchallenge.html', context)

