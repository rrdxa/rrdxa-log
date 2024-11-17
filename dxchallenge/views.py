from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import psycopg2, psycopg2.extras
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

import datetime
import re

from rrdxa import settings

from rrlog.utils import namedtuplefetchall, band_sort


q_dxchallenge = """
select *, rank() over (partition by major_mode order by count desc) from
(select major_mode, rrmember, count(*) from bandpoints where year = %s group by 1, 2);
"""

def v_dxchallenge(request, year=None):
    if year is None:
        today = datetime.date.today()
        year = today.year

    entries = {"CW": [], "PHONE": [], "DIGI": [], "FT8": [], "unknown": []}
    with connection.cursor() as cursor:
        cursor.execute(q_dxchallenge, [year])
        for row in cursor.fetchall():
            entries[row[0]].append({'call': row[1], 'bandslots': row[2], 'rank': row[3]})

    context = {
        'title': f"RRDXA DX Challenge {year}",
        'year': year,
        'modes': ['CW', 'PHONE', 'DIGI', 'FT8'],
        'entries': entries,
    }
    return render(request, 'dxchallenge/dxchallenge.html', context)

