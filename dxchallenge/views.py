from django.shortcuts import render, redirect
from django.http import HttpResponse, FileResponse
from django.db import connection

import json
import datetime
import re

from rrdxa import settings

from rrlog.auth import basic_auth, auth_required
from rrlog.utils import namedtuplefetchall, band_sort

major_modes = ['CW', 'PHONE', 'DIGI', 'FT8', 'MIXED']

q_dxchallenge = """
-- add rank to lists
select
  nullif(rank() over (partition by major_mode order by case when rrmember is null then 100000 else bandslots end desc) - 1, 0) as rank,
  coalesce(major_mode::text, 'MIXED') as major_mode,
  coalesce(rrmember, 'RRDXA') as rrmember,
  bandslots,
  dxccs,
  rrdxa.fetch_bandpoint_qsos(qso_ctids) as qsos
from
-- compute bandpoints per mode+member and aggregate the DXCC and QSO lists
(select major_mode, rrmember,
    count(distinct (band, dxcc)) as bandslots,
    array_agg(distinct dxcc) as dxccs,
    array_agg(qso_ctid) as qso_ctids from
    -- get one DXCC with example QSO per member
    (select major_mode, rrmember, band, dxcc, any_value(bandpoints.ctid) as qso_ctid
        from bandpoints
        where (year = %s or %s = 0)
            and (band = %s or %s is null)
        group by major_mode, rrmember, band, dxcc)
    group by cube (1, 2));
"""

@auth_required
def v_dxchallenge(request, year=None):
    today = datetime.date.today()
    this_year = today.year
    if year is None: year = this_year

    band = request.GET['band'] if 'band' in request.GET else None

    entries = {x: [] for x in major_modes}
    mode_member_dxccs = {x: {} for x in major_modes}
    mode_member_qsos = {x: {} for x in major_modes}
    with connection.cursor() as cursor:
        cursor.execute(q_dxchallenge, [year, year, band, band])
        for row in namedtuplefetchall(cursor):
            entries[row.major_mode].append({'call': row.rrmember, 'bandslots': row.bandslots, 'rank': row.rank})
            mode_member_dxccs[row.major_mode][row.rrmember] = row.dxccs
            mode_member_qsos[row.major_mode][row.rrmember] = row.qsos

        cursor.execute("select distinct band from bandpoints where (year = %s or %s = 0) order by 1", [year, year])
        bands = [x[0] for x in cursor.fetchall()]

    title_year = year if year > 0 else "All Time"
    context = {
        'title': f"RRDXA DX Challenge {title_year} {band or ''}",
        'year': year,
        'this_year': this_year,
        'band': band,
        'bands': bands,
        'modes': major_modes,
        'entries': entries,
        'mode_member_dxccs': json.dumps(mode_member_dxccs),
        'mode_member_qsos': json.dumps(mode_member_qsos),
    }
    return render(request, 'dxchallenge/dxchallenge.html', context)

