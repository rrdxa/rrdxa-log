from django.db import transaction
import re
from rrlog import cabrillo, country

q_insert_qso = """insert into log
(start, station_callsign, operator, call, dxcc, band, freq, major_mode, mode, rsttx, extx, rstrx, exrx, contest, upload)
values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict on constraint log_pkey do update set
operator = coalesce(excluded.operator, log.operator),
dxcc =     coalesce(excluded.dxcc, log.dxcc),
freq =     coalesce(excluded.freq, log.freq),
mode =     coalesce(excluded.mode, log.mode),
rsttx =    excluded.rsttx,
extx =     excluded.extx,
rstrx =    excluded.rstrx,
exrx =     excluded.exrx,
contest =  excluded.contest,
upload =   excluded.upload
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
            elif major_mode == 'PS':
                major_mode = 'DIGI'
                mode = 'PSK'
            elif major_mode == 'DG':
                major_mode = 'DIGI'
                mode = None

            cursor.execute(q_insert_qso,
                           [start,
                            qso_station, qso_operator,
                            call,
                            dxcc,
                            band, freq,
                            major_mode, mode,
                            qso['rsttx'], qso['extx'],
                            qso['rstrx'], qso['exrx'],
                            contest,
                            upload_id,
                            ])

        cursor.execute("""update upload set
qsos = %s,
start = %s,
stop = %s,
contest = %s,
station_callsign = coalesce(%s, station_callsign),
operators = %s,
club = %s,
category_operator = %s,
category_assisted = %s,
category_band = %s,
category_mode = %s,
category_overlay = %s,
category_power = %s,
category_station = %s,
category_time = %s,
category_transmitter = %s,
location = %s,
grid_locator = %s,
soapbox = %s,
claimed_score = %s,
exchange = %s
where id = %s""",
                       [len(qsos),
                        upload_start,
                        upload_stop,
                        contest,
                        data.get('CALLSIGN'),
                        data.get('OPERATORS'),
                        data.get('CLUB'),
                        data.get('CATEGORY-OPERATOR'),
                        data.get('CATEGORY-ASSISTED'),
                        data.get('CATEGORY-BAND'),
                        data.get('CATEGORY-MODE'),
                        data.get('CATEGORY-OVERLAY'),
                        data.get('CATEGORY-POWER'),
                        data.get('CATEGORY-STATION'),
                        data.get('CATEGORY-TIME'),
                        data.get('CATEGORY-TRANSMITTER'),
                        data.get('LOCATION'),
                        data.get('GRID-LOCATOR'),
                        data.get('SOAPBOX'),
                        data.get('CLAIMED-SCORE'),
                        qsos[0]['extx'] if len(qsos) > 0 else None,
                        upload_id])

    return len(qsos)
