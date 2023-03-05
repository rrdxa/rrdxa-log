from django.db import transaction
import re
from rrlog import cabrillo, country

q_insert_qso = """insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, rsttx, rstrx, contest, upload)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator = excluded.operator,
dxcc = excluded.dxcc,
band = excluded.band,
freq = excluded.freq,
major_mode = excluded.major_mode,
mode = excluded.mode,
rsttx = excluded.rsttx,
rstrx = excluded.rstrx,
contest = excluded.contest,
upload = excluded.upload
"""

def cabrillo_upload(cursor, content, station_callsign, operator, contest, upload_id):
    data = cabrillo.parse(content)
    qsos = data['qsos']
    upload_start, upload_stop = None, None

    # if there is a single operator specified in the Cabrillo file, use it
    if 'OPERATORS' in data and re.match(r'[\w\d/]+$', data['OPERATORS']):
        operator = data['OPERATORS'].upper()

    contest = data.get('CONTEST') or contest

    with transaction.atomic():
        for qso in qsos:
            start = qso['ts']
            upload_start = min(upload_start, start) if upload_start else start
            upload_stop = max(upload_stop, start) if upload_stop else start

            qso_station = qso['station_callsign'].upper()
            qso_operator = operator
            if qso_station == qso_operator:
                qso_operator = None

            call = qso['call'].upper()
            dxcc = country.lookup(call, start)

            rsttx = qso['rsttx'] + ' ' + qso['extx']
            rstrx = qso['rstrx'] + ' ' + qso['exrx']

            freq = qso['freq'] / 1000
            if qso['band'] >= 2:
                band = str(int(qso['band'])) + 'm'
            elif qso['band'] == 0.053:
                band = '6cm'
            elif qso['band'] >= 0.0125:
                band = str(int(qso['band'] * 100.0)) + 'cm'
            else:
                raise Exception(f"Band {qso['band']} is not supported yet")

            major_mode = qso['mode'].upper()
            if major_mode == 'CW':
                mode = 'CW'
            elif major_mode == 'PH':
                major_mode = 'PHONE'
                mode = 'SSB'
            elif major_mode == 'FM':
                major_mode = 'PHONE'
                mode = 'FM'
            elif major_mode == 'RY':
                major_mode = 'DIGI'
                mode = 'RTTY'
            elif major_mode == 'DG':
                major_mode = 'DIGI'
                mode = 'DIGI'

            cursor.execute(q_insert_qso,
                           [start,
                            qso_station, qso_operator,
                            call,
                            dxcc,
                            band, freq,
                            major_mode, mode,
                            rsttx, rstrx,
                            contest,
                            upload_id,
                            ])
        cursor.execute("update upload set qsos = %s, start = %s, stop = %s where id = %s", [len(qsos), upload_start, upload_stop, upload_id])

    return len(qsos)
